<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use RuntimeException;

/**
 * Série diária da NASA POWER (API pública, sem chave) para um ponto: chuva, mínima e máxima.
 * Usada pela janela de plantio. Fica em cache por 30 dias (a série histórica não muda).
 */
class NasaPowerDaily
{
    private const URL = 'https://power.larc.nasa.gov/api/temporal/daily/point';

    /** @return array<string, array{rain: float, tmin: float, tmax: float}> chave = AAAAMMDD */
    public function fetch(float $lat, float $lon, int $startYear, int $endYear): array
    {
        $lat = round($lat, 4);
        $lon = round($lon, 4);
        $key = "power-daily:{$lat}:{$lon}:{$startYear}:{$endYear}";

        return Cache::remember($key, now()->addDays(30), function () use ($lat, $lon, $startYear, $endYear) {
            $response = Http::timeout(120)->connectTimeout(20)->retry(2, 2000, fn ($e) => $e instanceof ConnectionException, throw: false)->get(self::URL, [
                'parameters' => 'PRECTOTCORR,T2M_MIN,T2M_MAX',
                'community' => 'AG',
                'latitude' => $lat,
                'longitude' => $lon,
                'start' => "{$startYear}0101",
                'end' => "{$endYear}1231",
                'format' => 'JSON',
            ]);
            if (! $response->successful()) {
                throw new RuntimeException("NASA POWER diário respondeu HTTP {$response->status()}.");
            }

            $p = $response->json('properties.parameter') ?? [];
            $fill = (float) ($response->json('header.fill_value') ?? -999);
            $out = [];
            foreach ($p['PRECTOTCORR'] ?? [] as $day => $rain) {
                $tmin = $p['T2M_MIN'][$day] ?? $fill;
                $tmax = $p['T2M_MAX'][$day] ?? $fill;
                if ($rain == $fill || $tmin == $fill || $tmax == $fill) {
                    continue;
                }
                $out[(string) $day] = ['rain' => (float) $rain, 'tmin' => (float) $tmin, 'tmax' => (float) $tmax];
            }
            if (count($out) < 365 * 5) {
                throw new RuntimeException('NASA POWER diário: série curta demais para avaliar a janela de plantio.');
            }

            return $out;
        });
    }
}
