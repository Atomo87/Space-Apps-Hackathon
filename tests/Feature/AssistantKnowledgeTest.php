<?php

use App\Models\AssistantKnowledgeEntry;
use App\Models\Farm;
use App\Models\Field;
use App\Services\Assistant\KnowledgeBase;
use Database\Seeders\AssistantKnowledgeSeeder;
use Illuminate\Support\Facades\Http;

it('answers a published alias without using Gemini, NASA or the geo-service', function () {
    $this->seed(AssistantKnowledgeSeeder::class);
    Http::fake();
    $farm = Farm::create(['name' => 'Test farm', 'is_demo' => false]);
    $field = Field::create(['farm_id' => $farm->id, 'name' => 'T1', 'latitude' => -18.9, 'longitude' => -48.3, 'status' => Field::STATUS_PENDING]);

    $this->postJson("/api/v1/fields/{$field->id}/ask", ['question' => '  WHAT DOES NDVI MEAN!! '])
        ->assertOk()
        ->assertJsonPath('mode', 'reference')
        ->assertJsonPath('claims.0.ref_ids.0', 'knowledge.ndvi')
        ->assertJsonPath('refs.0.locale', 'en-US')
        ->assertJsonPath('evidence_count', 0);

    Http::assertNothingSent();
});

it('loads only published references for the current language and uses reviewed entries in RAG', function () {
    $this->seed(AssistantKnowledgeSeeder::class);
    AssistantKnowledgeEntry::create([
        'locale' => 'en-US', 'slug' => 'draft', 'question' => 'A special unpublished NDVI question?',
        'answer' => 'Draft answer.', 'source' => 'Internal draft',
    ]);
    $kb = app(KnowledgeBase::class);
    app()->setLocale('en');
    expect($kb->matchAnswer('O que é NDVI?'))->toBeNull()
        ->and($kb->matchAnswer('A special unpublished NDVI question?'))->toBeNull()
        ->and($kb->matchAnswer('What is the NDVI for this field?'))->toBeNull()
        ->and(collect($kb->search('How does GeoSafra use NDVI to track greenness?'))->pluck('id')->all())->toContain('knowledge.ndvi');

    app()->setLocale('pt_BR');
    expect($kb->matchAnswer('O QUE E NDVI?')['locale'])->toBe('pt-BR');
});
