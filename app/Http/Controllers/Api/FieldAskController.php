<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Field;
use App\Services\AnalysisPayload;
use App\Services\Assistant\EvidenceCatalog;
use App\Services\Assistant\FieldAssistant;
use App\Services\Assistant\KnowledgeBase;
use App\Services\FirmsClient;
use App\Services\GeoServiceClient;
use App\Services\PublicDemo;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Str;
use RuntimeException;
use Throwable;

/**
 * POST /api/v1/fields/{field}/ask — pergunta ao assistente (IA + RAG) sobre o talhão.
 * Devolve afirmações com as evidências citadas: indicador, valor, período e fonte de cada uma.
 */
class FieldAskController extends Controller
{
    public function __invoke(Request $request, Field $field, GeoServiceClient $geo, FirmsClient $firms, FieldAssistant $assistant, KnowledgeBase $knowledge, PublicDemo $demo): JsonResponse
    {
        $data = $request->validate(['question' => ['required', 'string', 'min:3', 'max:500']]);
        $question = $data['question'];

        if ($reference = $knowledge->matchAnswer($question)) {
            return response()->json($assistant->referenceAnswer($reference) + [
                'question' => $question,
                'prompt_version' => FieldAssistant::PROMPT_VERSION,
            ]);
        }

        $region = $demo->region($field);
        $isPublicDemo = $region !== null;
        $field = $isPublicDemo ? $demo->prepare($field) : $field;

        if ($field->status !== Field::STATUS_READY) {
            return response()->json([
                'type' => 'about:blank', 'title' => __('Talhão ainda não processado'), 'status' => 409,
                'detail' => __('Aguarde o processamento dos dados da NASA.'), 'field_status' => $field->status,
            ], 409, ['Content-Type' => 'application/problem+json']);
        }

        // Mesma análise da tela (pesos salvos, sem cenário), reaproveitando o cache.
        $payload = AnalysisPayload::for($field);
        try {
            $analysis = $isPublicDemo
                ? $demo->baseline($region)
                : Cache::remember(GeoServiceClient::analysisCacheKey($payload), now()->addMinutes(10), fn () => $geo->analysis($payload));
        } catch (RuntimeException $e) {
            return response()->json([
                'type' => 'about:blank', 'title' => __('Serviço de dados indisponível'), 'status' => 502,
                'detail' => GeoServiceClient::isStaleProfileError($e) ? __('Os dados deste talhão estão sendo atualizados. Abra o diagnóstico e tente de novo em instantes.') : $e->getMessage(),
            ], 502, ['Content-Type' => 'application/problem+json']);
        }

        try {
            $fires = $isPublicDemo ? null : $firms->near((float) $field->latitude, (float) $field->longitude);
        } catch (Throwable) {
            $fires = null;
        }
        $evidence = EvidenceCatalog::build($analysis, $field->analysis?->planting, $fires);

        // A resposta expira também quando as referências recuperadas mudarem.
        $refs = $knowledge->search($question);
        $signature = [app()->getLocale(), Str::lower(trim($question)), $evidence->all(), $refs, FieldAssistant::PROMPT_VERSION, config('geosafra.ai.model')];
        $key = 'ask:'.$field->id.':'.sha1(json_encode($signature, JSON_THROW_ON_ERROR));
        $answer = Cache::remember($key, now()->addHours(6), fn () => $assistant->answer($question, $evidence, $refs));

        // Só as evidências citadas vão para a tela, cada uma com indicador, valor, período e fonte.
        $cited = collect($answer['claims'])->pluck('fact_ids')->flatten()->unique()->all();

        return response()->json($answer + [
            'question' => $question,
            'facts' => array_intersect_key($evidence->all(), array_flip($cited)),
            'evidence_count' => count($evidence->all()),
            'prompt_version' => FieldAssistant::PROMPT_VERSION,
        ]);
    }
}
