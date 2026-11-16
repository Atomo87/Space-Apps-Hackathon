<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Field;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** POST /api/v1/fields/{field}/feedback — validação humana (RF09). */
class FeedbackController extends Controller
{
    public function __invoke(Request $request, Field $field): JsonResponse
    {
        $data = $request->validate([
            'strategy_key' => ['required', 'string', 'max:60'],
            'verdict' => ['required', 'in:makes_sense,not_applicable,needs_adjustment'],
            'comment' => ['nullable', 'string', 'max:2000'],
            'snapshot' => ['nullable', 'array'],
        ]);
        $feedback = $field->feedbacks()->create($data);

        return response()->json(['id' => $feedback->id, 'message' => __('Obrigado! Sua avaliação ajuda a calibrar as regras da região.')], 201);
    }
}
