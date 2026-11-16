<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AssistantKnowledgeEntry extends Model
{
    protected $fillable = ['locale', 'slug', 'question', 'aliases', 'answer', 'source', 'source_url', 'published_at'];

    protected function casts(): array
    {
        return ['aliases' => 'array', 'published_at' => 'datetime'];
    }

    public function toReference(): array
    {
        return [
            'id' => 'knowledge.'.$this->slug,
            'title' => $this->question,
            'text' => $this->answer,
            'source' => $this->source,
            'url' => $this->referenceUrl(),
            'locale' => $this->locale,
        ];
    }

    private function referenceUrl(): ?string
    {
        if ($this->source_url === '/metodologia') {
            return url($this->source_url);
        }
        if ($this->source_url && preg_match('~^https?://~i', $this->source_url) && filter_var($this->source_url, FILTER_VALIDATE_URL)) {
            return $this->source_url;
        }

        return null;
    }
}
