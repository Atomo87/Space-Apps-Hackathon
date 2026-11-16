<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Field extends Model
{
    public const STATUS_PENDING = 'pending';

    public const STATUS_PROCESSING = 'processing';

    public const STATUS_READY = 'ready';

    public const STATUS_ERROR = 'error';

    protected $fillable = [
        'farm_id', 'name', 'latitude', 'longitude', 'boundary', 'area_ha',
        'irrigated', 'irrigation_mm_day', 'power_start_year', 'power_end_year', 'status', 'status_message', 'analyzed_at',
    ];

    /** Menor período aceito: percentis e tendências precisam de uma série razoável. */
    public const POWER_MIN_YEARS = 10;

    public const POWER_FIRST_YEAR = 1981;

    protected function casts(): array
    {
        return [
            'latitude' => 'float',
            'longitude' => 'float',
            'boundary' => 'array',
            'area_ha' => 'float',
            'irrigated' => 'boolean',
            'irrigation_mm_day' => 'float',
            'analyzed_at' => 'datetime',
        ];
    }

    public function farm(): BelongsTo
    {
        return $this->belongsTo(Farm::class);
    }

    public function soil(): HasOne
    {
        return $this->hasOne(FieldSoilProfile::class);
    }

    public function history(): HasMany
    {
        return $this->hasMany(CropHistory::class)->orderBy('sown_at');
    }

    public function analysis(): HasOne
    {
        return $this->hasOne(FieldAnalysis::class);
    }

    public function feedbacks(): HasMany
    {
        return $this->hasMany(Feedback::class);
    }
}
