<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Farm;
use App\Models\FarmerPriority;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** PUT /api/v1/farms/{farm}/priorities — pesos 0–5 usados pelo motor. */
class PriorityController extends Controller
{
    public function __invoke(Request $request, Farm $farm): JsonResponse
    {
        $rules = collect(FarmerPriority::KEYS)->mapWithKeys(fn ($k) => [$k => ['required', 'integer', 'between:0,5']])->all();
        $data = $request->validate($rules);
        $farm->priorities()->updateOrCreate(['farm_id' => $farm->id], $data);

        return response()->json(['farm_id' => $farm->id, 'priorities' => $data]);
    }
}
