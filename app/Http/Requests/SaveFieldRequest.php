<?php

namespace App\Http\Requests;

use App\Models\FarmerPriority;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Validator;

class SaveFieldRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        $priorityRules = collect(FarmerPriority::KEYS)->mapWithKeys(fn ($k) => ["priorities.$k" => ['required', 'integer', 'between:0,5']])->all();

        return [
            'farm.name' => ['required', 'string', 'max:150'],
            'farm.municipality' => ['nullable', 'string', 'max:150'],
            'farm.state' => ['nullable', 'string', 'size:2'],
            'farm.has_livestock' => ['boolean'],

            'field.name' => ['required', 'string', 'max:100'],
            'field.latitude' => ['required', 'numeric', 'between:-90,90'],
            'field.longitude' => ['required', 'numeric', 'between:-180,180'],
            'field.boundary' => ['nullable', 'array'],
            'field.boundary.type' => ['required_with:field.boundary', 'in:Polygon'],
            'field.boundary.coordinates' => ['required_with:field.boundary', 'array'],
            'field.area_ha' => ['nullable', 'numeric', 'min:0', 'max:100000'],
            'field.irrigated' => ['boolean'],
            'field.irrigation_mm_day' => ['nullable', 'required_if:field.irrigated,true', 'numeric', 'between:0,20'],

            'soil.source' => ['required', 'in:lab_analysis,farmer_estimate,unknown'],
            'soil.texture' => ['nullable', 'in:arenosa,media,argilosa,muito_argilosa'],
            'soil.clay_pct' => ['nullable', 'numeric', 'between:0,100'],
            'soil.ph_water' => ['nullable', 'numeric', 'between:3,9'],
            'soil.organic_matter_pct' => ['nullable', 'numeric', 'between:0,20'],
            'soil.p_mg_dm3' => ['nullable', 'numeric', 'min:0'],
            'soil.k_cmolc_dm3' => ['nullable', 'numeric', 'min:0'],
            'soil.ctc_cmolc_dm3' => ['nullable', 'numeric', 'min:0'],
            'soil.v_pct' => ['nullable', 'numeric', 'between:0,100'],
            'soil.sampled_at' => ['nullable', 'date'],

            'history' => ['array', 'max:20'],
            'history.*.crop' => ['required', 'string', 'exists:crops,slug'],
            'history.*.sown_at' => ['required', 'date'],
            'history.*.harvested_at' => ['required', 'date', 'after:history.*.sown_at'],

            ...$priorityRules,

            'constraints.excluded_crops' => ['array'],
            'constraints.excluded_crops.*' => ['string', 'exists:crops,slug'],
            'constraints.buyer_crops' => ['array'],
            'constraints.buyer_crops.*' => ['string', 'exists:crops,slug'],
            'constraints.no_buyer_crops' => ['array'],
            'constraints.no_buyer_crops.*' => ['string', 'exists:crops,slug'],
            'constraints.missing_equipment' => ['array'],
            'constraints.missing_equipment.*' => ['string', 'max:60'],
        ];
    }

    public function after(): array
    {
        return [function (Validator $v) {
            $buyer = $this->input('constraints.buyer_crops', []);
            $noBuyer = $this->input('constraints.no_buyer_crops', []);
            if (array_intersect($buyer, $noBuyer)) {
                $v->errors()->add('constraints.buyer_crops', __('Uma cultura não pode ter e não ter comprador ao mesmo tempo.'));
            }
        }];
    }

    public function attributes(): array
    {
        return [
            'farm.name' => 'nome da propriedade',
            'field.name' => __('nome do talhão'),
            'field.latitude' => 'latitude',
            'field.longitude' => 'longitude',
            'field.irrigation_mm_day' => __('capacidade de irrigação'),
            'history.*.crop' => 'cultura',
            'history.*.sown_at' => 'data de plantio',
            'history.*.harvested_at' => 'data de colheita',
        ];
    }

    public function messages(): array
    {
        return [
            'history.*.harvested_at.after' => 'A colheita precisa ser depois do plantio.',
            'field.latitude.required' => __('Marque o talhão no mapa ou informe a coordenada.'),
        ];
    }
}
