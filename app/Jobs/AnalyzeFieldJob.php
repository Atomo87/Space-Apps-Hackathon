<?php

namespace App\Jobs;

use App\Models\Field;
use App\Models\FieldAnalysis;
use App\Services\FieldProcessor;
use App\Services\GeoServiceClient;
use App\Services\NasaPowerDaily;
use App\Services\PlantingWindow;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * Busca a climatologia (NASA POWER), o relevo (SRTM) e a cobertura verde (NDVI MODIS) via geo-service e guarda no MySQL.
 * Depois disso, prioridades e cenários são recalculados sem consultar a NASA de novo.
 */
class AnalyzeFieldJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;

    public int $timeout = 720;

    public int $backoff = 30;

    public function __construct(public int $fieldId) {}

    /** Etapas, na ordem, com a mensagem mostrada ao produtor e o progresso (%) ao começar cada uma. */
    public const STEPS = [
        'queue' => ['Na fila: preparando a consulta aos dados da NASA…', 3],
        'resume' => ['Retomando de onde parou…', 5],
        'climate' => ['Consultando o clima da NASA POWER…', 8],
        'terrain' => ['Calculando a declividade do terreno (SRTM)…', 25],
        'vegetation' => ['Lendo a cobertura verde no satélite (NDVI MODIS e HLS)…', 35],
        'stress' => ['Medindo calor da superfície e evapotranspiração (MODIS)…', 55],
        'earthdata' => ['Lendo SMAP, GPM, ECOSTRESS e GRACE-FO (NASA Earthdata)…', 68],
        'planting' => ['Calculando a janela de plantio com o clima diário (NASA POWER)…', 88],
    ];

    /** Progresso (%) correspondente à mensagem de status gravada no talhão. */
    public static function progressFor(?string $message): ?int
    {
        foreach (self::STEPS as [$text, $pct]) {
            if ($message === $text) {
                return $pct;
            }
        }

        return null;
    }

    public function handle(GeoServiceClient $geo, NasaPowerDaily $power, PlantingWindow $window): void
    {
        $field = Field::findOrFail($this->fieldId);
        $field->update(['status' => Field::STATUS_PROCESSING]);

        // Progresso gravado etapa por etapa: se o processamento for interrompido (limite da hospedagem, queda),
        // a próxima tentativa retoma das etapas que faltam em vez de recomeçar do zero.
        $partialKey = sprintf('field-partial:%d:%s:%s:%s:%s', $field->id, round($field->latitude, 4), round($field->longitude, 4), $field->power_start_year, $field->power_end_year);
        $partial = Cache::get($partialKey, []);
        $step = function (string $key, callable $fetch, bool $required = false) use ($field, &$partial, $partialKey) {
            if (array_key_exists($key, $partial)) {
                return $partial[$key];
            }
            $field->update(['status_message' => self::STEPS[$key][0]]);
            try {
                $value = $fetch();
            } catch (Throwable $e) {
                if ($required) {
                    throw $e;
                }
                Log::warning("Etapa {$key} indisponível", ['field_id' => $field->id, 'error' => $e->getMessage()]);
                $value = null;
            }
            $partial[$key] = $value;
            Cache::put($partialKey, $partial, now()->addHours(3));

            return $value;
        };

        $profile = $step('climate', fn () => $geo->climateProfile($field->latitude, $field->longitude, $field->power_start_year, $field->power_end_year), required: true);
        // Os demais são complementares: sem eles, a análise segue e declara a lacuna.
        $terrain = $step('terrain', fn () => $geo->terrain($field->latitude, $field->longitude, $field->boundary));
        $vegetation = $step('vegetation', fn () => $geo->vegetation($field->latitude, $field->longitude));
        $stress = $step('stress', fn () => $geo->stress($field->latitude, $field->longitude));
        $earthdata = $step('earthdata', fn () => $geo->earthdata($field->latitude, $field->longitude));

        // Janela de plantio: chuva e temperatura diárias da NASA POWER (API pública).
        $planting = $step('planting', function () use ($field, $power, $window) {
            $last = (int) now()->year - 1;

            return $window->compute($power->fetch($field->latitude, $field->longitude, $field->power_start_year ?? max(Field::POWER_FIRST_YEAR, $last - 20), $field->power_end_year ?? $last));
        });

        FieldAnalysis::updateOrCreate(
            ['field_id' => $field->id],
            [
                'engine_version' => (string) ($profile['engine_version'] ?? 'desconhecida'),
                'climate' => $profile, 'terrain' => $terrain, 'vegetation' => $vegetation, 'stress' => $stress, 'earthdata' => $earthdata,
                'planting' => $planting, 'computed_at' => now(),
            ],
        );

        $field->update(['status' => Field::STATUS_READY, 'status_message' => null, 'analyzed_at' => now()]);
        Cache::forget($partialKey);
        Cache::forget("field-resumes-{$field->id}");
        Cache::forget(FieldProcessor::startedKey($field));
    }

    public function failed(?Throwable $e): void
    {
        Cache::forget("field-process-started-{$this->fieldId}");
        Field::whereKey($this->fieldId)->update([
            'status' => Field::STATUS_ERROR,
            'status_message' => $e?->getMessage() ?: 'Falha ao processar o talhão.',
        ]);
    }
}
