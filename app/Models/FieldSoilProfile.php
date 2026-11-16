<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class FieldSoilProfile extends Model
{
    protected $fillable = [
        'field_id', 'source', 'sampled_at', 'texture', 'clay_pct', 'ph_water', 'organic_matter_pct',
        'p_mg_dm3', 'k_cmolc_dm3', 'ctc_cmolc_dm3', 'v_pct', 'depth_cm',
    ];

    protected function casts(): array
    {
        return [
            'sampled_at' => 'date',
            'clay_pct' => 'float', 'ph_water' => 'float', 'organic_matter_pct' => 'float',
            'p_mg_dm3' => 'float', 'k_cmolc_dm3' => 'float', 'ctc_cmolc_dm3' => 'float',
            'v_pct' => 'float', 'depth_cm' => 'integer',
        ];
    }

    public function field(): BelongsTo
    {
        return $this->belongsTo(Field::class);
    }
}
