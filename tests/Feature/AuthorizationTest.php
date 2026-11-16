<?php

use App\Models\Field;
use App\Services\FieldWriter;
use Database\Seeders\CropSeeder;
use Illuminate\Support\Facades\Http;

// Acesso livre: sem login nem cadastro. Só o exemplo público de referência é protegido.
beforeEach(function () {
    $this->seed(CropSeeder::class);
    config(['geosafra.geo_service.url' => 'http://geo.test']);
    $this->field = app(FieldWriter::class)->save(fieldPayload(), null, ['user_id' => null]);
});

it('deixa qualquer visitante cadastrar talhão sem login', function () {
    $this->get('/talhoes/novo')->assertOk();
    $this->post('/talhoes', fieldPayload())->assertRedirect();
    expect(Field::count())->toBe(2);
});

it('abre a tela "Meus talhões" com todos os talhões', function () {
    $this->get('/talhoes')->assertOk()
        ->assertInertia(fn ($page) => $page->component('Fields/Index')->has('fields', 1)->where('stats.fields', 1));
});

it('lista todos os talhões para qualquer visitante em "Meus talhões", não na página inicial', function () {
    $this->get('/talhoes')->assertInertia(fn ($page) => $page->has('fields', 1)->where('fields.0.id', $this->field->id));
    $this->get('/')->assertInertia(fn ($page) => $page->component('Welcome')->missing('fields'));
});

it('deixa qualquer visitante ver, editar e excluir um talhão', function () {
    $id = $this->field->id;

    $this->get("/talhoes/{$id}")->assertOk()->assertInertia(fn ($page) => $page->where('can.update', true)->where('can.delete', true));
    $this->get("/talhoes/{$id}/editar")->assertOk();
    $this->put("/talhoes/{$id}", fieldPayload())->assertRedirect();
    $this->putJson("/api/v1/farms/{$this->field->farm_id}/priorities", fieldPayload()['priorities'])->assertOk();
    $this->delete("/talhoes/{$id}")->assertRedirect('/');
    expect(Field::find($id))->toBeNull();
});

it('leva os endereços antigos de conta para o início', function () {
    $this->get('/entrar')->assertRedirect('/');
    $this->get('/cadastro')->assertRedirect('/');
});

it('protege o exemplo público contra edição e exclusão, sem duplicar', function () {
    $this->post('/demo')->assertRedirect();
    $this->post('/demo')->assertRedirect();

    $demo = Field::whereHas('farm', fn ($q) => $q->where('is_demo', true)->whereNull('user_id'))->sole();

    $this->get("/talhoes/{$demo->id}")->assertOk()
        ->assertInertia(fn ($page) => $page->where('can.update', false)->where('can.delete', false));
    $this->delete("/talhoes/{$demo->id}")->assertForbidden();
    $this->put("/talhoes/{$demo->id}", fieldPayload())->assertForbidden();
    $this->putJson("/api/v1/farms/{$demo->farm_id}/priorities", fieldPayload()['priorities'])->assertForbidden();
    $this->putJson("/api/v1/fields/{$demo->id}/period", ['start_year' => 2005, 'end_year' => 2024])->assertForbidden();
});

it('simula prioridades no exemplo público sem gravar', function () {
    Http::fake([
        'geo.test/v1/climate-profile' => Http::response(['monthly' => [], 'source' => [], 'engine_version' => 'test']),
        'geo.test/v1/terrain' => Http::response(['slope_pct' => ['mean' => 2.0]]),
        'geo.test/v1/vegetation' => Http::response(['monthly' => []]),
        'geo.test/v1/stress' => Http::response(['lst' => null, 'et' => null]),
        'geo.test/v1/earthdata' => Http::response(['detail' => 'sem token'], 502),
        'geo.test/v1/analysis' => Http::response(['strategies' => [], 'diagnosis' => []]),
    ]);
    $this->post('/demo');
    $demo = Field::whereHas('farm', fn ($f) => $f->where('is_demo', true))->sole();

    $this->postJson("/api/v1/fields/{$demo->id}/process")->assertAccepted();
    $this->getJson("/api/v1/fields/{$demo->id}/status")->assertJson(['status' => 'ready']);
    $this->getJson("/api/v1/fields/{$demo->id}/analysis?priorities[forage]=5&priorities[save_water]=0")->assertOk();

    Http::assertSent(fn ($r) => str_ends_with($r->url(), '/v1/analysis') && $r['priorities']['forage'] === 5 && $r['priorities']['save_water'] === 0);
    expect($demo->farm->priorities()->first()->forage)->toBe(2);
});
