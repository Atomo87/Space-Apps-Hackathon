<?php

use App\Models\Farm;
use App\Models\Field;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Http;

function fireField(): Field
{
    $farm = Farm::create(['name' => 'Fazenda', 'is_demo' => false]);

    return Field::create(['farm_id' => $farm->id, 'name' => 'T1', 'latitude' => -18.9, 'longitude' => -48.55, 'status' => Field::STATUS_READY]);
}

it('sem chave, usa os arquivos públicos regionais da FIRMS', function () {
    config(['geosafra.firms.key' => '']);
    File::deleteDirectory(storage_path('app/firms')); // sem arquivo regional guardado de execuções anteriores
    Http::fake([
        'firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/*' => Http::response("latitude,longitude,acq_date,acq_time,confidence,frp\n-18.92,-48.56,2026-11-14,1630,h,8.0\n-10.0,-60.0,2026-11-14,1630,h,8.0\n"),
        'firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/*' => Http::response("latitude,longitude,acq_date,acq_time,confidence,frp\n"),
    ]);

    $this->getJson('/api/v1/fields/'.fireField()->id.'/fires')
        ->assertOk()->assertJson(['configured' => true, 'mode' => 'regional', 'counts' => ['10' => 1]])
        ->assertJsonCount(1, 'points');
});

it('fora da América do Sul e sem chave, avisa que não há dados', function () {
    config(['geosafra.firms.key' => '']);
    $farm = Farm::create(['name' => 'F', 'is_demo' => false]);
    $field = Field::create(['farm_id' => $farm->id, 'name' => 'T', 'latitude' => 40.0, 'longitude' => -100.0, 'status' => Field::STATUS_READY]);

    $this->getJson("/api/v1/fields/{$field->id}/fires")->assertOk()->assertJson(['configured' => false, 'points' => []]);
});

it('conta os focos de queimada por distância do talhão', function () {
    config(['geosafra.firms.key' => 'chave-teste', 'geosafra.firms.radius_km' => 50]);
    $csv = "latitude,longitude,acq_date,acq_time,confidence,frp\n"
        ."-18.95,-48.55,2026-11-14,1630,h,12.5\n"   // ~5,6 km
        ."-19.10,-48.55,2026-11-13,0412,n,3.1\n"    // ~22 km
        ."-19.30,-48.55,2026-11-12,1700,l,1.0\n";   // ~44 km
    Http::fake([
        'firms.modaps.eosdis.nasa.gov/api/area/csv/chave-teste/VIIRS_SNPP_NRT/*' => Http::response($csv),
        'firms.modaps.eosdis.nasa.gov/*' => Http::response("latitude,longitude,acq_date,acq_time,confidence,frp\n"),
    ]);

    $this->getJson('/api/v1/fields/'.fireField()->id.'/fires')
        ->assertOk()
        ->assertJson(['configured' => true, 'counts' => ['10' => 1, '25' => 2, '50' => 3]])
        ->assertJsonPath('points.0.satellite', 'VIIRS S-NPP')
        ->assertJsonPath('nearest_km', 5.6);
});
