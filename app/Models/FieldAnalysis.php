<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class FieldAnalysis extends Model
{
    protected $fillable = ['field_id', 'engine_version', 'climate', 'terrain', 'vegetation', 'stress', 'earthdata', 'planting', 'computed_at'];

    protected function casts(): array
    {
        return ['climate' => 'array', 'terrain' => 'array', 'vegetation' => 'array', 'stress' => 'array', 'earthdata' => 'array', 'planting' => 'array', 'computed_at' => 'datetime'];
    }

    public function field(): BelongsTo
    {
        return $this->belongsTo(Field::class);
    }
}
