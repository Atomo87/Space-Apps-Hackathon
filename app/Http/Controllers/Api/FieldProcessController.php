<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Jobs\AnalyzeFieldJob;
use App\Models\Field;
use App\Services\FieldProcessor;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Cache;

/**
 * Processamento disparado pelo navegador e executado em segundo plano (FieldProcessor).
 * O navegador acompanha o andamento por /status; sair da tela não interrompe o processamento.
 */
class FieldProcessController extends Controller
{
    /** Sem avanço há mais que isso, o processamento morreu (a etapa mais longa tem limite de 4 min). */
    private const STALE_MINUTES = 6;

    /** Retomadas automáticas antes de desistir e mostrar "Tentar de novo". */
    private const MAX_RESUMES = 2;

    public function status(Field $field, FieldProcessor $processor): JsonResponse
    {
        $this->recoverIfStale($field, $processor);

        return response()->json($this->state($field));
    }

    /** Responde na hora; o processamento segue em segundo plano (o navegador acompanha por /status). */
    public function process(Field $field, FieldProcessor $processor): JsonResponse
    {
        $this->recoverIfStale($field, $processor);

        if ($field->status === Field::STATUS_READY && ! request()->boolean('force')) {
            return response()->json($this->state($field));
        }
        if ($field->status === Field::STATUS_PROCESSING) {
            return response()->json($this->state($field), 202);
        }

        $processor->start($field);

        return response()->json($this->state($field->refresh()), 202);
    }

    /**
     * Cada etapa do job atualiza status_message (e updated_at); parado há muito tempo = interrompido
     * (ex.: a hospedagem encerrou o PHP). Retoma sozinho das etapas já gravadas; depois de algumas
     * tentativas, mostra o erro com "Tentar de novo".
     */
    private function recoverIfStale(Field $field, FieldProcessor $processor): void
    {
        if ($field->status !== Field::STATUS_PROCESSING || ! $field->updated_at?->lt(now()->subMinutes(self::STALE_MINUTES))) {
            return;
        }
        $key = "field-resumes-{$field->id}";
        $resumes = (int) Cache::get($key, 0);
        if ($resumes < self::MAX_RESUMES) {
            Cache::put($key, $resumes + 1, now()->addHours(3));
            $field->update(['status' => Field::STATUS_PENDING]);
            $processor->start($field, 'Retomando de onde parou…');

            return;
        }
        Cache::forget($key);
        $field->update([
            'status' => Field::STATUS_ERROR,
            'status_message' => 'O processamento foi interrompido várias vezes. Tente de novo: as etapas já concluídas ficam guardadas.',
        ]);
    }

    private function state(Field $field): array
    {
        $processing = $field->status === Field::STATUS_PROCESSING;
        $started = $processing ? Cache::get(FieldProcessor::startedKey($field)) : null;

        return [
            'id' => $field->id,
            'status' => $field->status,
            'message' => $field->status_message,
            'analyzed_at' => $field->analyzed_at?->toIso8601String(),
            // Andamento gravado no servidor: a tela retoma de onde estava ao voltar.
            'progress' => $processing ? AnalyzeFieldJob::progressFor($field->status_message) : null,
            'started_at' => $started ? now()->setTimestamp((int) $started)->toIso8601String() : null,
            'elapsed_s' => $started ? max(0, now()->timestamp - (int) $started) : null,
        ];
    }
}
