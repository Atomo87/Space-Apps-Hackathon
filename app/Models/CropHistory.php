<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CropHistory extends Model
{
    protected $table = 'crop_history';

    protected $fillable = ['field_id', 'crop_id', 'sown_at', 'harvested_at', 'yield_t_ha', 'notes'];

    protected function casts(): array
    {
        return ['sown_at' => 'date', 'harvested_at' => 'date', 'yield_t_ha' => 'float'];
    }

    public function field(): BelongsTo
    {
        return $this->belongsTo(Field::class);
    }

    public function crop(): BelongsTo
    {
        return $this->belongsTo(Crop::class);
    }
}
