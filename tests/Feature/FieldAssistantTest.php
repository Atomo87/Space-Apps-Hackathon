<?php

use App\Models\Farm;
use App\Models\Field;
use App\Services\Assistant\EvidenceCatalog;
use App\Services\Assistant\FieldAssistant;
use App\Services\Assistant\KnowledgeBase;
use Illuminate\Support\Facades\Http;

// As perguntas destes testes são em português: a base de conhecimento segue o idioma da aplicação.
beforeEach(fn () => app()->setLocale('pt_BR'));

function analysisFixture(): array
{
    return [
        'diagnosis' => [
            'source' => ['period' => ['start' => '2005-01-01', 'end' => '2025-12-31', 'years' => 21]],
            'monthly' => [['month' => 1, 'name' => 'jan', 'rain_mm' => ['mean' => 250], 'water_balance_mm' => 100, 'frost_prob' => 0, 'heat_days_34' => 1]],
            'season' => ['pct_seasons_dry_spell_ge_10' => 55, 'dry_spell_p90_days' => 14.3],
            'extremes' => ['annual_max_1day_mm_mean' => 80],
            'trends' => ['tmax_c' => ['per_decade' => 0.4, 'p_value' => 0.02], 'rain_mm' => ['per_decade' => -128, 'p_value' => 0.3]],
            'recent' => [],
            'calendar' => [],
            'earthdata' => ['grace' => ['trend_cm_per_decade' => -9.0, 'trend_p_value' => 0.03, 'coverage' => ['start' => '2002-04-17', 'end' => '2026-09-16']]],
        ],
        'strategies' => [
            ['label' => 'A', 'is_current' => true, 'title' => 'Soja → Milho → pousio', 'score' => 61],
            ['label' => 'B', 'is_current' => false, 'title' => 'Soja → Milho safrinha + braquiária', 'score' => 78],
        ],
    ];
}

it('monta fatos com indicador, valor, período e fonte', function () {
    app()->setLocale('pt_BR');
    $facts = EvidenceCatalog::build(analysisFixture())->all();

    expect($facts['clima.veranico_10'])->toMatchArray(['value' => 55, 'unit' => '%', 'period' => '2005–2025'])
        ->and($facts['clima.veranico_10']['source'])->toContain('NASA POWER')
        ->and($facts['grace.tendencia']['value'])->toBe(-9.0)
        ->and($facts['grace.tendencia']['period'])->toBe('2002-04-17 a 2026-09-16')
        ->and($facts['estrategia.B']['value'])->toBe(78);
});

it('recupera trechos relevantes da base de conhecimento (BM25)', function () {
    $hits = app(KnowledgeBase::class)->search('o que é veranico?', 3);

    expect($hits)->not->toBeEmpty()->and($hits[0]['id'])->toBe('glossario.veranico');
});

it('aceita só afirmações com evidência citada e números que batem com ela', function () {
    app()->setLocale('pt_BR');
    $evidence = EvidenceCatalog::build(analysisFixture());
    $out = app(FieldAssistant::class)->validate([
        'claims' => [
            ['text' => 'Em 55% das safras houve veranico de 10 dias ou mais (2005–2025, NASA POWER).', 'fact_ids' => ['clima.veranico_10'], 'ref_ids' => []],
            ['text' => 'A água da região caiu 9 cm por década.', 'fact_ids' => ['grace.tendencia'], 'ref_ids' => []],
            ['text' => 'A produtividade vai subir 30%.', 'fact_ids' => ['estrategia.B'], 'ref_ids' => []],   // número inventado
            ['text' => 'Plante em outubro.', 'fact_ids' => ['nao.existe'], 'ref_ids' => []],               // citação inexistente
        ],
        'limitations' => ['Apoia, não substitui.'],
        'follow_up_questions' => [],
    ], $evidence, []);

    expect($out['claims'])->toHaveCount(2)
        ->and($out['rejected'])->toHaveCount(2)
        ->and($out['rejected'][0]['reason'])->toContain('30')
        ->and($out['rejected'][1]['reason'])->toBe('sem evidência citada');
});

it('responde pelo endpoint com IA e devolve as evidências citadas', function () {
    config([
        'geosafra.geo_service.url' => 'http://geo.test',
        'geosafra.ai' => ['enabled' => true, 'key' => 'chave-teste', 'model' => 'gemini-teste', 'endpoint' => 'https://gemini.test/v1beta'],
        'geosafra.firms.key' => '',
    ]);
    $farm = Farm::create(['name' => 'Fazenda', 'is_demo' => false]);
    $field = Field::create(['farm_id' => $farm->id, 'name' => 'T1', 'latitude' => 40.0, 'longitude' => -100.0, 'status' => Field::STATUS_READY]);
    $field->analysis()->create(['engine_version' => 't', 'climate' => ['monthly' => []], 'computed_at' => now()]);

    $ai = ['claims' => [
        ['text' => 'Em 55% das safras houve veranico de 10 dias ou mais.', 'fact_ids' => ['clima.veranico_10'], 'ref_ids' => ['glossario.veranico']],
        ['text' => 'A soja rende 90 sacas.', 'fact_ids' => [], 'ref_ids' => []],
    ], 'limitations' => ['Apoia, não substitui o técnico.'], 'follow_up_questions' => ['E a safrinha?']];
    Http::fake([
        'geo.test/v1/analysis' => Http::response(analysisFixture()),
        'gemini.test/*' => Http::response(['candidates' => [['finishReason' => 'STOP', 'content' => ['parts' => [['text' => json_encode($ai)]]]]]]),
    ]);

    $this->withCredentials()->withUnencryptedCookie('geosafra_locale', 'pt-BR')
        ->postJson("/api/v1/fields/{$field->id}/ask", ['question' => 'Qual o risco de veranico?'])
        ->assertOk()
        ->assertHeader('Content-Language', 'pt-BR')
        ->assertJson(['mode' => 'ai', 'model' => 'gemini-teste'])
        ->assertJsonCount(1, 'claims')
        ->assertJsonCount(1, 'rejected')
        ->assertJson(['facts' => ['clima.veranico_10' => ['period' => '2005–2025', 'unit' => '%']]]);

    Http::assertSent(fn ($r) => str_contains($r->url(), 'gemini.test') && $r->hasHeader('x-goog-api-key', 'chave-teste')
        && str_contains($r['contents'][0]['parts'][0]['text'], 'clima.veranico_10'));
    Http::assertSent(fn ($r) => str_contains($r->url(), 'geo.test') && $r->hasHeader('Accept-Language', 'pt-BR'));
});

it('sem IA configurada, responde só com as evidências', function () {
    config(['geosafra.geo_service.url' => 'http://geo.test', 'geosafra.ai.key' => '', 'geosafra.firms.key' => '']);
    $farm = Farm::create(['name' => 'Fazenda', 'is_demo' => false]);
    $field = Field::create(['farm_id' => $farm->id, 'name' => 'T1', 'latitude' => 40.0, 'longitude' => -100.0, 'status' => Field::STATUS_READY]);
    Http::fake(['geo.test/v1/analysis' => Http::response(analysisFixture())]);

    $this->postJson("/api/v1/fields/{$field->id}/ask", ['question' => 'What is the risk of a dry spell?'])
        ->assertOk()
        ->assertHeader('Content-Language', 'en-US')
        ->assertJson(['mode' => 'evidence'])
        ->assertJsonPath('claims.0.fact_ids.0', fn ($id) => str_starts_with($id, 'clima.veranico'))
        ->assertJsonPath('refs.0.locale', 'en-US');
});
