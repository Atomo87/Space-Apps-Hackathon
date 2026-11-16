<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Models\Field;
use App\Services\FieldWriter;
use Illuminate\Http\RedirectResponse;
use Illuminate\Support\Facades\Cache;

/**
 * Caso de demonstração: talhão próximo a Uberlândia (MG) com soja → milho safrinha → pousio.
 * Coordenada demonstrativa (doc 10), não uma propriedade real.
 *
 * Abre o caso público compartilhado (protegido contra edição e exclusão), criado uma única vez.
 */
class DemoController extends Controller
{
    public function __invoke(FieldWriter $writer): RedirectResponse
    {
        $field = Cache::lock('public-demo-create', 30)->block(10, fn () => $this->publicDemo() ?? $writer->save($this->payload(), null, ['user_id' => null, 'is_demo' => true]));

        return redirect()->route('fields.show', $field)->with('success', 'Exemplo de Uberlândia (MG). Para analisar o seu, use “Cadastrar talhão”.');
    }

    private function publicDemo(): ?Field
    {
        return Field::whereHas('farm', fn ($q) => $q->where('is_demo', true)->whereNull('user_id'))->oldest()->first();
    }

    private function payload(): array
    {
        $y = (int) now()->subMonths(6)->format('Y');

        return [
            'farm' => ['name' => 'Fazenda Demonstração', 'municipality' => 'Uberlândia', 'state' => 'MG', 'has_livestock' => true],
            'field' => [
                // Área agrícola a oeste da cidade: o NDVI MODIS mostra o ciclo de lavoura (verde no verão, baixo no inverno).
                'name' => 'Talhão 1 (demo)', 'latitude' => -18.9, 'longitude' => -48.55, 'area_ha' => 48.5,
                'irrigated' => false, 'irrigation_mm_day' => null,
                'boundary' => ['type' => 'Polygon', 'coordinates' => [[
                    [-48.554, -18.897], [-48.546, -18.897], [-48.546, -18.903], [-48.554, -18.903], [-48.554, -18.897],
                ]]],
            ],
            'soil' => ['source' => 'unknown'],
            'history' => [
                ['crop' => 'soja', 'sown_at' => ($y - 1).'-10-25', 'harvested_at' => $y.'-02-20'],
                ['crop' => 'milho', 'sown_at' => $y.'-02-28', 'harvested_at' => $y.'-07-05'],
            ],
            'priorities' => [
                'save_water' => 4, 'soil_structure' => 3, 'n_fixation' => 2, 'erosion_control' => 4, 'organic_matter' => 3,
                'pest_break' => 3, 'forage' => 2, 'extra_income' => 4, 'market_fit' => 3,
            ],
            'constraints' => ['excluded_crops' => [], 'buyer_crops' => ['soja', 'milho'], 'no_buyer_crops' => [], 'missing_equipment' => []],
        ];
    }
}
