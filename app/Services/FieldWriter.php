<?php

namespace App\Services;

use App\Models\Crop;
use App\Models\Farm;
use App\Models\Field;
use Illuminate\Support\Arr;
use Illuminate\Support\Facades\DB;

/** Grava propriedade, talhão, solo, histórico, prioridades e restrições numa transação (A2). */
class FieldWriter
{
    /**
     * @param  array<string,mixed>  $ownership  só na criação: ['user_id' => int|null, 'is_demo' => bool]
     */
    public function save(array $data, ?Field $field = null, array $ownership = []): Field
    {
        return DB::transaction(function () use ($data, $field, $ownership) {
            $farmData = Arr::only($data['farm'], ['name', 'municipality', 'state', 'has_livestock']);
            $farm = $field
                ? tap($field->farm)->update($farmData)
                : Farm::create($farmData + Arr::only($ownership, ['user_id', 'is_demo']));

            $fieldData = Arr::only($data['field'], ['name', 'latitude', 'longitude', 'boundary', 'area_ha', 'irrigated', 'irrigation_mm_day']);
            $fieldData['irrigation_mm_day'] = ($fieldData['irrigated'] ?? false) ? ($fieldData['irrigation_mm_day'] ?? null) : null;

            if ($field) {
                // Mudou o ponto ou o contorno → clima e relevo precisam ser recalculados.
                $moved = abs($field->latitude - (float) $fieldData['latitude']) > 1e-5
                    || abs($field->longitude - (float) $fieldData['longitude']) > 1e-5
                    || json_encode($field->boundary) !== json_encode($fieldData['boundary'] ?? null);
                $field->update($fieldData + ($moved ? ['status' => Field::STATUS_PENDING, 'analyzed_at' => null] : []));
                if ($moved) {
                    $field->analysis()->delete();
                }
            } else {
                $field = $farm->fields()->create($fieldData + ['status' => Field::STATUS_PENDING]);
            }

            $field->soil()->updateOrCreate(['field_id' => $field->id], $data['soil']);

            $field->history()->delete();
            $crops = Crop::pluck('id', 'slug');
            foreach ($data['history'] ?? [] as $h) {
                $field->history()->create(['crop_id' => $crops[$h['crop']], 'sown_at' => $h['sown_at'], 'harvested_at' => $h['harvested_at']]);
            }

            $farm->priorities()->updateOrCreate(['farm_id' => $farm->id], $data['priorities']);
            $c = $data['constraints'] ?? [];
            $farm->constraints()->updateOrCreate(['farm_id' => $farm->id], [
                'excluded_crops' => array_values($c['excluded_crops'] ?? []),
                'buyer_crops' => array_values($c['buyer_crops'] ?? []),
                'no_buyer_crops' => array_values($c['no_buyer_crops'] ?? []),
                'missing_equipment' => array_values($c['missing_equipment'] ?? []),
            ]);

            return $field->refresh();
        });
    }
}
