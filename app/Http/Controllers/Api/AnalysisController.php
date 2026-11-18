<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\FarmerPriority;
use App\Models\Field;
use App\Services\AnalysisPayload;
use App\Services\FieldProcessor;
use App\Services\GeoServiceClient;
use App\Services\PublicDemo;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use RuntimeException;

/** GET /api/v1/fields/{field}/analysis — diagnóstico + estratégias (com cenário opcional). */
class AnalysisController extends Controller
{
    public function __invoke(Request $request, Field $field, GeoServiceClient $geo, FieldProcessor $processor, PublicDemo $demo): JsonResponse
    {
        $data = $request->validate([
            'rain_delta_pct' => ['nullable', 'numeric', 'between:-40,20'],
            'temp_delta_c' => ['nullable', 'numeric', 'between:0,3'],
            // Pesos para simular sem gravar (ex.: visitante no caso de demonstração). Sem isso, usa os pesos salvos.
            'priorities' => ['nullable', 'array:'.implode(',', FarmerPriority::KEYS)],
            'priorities.*' => ['integer', 'between:0,5'],
        ]);

        $region = $demo->region($field);
        $isPublicDemo = $region !== null;
        $field = $isPublicDemo ? $demo->prepare($field) : $field;

        if ($field->status !== Field::STATUS_READY) {
            return response()->json([
                'type' => 'about:blank', 'title' => __('Talhão ainda não processado'), 'status' => 409,
                'detail' => __('Aguarde o processamento dos dados da NASA.'),
                'field_status' => $field->status,
            ], 409, ['Content-Type' => 'application/problem+json']);
        }

        $payload = AnalysisPayload::for(
            $field,
            (float) ($data['rain_delta_pct'] ?? 0),
            (float) ($data['temp_delta_c'] ?? 0),
            isset($data['priorities']) ? array_map('intval', $data['priorities']) : null,
        );
        // A chave muda com os dados; depois de atualizar o motor no geo-service, rode `php artisan cache:clear`.
        $key = GeoServiceClient::analysisCacheKey($payload);
        $isBaseline = $isPublicDemo && $demo->isBaseline($region, $payload);

        if ($region === 'texas' && ! $isBaseline) {
            return response()->json([
                'type' => 'about:blank', 'title' => __('Simulação indisponível'), 'status' => 422,
                'detail' => __('O exemplo do Texas mostra um cenário de referência fixo.'),
            ], 422, ['Content-Type' => 'application/problem+json']);
        }

        try {
            $result = $isBaseline
                ? $demo->baseline($region)
                : Cache::remember($key, now()->addMinutes(10), fn () => $geo->analysis($payload));
        } catch (RuntimeException $e) {
            if ($isPublicDemo) {
                return response()->json([
                    'type' => 'about:blank', 'title' => __('Serviço de dados indisponível'), 'status' => 503,
                    'detail' => __('O serviço de análise está indisponível para recalcular a simulação. Restaure os valores iniciais para consultar o diagnóstico de demonstração.'),
                ], 503, ['Content-Type' => 'application/problem+json']);
            }

            if (GeoServiceClient::isStaleProfileError($e)) {
                // Recibo das fontes vencido: renova as fontes em segundo plano; o navegador acompanha por /status.
                $processor->start($field, 'Atualizando os dados da NASA deste talhão…');

                return response()->json([
                    'type' => 'about:blank', 'title' => __('Atualizando dados'), 'status' => 409,
                    'detail' => __('Os dados da NASA deste talhão estão sendo atualizados. A análise aparece em instantes.'),
                    'field_status' => Field::STATUS_PROCESSING,
                ], 409, ['Content-Type' => 'application/problem+json']);
            }

            return response()->json([
                'type' => 'about:blank', 'title' => __('Serviço de dados indisponível'), 'status' => 502, 'detail' => $e->getMessage(),
            ], 502, ['Content-Type' => 'application/problem+json']);
        }

        // Recursos calculados no próprio GeoSafra (fora do motor): janela de plantio.
        return response()->json(($isPublicDemo ? $demo->label($result) : $result) + [
            'field_id' => $field->id, 'planting' => $field->analysis?->planting,
        ]);
    }
}
