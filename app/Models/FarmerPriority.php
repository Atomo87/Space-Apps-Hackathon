<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class FarmerPriority extends Model
{
    /** Critérios ajustáveis pelo produtor (0–5), na mesma ordem do motor. */
    public const KEYS = [
        'save_water', 'soil_structure', 'n_fixation', 'erosion_control', 'organic_matter',
        'pest_break', 'forage', 'extra_income', 'market_fit',
    ];

    protected $primaryKey = 'farm_id';

    public $incrementing = false;

    protected $fillable = ['farm_id', ...self::KEYS];

    protected function casts(): array
    {
        return array_fill_keys(self::KEYS, 'integer');
    }

    /** @return array<string,int> */
    public function weights(): array
    {
        return array_map('intval', $this->only(self::KEYS));
    }
}
