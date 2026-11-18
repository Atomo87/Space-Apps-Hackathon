<?php

use App\Models\Field;
use App\Models\User;
use Database\Seeders\CropSeeder;
use Illuminate\Support\Facades\Http;
use Inertia\Testing\AssertableInertia as Assert;

beforeEach(function () {
    $this->seed(CropSeeder::class);
    config(['geosafra.geo_service.url' => 'http://geo.test']);
    $this->user = User::factory()->create();
    $this->actingAs($this->user);
});

it('salva o talhão com histórico, prioridades e restrições (A2)', function () {
    $this->post('/talhoes', fieldPayload())->assertRedirect();

    $field = Field::with(['history', 'farm.priorities', 'farm.constraints'])->sole();
    expect($field->status)->toBe('pending')
        ->and($field->farm->user_id)->toBeNull() // acesso livre: sem dono
        ->and($field->farm->country_code)->toBe('BR')
        ->and($field->history)->toHaveCount(2)
        ->and($field->farm->priorities->save_water)->toBe(4)
        ->and($field->farm->constraints->buyer_crops)->toBe(['soja']);
});

it('mantém cidade, região e país internacionais ao cadastrar e editar um talhão', function () {
    $payload = fieldPayload([
        'farm' => ['municipality' => 'Fresno', 'state' => 'California', 'country_code' => 'US'],
        'field' => ['latitude' => 36.7477, 'longitude' => -119.7724],
    ]);
    $this->post('/talhoes', $payload)->assertRedirect();

    $field = Field::sole();
    $this->get("/talhoes/{$field->id}/editar")->assertInertia(fn (Assert $page) => $page
        ->component('Fields/Form')
        ->where('initial.farm.municipality', 'Fresno')
        ->where('initial.farm.state', 'California')
        ->where('initial.farm.country_code', 'US')
        ->where('initial.field.latitude', 36.7477));

    $id = $field->id;
    $payload['farm'] = array_replace($payload['farm'], ['municipality' => 'Pergamino', 'state' => 'Buenos Aires', 'country_code' => 'AR']);
    $this->put("/talhoes/{$id}", $payload)->assertRedirect();
    $this->assertDatabaseHas('farms', ['id' => $field->farm_id, 'municipality' => 'Pergamino', 'state' => 'Buenos Aires', 'country_code' => 'AR']);
});

it('rejeita colheita antes do plantio', function () {
    $this->post('/talhoes', fieldPayload(['history' => [['crop' => 'soja', 'sown_at' => '2025-03-01', 'harvested_at' => '2025-01-01']]]))
        ->assertSessionHasErrors('history.0.harvested_at');
});

it('processa via geo-service e repassa a análise (B6)', function () {
    Http::fake([
        'geo.test/v1/climate-profile' => Http::response(['monthly' => [['month' => 1]], 'source' => [], 'engine_version' => 'test']),
        'geo.test/v1/terrain' => Http::response(['dataset' => 'SRTM GL1', 'slope_pct' => ['mean' => 4.2, 'p90' => 6.0, 'max' => 7.1], 'ls_relative' => 1.3]),
        'geo.test/v1/vegetation' => Http::response(['dataset' => 'MODIS', 'monthly' => [], 'low_green_months' => [7, 8]]),
        'geo.test/v1/stress' => Http::response(['lst' => ['hot_months' => [9]], 'et' => ['ratio' => 0.31]]),
        'geo.test/v1/earthdata' => Http::response(['smap' => ['dry_months' => [8]], 'gpm' => null, 'ecostress' => null, 'grace' => ['trend_cm_per_decade' => -9.0], 'notes' => []]),
        'geo.test/v1/analysis' => Http::response(['strategies' => [['label' => 'A']], 'diagnosis' => [], 'disclaimer' => 'apoia']),
    ]);
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();

    // Responde na hora ("processing") e termina depois da resposta, em segundo plano.
    $this->postJson("/api/v1/fields/{$field->id}/process")->assertAccepted()->assertJson(['status' => 'processing']);
    $this->getJson("/api/v1/fields/{$field->id}/status")->assertOk()->assertJson(['status' => 'ready']);
    $this->getJson("/api/v1/fields/{$field->id}/analysis?rain_delta_pct=-20&temp_delta_c=1")
        ->assertOk()->assertJsonPath('strategies.0.label', 'A');

    Http::assertSent(fn ($r) => str_ends_with($r->url(), '/v1/analysis')
        && $r['scenario']['rain_delta_pct'] == -20
        && $r['history'][0]['crop'] === 'soja'
        && $r['priorities']['save_water'] === 4
        && $r['terrain']['slope_pct']['mean'] == 4.2
        && $r['vegetation']['low_green_months'] === [7, 8]
        && $r['stress']['et']['ratio'] == 0.31
        && $r['earthdata']['grace']['trend_cm_per_decade'] == -9.0);
});

it('consulta as fontes de novo quando o recibo do geo-service vence', function () {
    $stale = ['detail' => 'Perfil invalido ou insuficiente. Consulte novamente as fontes neste servidor, sem alterar os perfis e mantendo o mesmo local.'];
    Http::fake([
        'geo.test/v1/climate-profile' => Http::sequence()
            ->push(['monthly' => [], 'source' => [], 'engine_version' => 'test', '_receipt' => ['id' => 'velho']])
            ->push(['monthly' => [], 'source' => [], 'engine_version' => 'test', '_receipt' => ['id' => 'novo']]),
        'geo.test/v1/terrain' => Http::response(['slope_pct' => ['mean' => 2.0]]),
        'geo.test/v1/vegetation' => Http::response(['monthly' => []]),
        'geo.test/v1/stress' => Http::response(['lst' => null, 'et' => null]),
        'geo.test/v1/earthdata' => Http::response(['detail' => 'sem token'], 502),
        'geo.test/v1/analysis' => Http::sequence()
            ->push($stale, 422)
            ->push(['strategies' => [['label' => 'A']], 'diagnosis' => []]),
    ]);
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();
    $this->postJson("/api/v1/fields/{$field->id}/process")->assertAccepted();

    // Recibo vencido: a API avisa que está atualizando e renova as fontes em segundo plano.
    $this->getJson("/api/v1/fields/{$field->id}/analysis")->assertStatus(409)->assertJsonPath('field_status', 'processing');
    $this->getJson("/api/v1/fields/{$field->id}/analysis")->assertOk()->assertJsonPath('strategies.0.label', 'A');

    expect($field->refresh()->status)->toBe('ready')
        ->and($field->analysis->climate['_receipt']['id'])->toBe('novo');
    Http::assertSent(fn ($r) => str_ends_with($r->url(), '/v1/analysis') && ($r['climate']['_receipt']['id'] ?? null) === 'novo'
        && $r['field']['latitude'] === round($field->latitude, 4));
});

it('traduz respostas legadas e mantém o cache separado por idioma', function () {
    $finding = [
        'key' => 'bare_soil',
        'text' => 'Pelo seu histórico, o solo fica descoberto em jul, ago, set e out (~118 dias no último ano).',
        'datasets' => ['Histórico informado'],
        'period' => 'últimos 12 meses',
    ];
    Http::fake(['geo.test/v1/analysis' => Http::response(['diagnosis' => ['highlights' => [$finding]]])]);
    $this->post('/talhoes', fieldPayload())->assertRedirect();
    $field = Field::sole();
    $field->update(['status' => Field::STATUS_READY]);
    $path = "/api/v1/fields/{$field->id}/analysis";

    $this->getJson($path)->assertOk()->assertHeader('Content-Language', 'en-US')
        ->assertJsonPath('diagnosis.highlights.0.text', 'Your crop history indicates bare soil in Jul, Aug, Sep and Oct (~118 days in the last year).')
        ->assertJsonPath('diagnosis.highlights.0.datasets.0', 'Provided crop history')
        ->assertJsonPath('diagnosis.highlights.0.period', 'last 12 months');
    $this->withCredentials()->withUnencryptedCookie('geosafra_locale', 'pt-BR')->getJson($path)->assertOk()
        ->assertHeader('Content-Language', 'pt-BR')
        ->assertJsonPath('diagnosis.highlights.0', $finding);
    $this->withUnencryptedCookie('geosafra_locale', 'en-US')->getJson($path)->assertOk()
        ->assertJsonPath('diagnosis.highlights.0.period', 'last 12 months');

    Http::assertSentCount(2);
});

it('segue a análise sem relevo nem NDVI quando esses serviços falham', function () {
    Http::fake([
        'geo.test/v1/climate-profile' => Http::response(['monthly' => [['month' => 1]], 'source' => [], 'engine_version' => 'test']),
        'geo.test/v1/terrain' => Http::response(['detail' => 'Falha na elevação'], 502),
        'geo.test/v1/vegetation' => Http::response(['detail' => 'Falha no NDVI'], 502),
        'geo.test/v1/stress' => Http::response(['detail' => 'Falha no estresse'], 502),
        'geo.test/v1/earthdata' => Http::response(['detail' => 'Token Earthdata não configurado'], 502),
    ]);
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();

    $this->postJson("/api/v1/fields/{$field->id}/process")->assertAccepted();
    expect($field->refresh()->status)->toBe('ready');
    $analysis = $field->analysis()->first();
    expect($analysis->terrain)->toBeNull()->and($analysis->vegetation)->toBeNull()->and($analysis->stress)->toBeNull()->and($analysis->earthdata)->toBeNull();
});

it('refaz a análise quando o contorno do talhão muda', function () {
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();
    $field->update(['status' => Field::STATUS_READY]);
    $poly = ['type' => 'Polygon', 'coordinates' => [[[-48.28, -18.91], [-48.27, -18.91], [-48.27, -18.92], [-48.28, -18.91]]]];

    $this->put("/talhoes/{$field->id}", fieldPayload(['field' => ['boundary' => $poly]]))->assertRedirect();
    expect($field->refresh()->status)->toBe(Field::STATUS_PENDING);
});

it('marca erro quando o geo-service falha', function () {
    Http::fake(['geo.test/*' => Http::response(['detail' => 'Falha na NASA POWER'], 502)]);
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();

    $this->postJson("/api/v1/fields/{$field->id}/process")->assertAccepted();
    $this->getJson("/api/v1/fields/{$field->id}/status")->assertJson(['status' => 'error']);
    expect($field->refresh()->status_message)->toContain('NASA');
});

it('atualiza prioridades (B5 — rastreável)', function () {
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();
    $p = fieldPayload()['priorities'];
    $p['forage'] = 5;

    $this->putJson("/api/v1/farms/{$field->farm_id}/priorities", $p)->assertOk();
    expect($field->farm->priorities()->first()->forage)->toBe(5);
});

it('depois de retomar sem sucesso, libera o "Tentar de novo" (servidor matou o PHP)', function () {
    $this->post('/talhoes', fieldPayload());
    $field = Field::sole();
    $field->update(['status' => Field::STATUS_PROCESSING, 'status_message' => 'Consultando dados da NASA POWER…']);
    Field::whereKey($field->id)->update(['updated_at' => now()->subMinutes(20)]);
    cache()->put("field-resumes-{$field->id}", 2); // as retomadas automáticas já foram usadas

    $this->getJson("/api/v1/fields/{$field->id}/status")
        ->assertOk()
        ->assertJson(['status' => 'error'])
        ->assertJsonPath('message', fn ($m) => str_contains($m, 'interrupted'));
    expect($field->refresh()->status_message)->toContain('interrompido'); // gravada em português, traduzida na saída
});
