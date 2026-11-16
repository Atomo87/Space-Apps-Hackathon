<?php

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;
use RuntimeException;

/**
 * Cliente HTTP do geo-service (Python/FastAPI) — tarefa B6.
 * O Laravel nunca chama a NASA diretamente: quem consulta a POWER é o geo-service.
 */
class GeoServiceClient
{
    private function http(int $timeout): PendingRequest
    {
        return Http::baseUrl(config('geosafra.geo_service.url'))
            ->acceptJson()
            ->asJson()
            ->withHeaders(array_filter(['X-GeoSafra-Token' => config('geosafra.geo_service.token')]))
            ->connectTimeout(20)
            ->timeout($timeout);
    }

    /** Consulta a NASA POWER (via geo-service) e devolve o ClimateProfile. Pode levar até ~2 min sem cache. */
    public function climateProfile(float $lat, float $lon, ?int $startYear = null, ?int $endYear = null): array
    {
        return $this->send('post', '/v1/climate-profile', array_filter([
            'latitude' => round($lat, 4),
            'longitude' => round($lon, 4),
            'start_year' => $startYear ?? config('geosafra.geo_service.start_year'),
            'end_year' => $endYear ?? config('geosafra.geo_service.end_year'),
        ], fn ($v) => $v !== null), (int) config('geosafra.geo_service.timeout'));
    }

    /** Declividade e fator LS do talhão pela elevação SRTM (~30 m). */
    public function terrain(float $lat, float $lon, ?array $boundary = null): array
    {
        return $this->send('post', '/v1/terrain', array_filter([
            'latitude' => round($lat, 4),
            'longitude' => round($lon, 4),
            'boundary' => $boundary,
        ], fn ($v) => $v !== null), 60);
    }

    /** Cobertura verde: NDVI MODIS (250 m, 5 anos) + HLS (30 m, 2 anos). ~20–60 s sem cache. */
    public function vegetation(float $lat, float $lon): array
    {
        return $this->send('post', '/v1/vegetation', [
            'latitude' => round($lat, 4),
            'longitude' => round($lon, 4),
        ], 180);
    }

    /** Estresse observado: temperatura da superfície (MODIS LST) e evapotranspiração real/potencial (MODIS ET). */
    public function stress(float $lat, float $lon): array
    {
        return $this->send('post', '/v1/stress', [
            'latitude' => round($lat, 4),
            'longitude' => round($lon, 4),
        ], 120);
    }

    /** SMAP, GPM IMERG, ECOSTRESS e GRACE-FO (exigem token Earthdata no geo-service). ~1–3 min sem cache. */
    public function earthdata(float $lat, float $lon): array
    {
        return $this->send('post', '/v1/earthdata', [
            'latitude' => round($lat, 4),
            'longitude' => round($lon, 4),
        ], 240);
    }

    /**
     * O geo-service assina cada consulta de fonte com um recibo (_receipt) válido por tempo limitado e
     * só para o mesmo ponto. Quando o recibo vence (ou o serviço reinicia), a análise é recusada com esta mensagem.
     */
    public static function isStaleProfileError(RuntimeException $e): bool
    {
        return str_contains(mb_strtolower($e->getMessage()), 'consulte novamente as fontes');
    }

    /** Diagnóstico + estratégias A–D (rápido: usa o ClimateProfile já guardado). */
    public function analysis(array $payload): array
    {
        return $this->send('post', '/v1/analysis', $payload, 60, ['Accept-Language' => self::analysisLanguage()]);
    }

    public static function analysisCacheKey(array $payload): string
    {
        return 'analysis:v2:'.self::analysisLanguage().':'.sha1(json_encode($payload));
    }

    private static function analysisLanguage(): string
    {
        return app()->isLocale('pt_BR') ? 'pt-BR' : 'en-US';
    }

    public function catalog(): array
    {
        return $this->send('get', '/v1/catalog', [], 30);
    }

    public function health(): array
    {
        return $this->send('get', '/health', [], 70);
    }

    private function send(string $method, string $uri, array $data, int $timeout, array $headers = []): array
    {
        try {
            $response = $this->http($timeout)->withHeaders($headers)->{$method}($uri, $data);
            $response->throw();

            return $response->json();
        } catch (ConnectionException $e) {
            throw new RuntimeException(__('Não foi possível falar com o serviço de dados (geo-service). Ele pode estar iniciando; tente de novo em 1 minuto.'), 0, $e);
        } catch (RequestException $e) {
            $detail = $e->response->json('detail');
            $detail = is_array($detail) ? collect($detail)->pluck('msg')->implode('; ') : $detail;
            throw new RuntimeException($detail ?: "O geo-service respondeu HTTP {$e->response->status()}.", $e->response->status(), $e);
        }
    }
}
