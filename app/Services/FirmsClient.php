<?php

namespace App\Services;

use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

/**
 * Focos de queimada da NASA FIRMS (VIIRS e MODIS, quase em tempo real) perto do talhão.
 *
 * - Com FIRMS_MAP_KEY: API de área (VIIRS S-NPP, VIIRS NOAA-20 e MODIS), recorte exato.
 * - Sem chave: arquivos públicos regionais da FIRMS dos últimos 7 dias (América do Sul), filtrados aqui.
 * Resultado em cache por 1 hora.
 */
class FirmsClient
{
    private const AREA_URL = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv';

    private const AREA_SOURCES = ['VIIRS_SNPP_NRT' => 'VIIRS S-NPP', 'VIIRS_NOAA20_NRT' => 'VIIRS NOAA-20', 'MODIS_NRT' => 'MODIS'];

    /** Arquivos públicos (sem chave) dos últimos 7 dias — América do Sul. */
    private const REGIONAL = [
        'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_America_7d.csv' => 'VIIRS NOAA-20',
        'https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_South_America_7d.csv' => 'MODIS',
    ];

    public function near(float $lat, float $lon): array
    {
        $key = (string) config('geosafra.firms.key');
        $radius = max(5, min(100, (int) config('geosafra.firms.radius_km')));
        $days = $key !== '' ? max(1, min(10, (int) config('geosafra.firms.days'))) : 7;
        $inSouthAmerica = $lat >= -56 && $lat <= 13 && $lon >= -82 && $lon <= -34;
        $base = [
            'configured' => $key !== '' || $inSouthAmerica,
            'mode' => $key !== '' ? 'api' : 'regional',
            'days' => $days, 'radius_km' => $radius,
            'source' => 'NASA FIRMS (VIIRS e MODIS, quase em tempo real)',
        ];
        if (! $base['configured']) {
            return $base + ['points' => [], 'counts' => null, 'nearest_km' => null];
        }

        $cacheKey = 'firms:'.$base['mode'].':'.round($lat, 2).':'.round($lon, 2).":{$days}:{$radius}";

        return Cache::remember($cacheKey, now()->addHour(), function () use ($key, $lat, $lon, $days, $radius, $base) {
            $dLat = $radius / 111.0;
            $dLon = $radius / (111.0 * max(0.2, cos(deg2rad($lat))));
            $box = [$lon - $dLon, $lat - $dLat, $lon + $dLon, $lat + $dLat];

            $requests = $key !== ''
                ? collect(self::AREA_SOURCES)->mapWithKeys(fn ($label, $src) => [self::AREA_URL."/{$key}/{$src}/".implode(',', array_map(fn ($v) => round($v, 4), $box))."/{$days}" => $label])->all()
                : self::REGIONAL;

            $points = [];
            $failed = [];
            foreach ($requests as $url => $label) {
                $csv = $key !== '' ? $this->download($url) : $this->regional($url);
                if ($csv === null) {
                    $failed[] = $label;

                    continue;
                }
                foreach ($this->rows($csv, $box) as $row) {
                    $dist = $this->distanceKm($lat, $lon, (float) $row['latitude'], (float) $row['longitude']);
                    if ($dist > $radius) {
                        continue;
                    }
                    $points[] = [
                        'lat' => (float) $row['latitude'], 'lon' => (float) $row['longitude'], 'distance_km' => round($dist, 1),
                        'date' => $row['acq_date'] ?? null, 'time' => $row['acq_time'] ?? null,
                        'frp' => isset($row['frp']) ? (float) $row['frp'] : null,
                        'confidence' => $row['confidence'] ?? null, 'satellite' => $label,
                    ];
                }
            }
            usort($points, fn ($a, $b) => $a['distance_km'] <=> $b['distance_km']);
            $count = fn (int $km) => count(array_filter($points, fn ($p) => $p['distance_km'] <= $km));

            return $base + [
                'points' => array_slice($points, 0, 300),
                'counts' => ['10' => $count(10), '25' => $count(25), (string) $radius => count($points)],
                'nearest_km' => $points[0]['distance_km'] ?? null,
                'failed_sources' => $failed,
                'fetched_at' => now()->toIso8601String(),
            ];
        });
    }

    private function download(string $url): ?string
    {
        $res = Http::timeout(60)->connectTimeout(15)->get($url);
        $body = $res->successful() ? $res->body() : '';

        return $body !== '' && ! str_starts_with(trim($body), 'Invalid') ? $body : null;
    }

    /** Arquivo regional (alguns MB) baixado no máximo uma vez por hora para storage/app/firms e compartilhado entre os talhões. */
    private function regional(string $url): ?string
    {
        $path = storage_path('app/firms/'.md5($url).'.csv');
        if (is_file($path) && filemtime($path) > time() - 3600) {
            return (string) file_get_contents($path);
        }
        $csv = $this->download($url);
        if ($csv !== null) {
            @mkdir(dirname($path), 0755, true);
            file_put_contents($path, $csv, LOCK_EX);
        } elseif (is_file($path)) {
            return (string) file_get_contents($path); // FIRMS fora do ar: usa o último arquivo baixado
        }

        return $csv;
    }

    /** Linhas do CSV dentro do retângulo (filtra antes de montar o array, para arquivos grandes). */
    private function rows(string $csv, array $box): \Generator
    {
        $lines = preg_split('/\r?\n/', trim($csv));
        $head = str_getcsv((string) array_shift($lines));
        $iLat = array_search('latitude', $head, true);
        $iLon = array_search('longitude', $head, true);
        if ($iLat === false || $iLon === false) {
            return;
        }
        foreach ($lines as $line) {
            $cols = str_getcsv($line);
            if (count($cols) !== count($head)) {
                continue;
            }
            $la = (float) $cols[$iLat];
            $lo = (float) $cols[$iLon];
            if ($lo < $box[0] || $la < $box[1] || $lo > $box[2] || $la > $box[3]) {
                continue;
            }
            yield array_combine($head, $cols);
        }
    }

    private function distanceKm(float $lat1, float $lon1, float $lat2, float $lon2): float
    {
        $dLat = deg2rad($lat2 - $lat1);
        $dLon = deg2rad($lon2 - $lon1);
        $a = sin($dLat / 2) ** 2 + cos(deg2rad($lat1)) * cos(deg2rad($lat2)) * sin($dLon / 2) ** 2;

        return 2 * 6371.0 * asin(min(1, sqrt($a)));
    }
}
