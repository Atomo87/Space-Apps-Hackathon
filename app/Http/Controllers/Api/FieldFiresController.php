<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Field;
use App\Services\FirmsClient;
use Illuminate\Http\JsonResponse;
use Throwable;

/** GET /api/v1/fields/{field}/fires — focos de queimada da NASA FIRMS perto do talhão. */
class FieldFiresController extends Controller
{
    public function __invoke(Field $field, FirmsClient $firms): JsonResponse
    {
        try {
            return response()->json($firms->near((float) $field->latitude, (float) $field->longitude));
        } catch (Throwable $e) {
            report($e);

            return response()->json([
                'type' => 'about:blank', 'title' => 'NASA FIRMS indisponível', 'status' => 502,
                'detail' => 'Não foi possível consultar os focos de queimada agora. Tente mais tarde.',
            ], 502, ['Content-Type' => 'application/problem+json']);
        }
    }
}
