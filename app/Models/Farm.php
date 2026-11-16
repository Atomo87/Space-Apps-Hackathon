<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Farm extends Model
{
    protected $fillable = ['user_id', 'is_demo', 'name', 'municipality', 'state', 'country_code', 'has_livestock'];

    protected function casts(): array
    {
        return ['has_livestock' => 'boolean', 'is_demo' => 'boolean'];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function fields(): HasMany
    {
        return $this->hasMany(Field::class);
    }

    public function priorities(): HasOne
    {
        return $this->hasOne(FarmerPriority::class);
    }

    public function constraints(): HasOne
    {
        return $this->hasOne(FarmConstraint::class);
    }

    public function isOwnedBy(?User $user): bool
    {
        return $user !== null && $this->user_id === $user->id;
    }

    /** Caso público de demonstração (sem dono): qualquer visitante pode ver, ninguém altera. */
    public function isPublicDemo(): bool
    {
        return $this->is_demo && $this->user_id === null;
    }
}
