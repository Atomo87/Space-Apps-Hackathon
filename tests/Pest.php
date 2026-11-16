<?php

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

pest()->extend(TestCase::class)
    ->use(RefreshDatabase::class)
    ->in('Feature');

/** Corpo válido de cadastro de talhão (mesmo formato do formulário). */
function fieldPayload(array $overrides = []): array
{
    return array_replace_recursive([
        'farm' => ['name' => 'Sítio Teste', 'municipality' => 'Uberlândia', 'state' => 'MG', 'has_livestock' => false],
        'field' => ['name' => 'T1', 'latitude' => -18.9186, 'longitude' => -48.2772, 'boundary' => null, 'area_ha' => 10, 'irrigated' => false, 'irrigation_mm_day' => null],
        'soil' => ['source' => 'unknown'],
        'history' => [
            ['crop' => 'soja', 'sown_at' => '2024-10-20', 'harvested_at' => '2025-02-15'],
            ['crop' => 'milho', 'sown_at' => '2025-02-25', 'harvested_at' => '2025-06-30'],
        ],
        'priorities' => ['save_water' => 4, 'soil_structure' => 3, 'n_fixation' => 2, 'erosion_control' => 4, 'organic_matter' => 3, 'pest_break' => 3, 'forage' => 2, 'extra_income' => 4, 'market_fit' => 3],
        'constraints' => ['excluded_crops' => [], 'buyer_crops' => ['soja'], 'no_buyer_crops' => [], 'missing_equipment' => []],
    ], $overrides);
}
