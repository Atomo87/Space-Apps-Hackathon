<?php

namespace App\Services;

use App\Models\Crop;
use App\Models\Field;
use Database\Seeders\CropSeeder;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

class PublicDemo
{
    public const DEFAULT_REGION = 'uberlandia';

    private const REGIONS = [
        'uberlandia' => ['country' => 'BR', 'state' => 'MG', 'city' => 'Uberlândia', 'label' => 'Uberlândia, Brasil', 'snapshot' => 'public-demo.json', 'version' => 'demo-synthetic-v1'],
        'texas' => ['country' => 'US', 'state' => 'TX', 'city' => 'Lubbock', 'label' => 'Lubbock TX - US', 'snapshot' => 'public-demo-texas.json', 'version' => 'demo-texas-v1'],
    ];

    private array $snapshots = [];

    public function __construct(private readonly FieldWriter $writer) {}

    public function options(): array
    {
        return collect(self::REGIONS)->map(fn ($region, $key) => ['key' => $key, 'label' => __($region['label'])])->values()->all();
    }

    public function open(string $key = self::DEFAULT_REGION): Field
    {
        $region = self::REGIONS[$key];

        return Cache::lock('public-demo-create:'.$key, 30)->block(10, function () use ($key, $region) {
            $field = Field::whereHas('farm', fn ($q) => $q->where('is_demo', true)->whereNull('user_id')
                ->where('country_code', $region['country'])->where('state', $region['state'])->where('municipality', $region['city']))
                ->oldest()->orderBy('id')->first();

            return $field ? $this->prepare($field) : DB::transaction(fn () => $this->install($key, null));
        });
    }

    public function appliesTo(Field $field): bool
    {
        return $this->region($field) !== null;
    }

    public function region(Field $field): ?string
    {
        $farm = $field->farm;
        if (! $farm->isPublicDemo()) {
            return null;
        }

        foreach (self::REGIONS as $key => $region) {
            if ($farm->country_code === $region['country'] && $farm->state === $region['state'] && $farm->municipality === $region['city']) {
                return $key;
            }
        }

        return null;
    }

    public function prepare(Field $field): Field
    {
        $key = $this->region($field);
        if ($key === null || $this->isReady($field, $key)) {
            return $field;
        }

        return DB::transaction(function () use ($field, $key) {
            $locked = Field::lockForUpdate()->findOrFail($field->id);

            return $this->isReady($locked, $key) ? $locked : $this->install($key, $locked);
        });
    }

    public function isBaseline(string $key, array $payload): bool
    {
        return $payload['scenario']['rain_delta_pct'] == 0
            && $payload['scenario']['temp_delta_c'] == 0
            && $payload['priorities'] == $this->snapshot($key)['priorities'];
    }

    public function baseline(string $key): array
    {
        return $this->snapshot($key)['analyses'][app()->isLocale('pt_BR') ? 'pt-BR' : 'en-US'];
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

    private function isReady(Field $field, string $key): bool
    {
        return $field->status === Field::STATUS_READY && $field->analysis?->engine_version === self::REGIONS[$key]['version'];
    }

    private function snapshot(string $key): array
    {
        return $this->snapshots[$key] ??= json_decode(
            file_get_contents(database_path('data/'.self::REGIONS[$key]['snapshot'])), true, 512, JSON_THROW_ON_ERROR,
        );
    }

    private function install(string $key, ?Field $field): Field
    {
        $snapshot = $this->snapshot($key);
        $region = self::REGIONS[$key];
        $buyerCrops = $snapshot['buyer_crops'] ?? ['soja', 'milho'];
        $historyCrops = array_unique(array_column($snapshot['history'], 'crop'));
        if (Crop::whereIn('slug', $historyCrops)->count() !== count($historyCrops)) {
            app(CropSeeder::class)->run();
        }

        $field = $this->writer->save([
            'farm' => [
                'name' => $snapshot['farm_name'] ?? 'Fazenda Demonstração',
                'municipality' => $region['city'], 'state' => $region['state'], 'country_code' => $region['country'],
                'has_livestock' => $snapshot['has_livestock'] ?? true,
            ],
            'field' => $snapshot['field'] ?? [
                'name' => 'Talhão 1 (demo)', 'latitude' => -18.9, 'longitude' => -48.55, 'area_ha' => 48.5,
                'irrigated' => false, 'irrigation_mm_day' => null,
                'boundary' => ['type' => 'Polygon', 'coordinates' => [[
                    [-48.554, -18.897], [-48.546, -18.897], [-48.546, -18.903], [-48.554, -18.903], [-48.554, -18.897],
                ]]],
            ],
            'soil' => ['source' => 'unknown'],
            'history' => $snapshot['history'],
            'priorities' => $snapshot['priorities'],
            'constraints' => ['buyer_crops' => $buyerCrops],
        ], $field, ['user_id' => null, 'is_demo' => true]);

        $field->analysis()->updateOrCreate(['field_id' => $field->id], [
            'engine_version' => $region['version'],
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
