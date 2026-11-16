<?php

namespace App\Services;

use App\Models\Crop;
use App\Models\Field;
use Database\Seeders\CropSeeder;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

class PublicDemo
{
    private const VERSION = 'demo-synthetic-v1';

    private ?array $snapshot = null;

    public function __construct(private readonly FieldWriter $writer) {}

    public function open(): Field
    {
        return Cache::lock('public-demo-create', 30)->block(10, function () {
            $field = Field::whereHas('farm', fn ($q) => $q->where('is_demo', true)->whereNull('user_id'))->oldest()->first();

            return $field ? $this->prepare($field) : DB::transaction(fn () => $this->install(null));
        });
    }

    public function appliesTo(Field $field): bool
    {
        return $field->farm->is_demo && $field->farm->user_id === null;
    }

    public function prepare(Field $field): Field
    {
        if (! $this->appliesTo($field) || $this->isReady($field)) {
            return $field;
        }

        return DB::transaction(function () use ($field) {
            $locked = Field::lockForUpdate()->findOrFail($field->id);

            return $this->isReady($locked) ? $locked : $this->install($locked);
        });
    }

    public function isBaseline(array $payload): bool
    {
        return $payload['scenario']['rain_delta_pct'] == 0
            && $payload['scenario']['temp_delta_c'] == 0
            && $payload['priorities'] == $this->snapshot()['priorities'];
    }

    public function baseline(): array
    {
        return $this->snapshot()['analyses'][app()->isLocale('pt_BR') ? 'pt-BR' : 'en-US'];
    }

    public function label(array $result): array
    {
        $name = __('Dados climáticos ilustrativos');
        $note = __('Série sintética de 2005 a 2025 para demonstrar o GeoSafra.');
        $result['diagnosis']['source']['dataset'] = $name;
        $result['diagnosis']['source']['grid_note'] = $note;
        $result['diagnosis']['source']['citation'] = $name;
        $result['diagnosis']['confidence']['notes'] = [$note];
        foreach ($result['diagnosis']['highlights'] ?? [] as $i => $finding) {
            $result['diagnosis']['highlights'][$i]['datasets'] = array_map(
                fn ($dataset) => $dataset === 'POWER' ? 'DEMO' : $dataset,
                $finding['datasets'],
            );
        }
        foreach ($result['sources'] ?? [] as $i => $source) {
            if ($source['code'] === 'POWER') {
                $result['sources'][$i] = array_replace($source, [
                    'code' => 'DEMO', 'name' => $name, 'citation' => $name, 'resolution' => $note,
                ]);
            }
        }
        foreach ($result['strategies'] ?? [] as $i => $strategy) {
            foreach ($strategy['evidences'] ?? [] as $j => $evidence) {
                $result['strategies'][$i]['evidences'][$j]['datasets'] = array_map(
                    fn ($dataset) => $dataset === 'POWER' ? 'DEMO' : $dataset,
                    $evidence['datasets'],
                );
            }
        }

        return $result;
    }

    private function isReady(Field $field): bool
    {
        return $field->status === Field::STATUS_READY && $field->analysis?->engine_version === self::VERSION;
    }

    private function snapshot(): array
    {
        return $this->snapshot ??= json_decode(file_get_contents(database_path('data/public-demo.json')), true, 512, JSON_THROW_ON_ERROR);
    }

    private function install(?Field $field): Field
    {
        $snapshot = $this->snapshot();
        if (Crop::whereIn('slug', ['soja', 'milho'])->count() !== 2) {
            app(CropSeeder::class)->run();
        }

        $field = $this->writer->save([
            'farm' => ['name' => 'Fazenda Demonstração', 'municipality' => 'Uberlândia', 'state' => 'MG', 'has_livestock' => true],
            'field' => [
                'name' => 'Talhão 1 (demo)', 'latitude' => -18.9, 'longitude' => -48.55, 'area_ha' => 48.5,
                'irrigated' => false, 'irrigation_mm_day' => null,
                'boundary' => ['type' => 'Polygon', 'coordinates' => [[
                    [-48.554, -18.897], [-48.546, -18.897], [-48.546, -18.903], [-48.554, -18.903], [-48.554, -18.897],
                ]]],
            ],
            'soil' => ['source' => 'unknown'],
            'history' => $snapshot['history'],
            'priorities' => $snapshot['priorities'],
            'constraints' => ['buyer_crops' => ['soja', 'milho']],
        ], $field, ['user_id' => null, 'is_demo' => true]);

        $field->analysis()->updateOrCreate(['field_id' => $field->id], [
            'engine_version' => self::VERSION,
            'climate' => $snapshot['climate'],
            'planting' => $snapshot['planting'],
            'terrain' => null,
            'vegetation' => null,
            'stress' => null,
            'earthdata' => null,
            'computed_at' => now(),
        ]);
        $field->update(['status' => Field::STATUS_READY, 'status_message' => null, 'analyzed_at' => now()]);

        return $field->fresh();
    }
}
