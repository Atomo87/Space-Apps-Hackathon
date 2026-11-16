<?php

use App\Http\Controllers\Web\DemoController;
use App\Http\Controllers\Web\FieldController;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

// Acesso livre: sem login nem cadastro. Qualquer visitante vê, cria, edita e exclui talhões
// (só o exemplo público de referência fica protegido contra edição e exclusão — FieldPolicy).
Route::get('/', [FieldController::class, 'index'])->name('home');
Route::get('/metodologia', fn () => Inertia::render('Methodology'))->name('methodology');
Route::post('/demo', DemoController::class)->middleware('throttle:10,1')->name('demo');

Route::get('/talhoes', [FieldController::class, 'list'])->name('fields.index');
Route::get('/talhoes/novo', [FieldController::class, 'create'])->name('fields.create');
Route::post('/talhoes', [FieldController::class, 'store'])->middleware('throttle:20,1')->name('fields.store');
Route::get('/talhoes/{field}', [FieldController::class, 'show'])->whereNumber('field')->name('fields.show');
Route::get('/talhoes/{field}/editar', [FieldController::class, 'edit'])->name('fields.edit');
Route::put('/talhoes/{field}', [FieldController::class, 'update'])->middleware('throttle:30,1')->name('fields.update');
Route::delete('/talhoes/{field}', [FieldController::class, 'destroy'])->middleware('throttle:20,1')->name('fields.destroy');

// Endereços antigos de conta levam à página inicial.
Route::redirect('/entrar', '/', 301);
Route::redirect('/cadastro', '/', 301);

// Endereço inexistente: passa pelo grupo "web" (sessão) antes da página 404 do app.
Route::fallback(fn () => abort(404));
