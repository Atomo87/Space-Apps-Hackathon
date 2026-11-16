<?php

namespace App\Services;

use App\Models\FarmerPriority;
use App\Models\Field;

/** Monta o corpo de POST /v1/analysis (contrato B1) a partir do talhão salvo. */
class AnalysisPayload
{
    /** @param  array<string,int>|null  $priorities  pesos temporários (simulação); null = pesos salvos */
    public static function for(Field $field, float $rainDeltaPct = 0, float $tempDeltaC = 0, ?array $priorities = null): array
    {
        $field->loadMissing(['farm.priorities', 'farm.constraints', 'soil', 'history.crop', 'analysis']);
        $farm = $field->farm;
        $soil = $field->soil;
        $constraints = $farm->constraints;

        return [
            'climate' => $field->analysis?->climate ?? [],
            'terrain' => $field->analysis?->terrain,
            'vegetation' => $field->analysis?->vegetation,
            'stress' => $field->analysis?->stress,
            'earthdata' => $field->analysis?->earthdata,
            'field' => [
                // Mesmo arredondamento das consultas às fontes: o recibo do geo-service exige o mesmo ponto.
                'latitude' => round((float) $field->latitude, 4),
                'longitude' => round((float) $field->longitude, 4),
                'area_ha' => $field->area_ha,
                'irrigated' => $field->irrigated,
                'irrigation_mm_day' => $field->irrigation_mm_day,
            ],
            'soil' => $soil ? [
                'source' => $soil->source,
                'texture' => $soil->texture,
                'clay_pct' => $soil->clay_pct,
                'ph_water' => $soil->ph_water,
                'organic_matter_pct' => $soil->organic_matter_pct,
                'v_pct' => $soil->v_pct,
            ] : null,
            'history' => $field->history->map(fn ($h) => [
                'crop' => $h->crop->slug,
                'sown_at' => $h->sown_at->toDateString(),
                'harvested_at' => $h->harvested_at->toDateString(),
            ])->values()->all(),
            'priorities' => array_replace(
                $farm->priorities?->weights() ?? array_fill_keys(FarmerPriority::KEYS, 3),
                array_intersect_key($priorities ?? [], array_flip(FarmerPriority::KEYS)),
            ),
            'constraints' => [
                'excluded_crops' => $constraints?->excluded_crops ?? [],
                'buyer_crops' => $constraints?->buyer_crops ?? [],
                'no_buyer_crops' => $constraints?->no_buyer_crops ?? [],
                'missing_equipment' => $constraints?->missing_equipment ?? [],
                'has_livestock' => $farm->has_livestock,
            ],
            'scenario' => [
                'rain_delta_pct' => $rainDeltaPct,
                'temp_delta_c' => $tempDeltaC,
            ],
        ];
    }
}
