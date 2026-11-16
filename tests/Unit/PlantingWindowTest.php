<?php

use App\Services\PlantingWindow;
use Carbon\CarbonImmutable;

/** Clima sintético: chuva regular de 15 out a 31 mar, seco no resto; frio só em junho/julho. */
function syntheticDaily(int $from = 2005, int $to = 2024): array
{
    $out = [];
    for ($d = CarbonImmutable::create($from, 1, 1); $d->year <= $to; $d = $d->addDay()) {
        $wet = ($d->month >= 11 || $d->month <= 3) || ($d->month === 10 && $d->day >= 15);
        $out[$d->format('Ymd')] = [
            'rain' => $wet ? 8.0 : 0.0,
            'tmin' => in_array($d->month, [6, 7], true) ? 1.0 : 15.0,
            'tmax' => 30.0,
        ];
    }

    return $out;
}

it('acha a janela de verão depois do início das chuvas', function () {
    $r = (new PlantingWindow)->compute(syntheticDaily());
    $verao = collect($r['seasons'])->firstWhere('key', 'verao');

    $sep = collect($verao['weeks'])->firstWhere('date', '09-01');
    $nov = collect($verao['weeks'])->firstWhere('date', '11-03');

    expect($sep['score'])->toBe(0.0)          // antes das chuvas: sem umidade para semear
        ->and($nov['score'])->toBe(1.0)       // chuva antes e durante: todos os anos bons
        ->and($verao['best']['level'])->toBe('good')
        ->and($r['period'])->toBe(['start' => 2005, 'end' => 2024]);
});

it('aponta geada e falta de chuva no inverno', function () {
    $r = (new PlantingWindow)->compute(syntheticDaily());
    $inverno = collect($r['seasons'])->firstWhere('key', 'inverno');
    $maio = collect($inverno['weeks'])->firstWhere('date', '05-03');

    expect($maio['p_frost'])->toBe(1.0)->and($maio['p_water'])->toBe(0.0)->and($maio['score'])->toBe(0.0);
});
