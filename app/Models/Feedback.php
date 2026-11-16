<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Feedback extends Model
{
    protected $table = 'feedbacks';

    protected $fillable = ['field_id', 'strategy_key', 'verdict', 'comment', 'snapshot'];

    protected function casts(): array
    {
        return ['snapshot' => 'array'];
    }
}
