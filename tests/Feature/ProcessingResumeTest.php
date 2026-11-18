<?php

use App\Jobs\AnalyzeFieldJob;
use App\Models\Farm;
use App\Models\Field;
use Illuminate\Support\Facades\Http;

beforeEach(fn () => config(['geosafra.geo_service.url' => 'http://geo.test']));

function resumeField(): Field
{
    $farm = Farm::create(['name' => 'Fazenda', 'is_demo' => false]);

    return Field::create(['farm_id' => $farm->id, 'name' => 'T1', 'latitude' => -18.9, 'longitude' => -48.55, 'status' => Field::STATUS_PENDING]);
}

it('mostra andamento e tempo gravados no servidor enquanto processa', function () {
    $field = resumeField();
    $field->update(['status' => Field::STATUS_PROCESSING, 'status_message' => AnalyzeFieldJob::STEPS['stress'][0]]);
    cache()->put("field-process-started-{$field->id}", now()->subSeconds(90)->timestamp);

    $this->getJson("/api/v1/fields/{$field->id}/status")
        ->assertOk()
        ->assertJson(['status' => 'processing', 'progress' => 55])
        ->assertJsonPath('elapsed_s', fn ($s) => $s >= 90 && $s < 100);
});

it('mostra a etapa do processamento no idioma escolhido', function () {
    $field = resumeField();
    $field->update(['status' => Field::STATUS_PROCESSING, 'status_message' => AnalyzeFieldJob::STEPS['earthdata'][0]]);
    $path = "/api/v1/fields/{$field->id}/status";

    $this->getJson($path)->assertJson(['message' => 'Reading SMAP, GPM, ECOSTRESS and GRACE-FO (NASA Earthdata)…', 'progress' => 68]);
    $this->get("/talhoes/{$field->id}")->assertInertia(fn ($page) => $page->where('field.status_message', 'Reading SMAP, GPM, ECOSTRESS and GRACE-FO (NASA Earthdata)…'));
    $this->withCredentials()->withUnencryptedCookie('geosafra_locale', 'pt-BR')->getJson($path)
        ->assertJson(['message' => 'Lendo SMAP, GPM, ECOSTRESS e GRACE-FO (NASA Earthdata)…', 'progress' => 68]);
});

it('retoma sozinho um processamento interrompido, sem refazer as etapas já gravadas', function () {
    Http::fake([
        'geo.test/v1/climate-profile' => Http::response(['monthly' => [], 'source' => [], 'engine_version' => 'test']),
        'geo.test/v1/terrain' => Http::response(['slope_pct' => ['mean' => 2.0]]),
        'geo.test/v1/vegetation' => Http::response(['monthly' => []]),
        'geo.test/v1/stress' => Http::response(['lst' => null, 'et' => null]),
        'geo.test/v1/earthdata' => Http::response(['detail' => 'sem token'], 502),
        'power.larc.nasa.gov/*' => Http::response(['detail' => 'fora do teste'], 500),
    ]);
    $field = resumeField();

    // Simula um processamento morto depois de concluir clima e relevo.
    $key = sprintf('field-partial:%d:%s:%s::', $field->id, -18.9, -48.55);
    cache()->put($key, ['climate' => ['monthly' => [], 'engine_version' => 'antigo'], 'terrain' => ['slope_pct' => ['mean' => 9.9]]]);
    $field->update(['status' => Field::STATUS_PROCESSING, 'status_message' => AnalyzeFieldJob::STEPS['vegetation'][0]]);
    Field::whereKey($field->id)->update(['updated_at' => now()->subMinutes(10)]);

    $this->getJson("/api/v1/fields/{$field->id}/status")->assertOk();

    expect($field->refresh()->status)->toBe('ready')
        ->and($field->analysis->terrain['slope_pct']['mean'])->toBe(9.9); // etapa reaproveitada
    Http::assertNotSent(fn ($r) => str_ends_with($r->url(), '/v1/climate-profile') || str_ends_with($r->url(), '/v1/terrain'));
    Http::assertSent(fn ($r) => str_ends_with($r->url(), '/v1/vegetation'));
});

it('não deixa o talhão parado em "pending" quando a retomada encontra a trava ainda presa', function () {
    $field = resumeField();
    $field->update(['status' => Field::STATUS_PROCESSING, 'status_message' => AnalyzeFieldJob::STEPS['earthdata'][0]]);
    Field::whereKey($field->id)->update(['updated_at' => now()->subMinutes(10)]);
    $held = cache()->lock("field-process-{$field->id}", 600);
    $held->get(); // o processamento antigo ainda segura a trava

    $this->getJson("/api/v1/fields/{$field->id}/status")->assertOk()->assertJson(['status' => 'processing']);
    expect($field->refresh()->status)->toBe('processing')
        ->and(cache()->get("field-resumes-{$field->id}", 0))->toBe(0); // tentativa sem efeito não gasta retomada

    $held->release();
});
