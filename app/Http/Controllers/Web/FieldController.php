<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Http\Requests\SaveFieldRequest;
use App\Models\Crop;
use App\Models\FarmerPriority;
use App\Models\Field;
use App\Services\FieldWriter;
use App\Services\PublicDemo;
use Illuminate\Http\RedirectResponse;
use Illuminate\Support\Facades\Gate;
use Inertia\Inertia;
use Inertia\Response;

class FieldController extends Controller
{
    /** Página inicial (acesso livre): apresentação. A lista de talhões fica em "Meus talhões" (/talhoes). */
    public function index(PublicDemo $demo): Response
    {
        return Inertia::render('Welcome', ['demoRegions' => $demo->options()]);
    }

    /** Tela "Meus talhões": todos os talhões cadastrados, com busca e filtro. */
    public function list(PublicDemo $demo): Response
    {
        return Inertia::render('Fields/Index', $this->fieldList() + ['demoRegions' => $demo->options()]);
    }

    /** @return array{fields: list<array<string,mixed>>, stats: array<string,int|float>} */
    private function fieldList(): array
    {
        $fields = Field::with('farm')->latest('fields.updated_at')->get()->map(fn (Field $f) => [
            'id' => $f->id,
            'name' => $f->farm->isPublicDemo() ? __($f->name) : $f->name,
            'farm' => $f->farm->isPublicDemo() ? __($f->farm->name) : $f->farm->name,
            'municipality' => $f->farm->municipality,
            'state' => $f->farm->state,
            'country_code' => $f->farm->country_code,
            'area_ha' => $f->area_ha,
            'status' => $f->status,
            'analyzed_at' => $f->analyzed_at?->toIso8601String(),
            'is_demo' => $f->farm->is_demo,
        ])->values()->all();

        return [
            'fields' => $fields,
            'stats' => [
                'fields' => count($fields),
                'area_ha' => round((float) collect($fields)->sum('area_ha'), 1),
                'ready' => collect($fields)->where('status', Field::STATUS_READY)->count(),
            ],
        ];
    }

    public function create(): Response
    {
        return Inertia::render('Fields/Form', $this->formProps(null));
    }

    public function store(SaveFieldRequest $request, FieldWriter $writer): RedirectResponse
    {
        $field = $writer->save($request->validated(), null, ['user_id' => null]);

        return redirect()->route('fields.show', $field)->with('success', __('Talhão salvo! Agora vamos buscar os dados da NASA.'));
    }

    public function show(Field $field, PublicDemo $demo): Response
    {
        Gate::authorize('view', $field);
        $field = $demo->prepare($field);
        $field->load(['farm.priorities', 'soil', 'history.crop']);
        $region = $demo->region($field);
        $isPublicDemo = $region !== null;

        return Inertia::render('Fields/Show', [
            'demoRegions' => $isPublicDemo ? $demo->options() : [],
            'field' => [
                'id' => $field->id,
                'name' => $isPublicDemo ? __($field->name) : $field->name,
                'latitude' => $field->latitude,
                'longitude' => $field->longitude,
                'boundary' => $field->boundary,
                'area_ha' => $field->area_ha,
                'irrigated' => $field->irrigated,
                'power_period' => [
                    'start_year' => $field->power_start_year,
                    'end_year' => $field->power_end_year,
                    'first_year' => Field::POWER_FIRST_YEAR,
                    'last_year' => (int) now()->year - 1,
                    'min_years' => Field::POWER_MIN_YEARS,
                ],
                'status' => $field->status,
                'status_message' => $field->status_message !== null ? __($field->status_message) : null,
                'is_demo' => $field->farm->is_demo,
                'is_public_demo' => $isPublicDemo,
                'demo_region' => $region,
                'farm' => [
                    'id' => $field->farm->id,
                    'name' => $isPublicDemo ? __($field->farm->name) : $field->farm->name,
                    ...$field->farm->only(['municipality', 'state', 'country_code']),
                ],
                'soil_source' => $field->soil?->source ?? 'unknown',
                'history' => $field->history->map(fn ($h) => ['crop' => $h->crop->name_pt, 'sown_at' => $h->sown_at->toDateString(), 'harvested_at' => $h->harvested_at->toDateString()]),
                'priorities' => $field->farm->priorities?->weights() ?? array_fill_keys(FarmerPriority::KEYS, 3),
            ],
            'can' => [
                'update' => Gate::allows('update', $field),
                'delete' => Gate::allows('delete', $field),
            ],
        ]);
    }

    public function edit(Field $field): Response
    {
        Gate::authorize('update', $field);

        return Inertia::render('Fields/Form', $this->formProps($field));
    }

    public function update(SaveFieldRequest $request, Field $field, FieldWriter $writer): RedirectResponse
    {
        Gate::authorize('update', $field);
        $writer->save($request->validated(), $field);

        return redirect()->route('fields.show', $field)->with('success', __('Alterações salvas.'));
    }

    public function destroy(Field $field): RedirectResponse
    {
        Gate::authorize('delete', $field);
        $farm = $field->farm;
        $field->delete();
        if ($farm->fields()->doesntExist()) {
            $farm->delete();
        }

        return redirect()->route('home')->with('success', __('Talhão e dados associados excluídos.'));
    }

    private function formProps(?Field $field): array
    {
        $field?->load(['farm.priorities', 'farm.constraints', 'soil', 'history.crop']);
        $equipment = json_decode((string) @file_get_contents(base_path('geo-service/app/catalog/crops.json')), true)['equipment'] ?? [];

        return [
            'crops' => Crop::orderBy('name_pt')->get()->map(fn (Crop $c) => [
                'slug' => $c->slug, 'name' => $c->name_pt, 'category' => $c->category, 'family' => $c->family,
            ]),
            'equipment' => collect($equipment)->map(fn ($label, $key) => ['key' => $key, 'label' => $label])->values(),
            'initial' => $field ? [
                'id' => $field->id,
                'farm' => $field->farm->only(['name', 'municipality', 'state', 'country_code', 'has_livestock']),
                'field' => $field->only(['name', 'latitude', 'longitude', 'boundary', 'area_ha', 'irrigated', 'irrigation_mm_day']),
                'soil' => $field->soil
                    ? $field->soil->only(['source', 'texture', 'clay_pct', 'ph_water', 'organic_matter_pct', 'p_mg_dm3', 'k_cmolc_dm3', 'ctc_cmolc_dm3', 'v_pct']) + ['sampled_at' => $field->soil->sampled_at?->toDateString()]
                    : ['source' => 'unknown'],
                'history' => $field->history->map(fn ($h) => ['crop' => $h->crop->slug, 'sown_at' => $h->sown_at->toDateString(), 'harvested_at' => $h->harvested_at->toDateString()]),
                'priorities' => $field->farm->priorities?->weights() ?? array_fill_keys(FarmerPriority::KEYS, 3),
                'constraints' => $field->farm->constraints?->only(['excluded_crops', 'buyer_crops', 'no_buyer_crops', 'missing_equipment'])
                    ?? ['excluded_crops' => [], 'buyer_crops' => [], 'no_buyer_crops' => [], 'missing_equipment' => []],
            ] : null,
        ];
    }
}
