<?php

namespace Database\Seeders;

use App\Models\Crop;
use Illuminate\Database\Seeder;
use RuntimeException;

/**
 * Copia o catálogo do geo-service (fonte única: geo-service/app/catalog/crops.json) para o MySQL,
 * para que o formulário de histórico e restrições use os mesmos códigos (slugs) do motor.
 */
class CropSeeder extends Seeder
{
    public function run(): void
    {
        $path = base_path('geo-service/app/catalog/crops.json');
        $doc = json_decode((string) file_get_contents($path), true) ?? throw new RuntimeException("Catálogo não encontrado em $path");

        foreach ($doc['crops'] as $c) {
            Crop::updateOrCreate(['slug' => $c['slug']], [
                'name_pt' => $c['name_pt'],
                'scientific_name' => $c['scientific_name'] ?? null,
                'family' => $c['family'],
                'category' => $c['category'],
                'traits' => collect($c)->except(['slug', 'name_pt', 'scientific_name', 'family', 'category', 'sources'])->all(),
                'sources' => $c['sources'] ?? [],
            ]);
        }
    }
}
