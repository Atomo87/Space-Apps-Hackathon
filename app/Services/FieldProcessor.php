<?php

namespace App\Services;

use App\Jobs\AnalyzeFieldJob;
use App\Models\Field;
use Illuminate\Support\Facades\Cache;
use Throwable;

/**
 * Processamento em segundo plano que funciona em hospedagem compartilhada (sem worker de fila).
 *
 * A requisição responde na hora com "processing" e o job roda DEPOIS da resposta, no mesmo processo PHP
 * (fastcgi/litespeed_finish_request): a tela não trava, e sair da página não interrompe nada.
 * Com QUEUE_CONNECTION diferente de "sync" e um worker rodando, o job vai para a fila normalmente.
 */
class FieldProcessor
{
    /** Cobre o tempo máximo do processamento (set_time_limit abaixo) com folga. */
    private const LOCK_SECONDS = 780;

    /** @var array<string,bool> processamentos já executados neste processo PHP (pelo dono da trava) */
    private static array $started = [];

    /** Inicia o processamento. false = já existe um em andamento para este talhão. */
    public function start(Field $field, ?string $message = null): bool
    {
        $lock = Cache::lock($this->lockKey($field), self::LOCK_SECONDS);
        if (! $lock->get()) {
            return false;
        }

        $field->update(['status' => Field::STATUS_PROCESSING, 'status_message' => $message ?? AnalyzeFieldJob::STEPS['queue'][0]]);
        // Início guardado no servidor: quem volta à página vê o tempo real decorrido, não um cronômetro zerado.
        // Em uma retomada, mantém o início original.
        Cache::add(self::startedKey($field), now()->timestamp, now()->addHours(3));

        if (config('queue.default') !== 'sync') {
            // Fila de verdade: o worker libera a trava ao terminar (ou ela expira).
            AnalyzeFieldJob::dispatch($field->id)->afterCommit();
            $this->releaseLater($field, $lock->owner());

            return true;
        }

        $fieldId = $field->id;
        $owner = $lock->owner();
        $key = $this->lockKey($field);
        dispatch(function () use ($fieldId, $owner, $key) {
            // Em processos longos (testes, Octane) callbacks de "terminating" podem ser chamados de novo.
            if (isset(self::$started[$owner])) {
                return;
            }
            self::$started[$owner] = true;
            ignore_user_abort(true); // o navegador pode fechar a aba: o PHP segue até o fim
            @set_time_limit(720);    // POWER + SRTM + NDVI + LST/ET + Earthdata na primeira vez
            try {
                AnalyzeFieldJob::dispatchSync($fieldId);
            } catch (Throwable $e) {
                report($e);
                Field::whereKey($fieldId)->update([
                    'status' => Field::STATUS_ERROR,
                    'status_message' => $e->getMessage() ?: 'Falha ao processar o talhão.',
                ]);
            } finally {
                Cache::restoreLock($key, $owner)->release();
            }
        })->afterResponse();

        return true;
    }

    private function releaseLater(Field $field, string $owner): void
    {
        // Na fila real, não seguramos a trava: o próprio status "processing" e o recoverIfStale protegem contra repetição.
        Cache::restoreLock($this->lockKey($field), $owner)->release();
    }

    public static function startedKey(Field $field): string
    {
        return "field-process-started-{$field->id}";
    }

    private function lockKey(Field $field): string
    {
        return "field-process-{$field->id}";
    }
}
