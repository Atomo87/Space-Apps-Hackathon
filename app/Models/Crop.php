<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Crop extends Model
{
    protected $fillable = ['slug', 'name_pt', 'scientific_name', 'family', 'category', 'traits', 'sources'];

    protected function casts(): array
    {
        return ['traits' => 'array', 'sources' => 'array'];
    }
}
