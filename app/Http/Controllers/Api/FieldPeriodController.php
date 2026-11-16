<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Field;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * PUT /api/v1/fields/{field}/period — anos do NASA POWER usados na análise do talhão.
 * Grava e deixa o talhão pendente; o navegador chama /process em seguida para consultar a NASA de novo.
 */
class FieldPeriodController extends Controller
{
    public function __invoke(Request $request, Field $field): JsonResponse
    {
        $last = (int) now()->year - 1; // último ano completo
        $data = $request->validate([
            'start_year' => ['nullable', 'integer', 'min:'.Field::POWER_FIRST_YEAR, 'max:'.($last - Field::POWER_MIN_YEARS + 1)],
            'end_year' => ['nullable', 'integer', 'max:'.$last, 'required_with:start_year'],
        ], [
            'start_year.max' => 'Escolha um início que deixe pelo menos '.Field::POWER_MIN_YEARS.' anos de dados.',
            'end_year.max' => "O último ano completo disponível é {$last}.",
        ]);

        $start = $data['start_year'] ?? null;
        $end = $data['end_year'] ?? null;
        if ($start !== null && $end - $start + 1 < Field::POWER_MIN_YEARS) {
            return response()->json([
                'message' => __('O período precisa ter pelo menos :years anos.', ['years' => Field::POWER_MIN_YEARS]),
                'errors' => ['end_year' => ['O período precisa ter pelo menos '.Field::POWER_MIN_YEARS.' anos.']],
            ], 422);
        }

        $changed = $field->power_start_year !== $start || $field->power_end_year !== $end;
        $field->update([
            'power_start_year' => $start,
            'power_end_year' => $end,
        ] + ($changed ? ['status' => Field::STATUS_PENDING, 'status_message' => 'Período alterado: consultando o NASA POWER de novo…'] : []));

        return response()->json([
            'start_year' => $field->power_start_year,
            'end_year' => $field->power_end_year,
            'changed' => $changed,
        ]);
    }
}
