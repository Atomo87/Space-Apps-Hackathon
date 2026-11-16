<?php

use App\Http\Controllers\Api\AnalysisController;
use App\Http\Controllers\Api\FeedbackController;
use App\Http\Controllers\Api\FieldAskController;
use App\Http\Controllers\Api\FieldFiresController;
use App\Http\Controllers\Api\FieldPeriodController;
use App\Http\Controllers\Api\FieldProcessController;
use App\Http\Controllers\Api\PriorityController;
use Illuminate\Support\Facades\Route;

/*
 * API interna consumida pelo próprio front-end (mesma origem).
 * Usa a sessão do Laravel (grupo "web": cookie + proteção CSRF via X-XSRF-TOKEN) para saber quem está pedindo.
 * Autorização pelas policies: dono do talhão ou caso público de demonstração.
 */
Route::prefix('v1')->middleware('web')->group(function () {
    Route::middleware('can:view,field')->group(function () {
        Route::get('fields/{field}/status', [FieldProcessController::class, 'status']);
        Route::post('fields/{field}/process', [FieldProcessController::class, 'process'])->middleware('throttle:10,1');
        Route::get('fields/{field}/analysis', AnalysisController::class)->middleware('throttle:120,1');
        Route::post('fields/{field}/feedback', FeedbackController::class)->middleware('throttle:30,1');
        Route::get('fields/{field}/fires', FieldFiresController::class)->middleware('throttle:30,1');
        Route::post('fields/{field}/ask', FieldAskController::class)->middleware('throttle:12,1');
    });

    Route::put('fields/{field}/period', FieldPeriodController::class)->middleware(['can:update,field', 'throttle:20,1']);
    Route::put('farms/{farm}/priorities', PriorityController::class)->middleware(['can:update,farm', 'throttle:60,1']);
});
