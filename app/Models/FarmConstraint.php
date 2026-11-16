<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class FarmConstraint extends Model
{
    protected $primaryKey = 'farm_id';

    public $incrementing = false;

    protected $fillable = ['farm_id', 'excluded_crops', 'buyer_crops', 'no_buyer_crops', 'missing_equipment', 'notes'];

    protected function casts(): array
    {
        return [
            'excluded_crops' => 'array',
            'buyer_crops' => 'array',
            'no_buyer_crops' => 'array',
            'missing_equipment' => 'array',
        ];
    }
}
