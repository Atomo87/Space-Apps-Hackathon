<?php

use App\Models\Farm;
use App\Models\Field;
use App\Models\User;
use Illuminate\Support\Facades\Http;

function fieldOwnedBy(User $user): Field
{
    $farm = Farm::create(['user_id' => $user->id, 'name' => 'Fazenda', 'is_demo' => false]);

    return Field::create(['farm_id' => $farm->id, 'name' => 'T1', 'latitude' => -18.924716, 'longitude' => -48.312922, 'status' => Field::STATUS_READY]);
}

it('grava o período do NASA POWER e reprocessa com esses anos', function () {
    Http::fake([
        'geo.test/v1/climate-profile' => Http::response(['monthly' => [], 'source' => [], 'engine_version' => 'test']),
        'geo.test/*' => Http::response(['detail' => 'fora do teste'], 502),
    ]);
    config(['geosafra.geo_service.url' => 'http://geo.test']);
    $user = User::factory()->create();
    $field = fieldOwnedBy($user);

    $this->actingAs($user)->putJson("/api/v1/fields/{$field->id}/period", ['start_year' => 2010, 'end_year' => 2024])
        ->assertOk()->assertJson(['start_year' => 2010, 'end_year' => 2024, 'changed' => true]);
    expect($field->refresh()->status)->toBe(Field::STATUS_PENDING);

    $this->actingAs($user)->postJson("/api/v1/fields/{$field->id}/process")->assertAccepted();
    expect($field->refresh()->status)->toBe(Field::STATUS_READY);
    Http::assertSent(fn ($r) => str_ends_with($r->url(), '/v1/climate-profile') && $r['start_year'] === 2010 && $r['end_year'] === 2024);
});

it('recusa períodos curtos demais ou no futuro', function () {
    $user = User::factory()->create();
    $field = fieldOwnedBy($user);
    $last = now()->year - 1;

    $this->actingAs($user)->putJson("/api/v1/fields/{$field->id}/period", ['start_year' => $last - 4, 'end_year' => $last])->assertStatus(422);
    $this->actingAs($user)->putJson("/api/v1/fields/{$field->id}/period", ['start_year' => 2000, 'end_year' => $last + 1])->assertStatus(422);
    $this->actingAs($user)->putJson("/api/v1/fields/{$field->id}/period", ['start_year' => 1970, 'end_year' => 2000])->assertStatus(422);
    expect($field->refresh()->power_start_year)->toBeNull();
});

it('deixa qualquer visitante mudar o período (acesso livre)', function () {
    $field = fieldOwnedBy(User::factory()->create());

    $this->putJson("/api/v1/fields/{$field->id}/period", ['start_year' => 2005, 'end_year' => 2024])->assertOk();
    expect($field->refresh()->power_start_year)->toBe(2005);
});
