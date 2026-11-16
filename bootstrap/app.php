<?php

use App\Http\Middleware\HandleInertiaRequests;
use App\Http\Middleware\SetLocale;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Inertia\Inertia;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->prepend(SetLocale::class);
        $middleware->web(append: [
            HandleInertiaRequests::class,
        ]);
        $middleware->redirectGuestsTo(fn () => route('home'));
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        // Erros da API no formato RFC 9457 (problem+json).
        $exceptions->render(function (Throwable $e, Request $request) {
            if (! $request->is('api/*') || $e instanceof ValidationException) {
                return null;
            }
            $status = match (true) {
                $e instanceof AuthenticationException => 401,
                $e instanceof HttpExceptionInterface => $e->getStatusCode(),
                default => 500,
            };
            $title = match ($status) {
                401 => __('Entre na sua conta'),
                403 => __('Sem permissão'),
                404 => __('Não encontrado'),
                419 => __('Sessão expirada'),
                429 => __('Muitas requisições'),
                default => $status >= 500 ? __('Erro interno') : __('Requisição inválida'),
            };
            $detail = match ($status) {
                401 => __('Entre na sua conta para continuar.'),
                403 => __('O exemplo público de referência não pode ser alterado.'),
                404 => __('O recurso pedido não existe ou foi excluído.'),
                419 => __('Sua sessão expirou. Recarregue a página.'),
                429 => __('Muitas requisições seguidas. Aguarde um instante.'),
                default => $status >= 500 && ! config('app.debug') ? __('Tente novamente em instantes.') : $e->getMessage(),
            };

            return response()->json([
                'type' => 'about:blank',
                'title' => $title,
                'status' => $status,
                'detail' => $detail,
            ], $status, ['Content-Type' => 'application/problem+json']);
        });

        // Páginas de erro com o visual do app (em produção; em desenvolvimento fica o relatório detalhado).
        $exceptions->respond(function (Response $response, Throwable $e, Request $request) {
            $status = $response->getStatusCode();
            if ($request->is('api/*') || $request->expectsJson()) {
                return $response;
            }
            if ($status === 419) {
                return back()->with('error', __('Sua sessão expirou. Tente de novo.'));
            }
            if (in_array($status, [403, 404, 429, 500, 503], true) && (! config('app.debug') || in_array($status, [403, 404], true))) {
                // Em rota inexistente o middleware do Inertia não roda: compartilhamos aqui o mínimo que o layout usa.
                Inertia::share([
                    'app' => [
                        'name' => config('app.name'),
                        'disclaimer' => __(config('geosafra.disclaimer')),
                        'footerWarning' => __(config('geosafra.footer_warning')),
                        'powerCitation' => __(config('geosafra.power_citation')),
                    ],
                    'auth' => ['user' => $request->hasSession() ? $request->user()?->only(['id', 'name', 'email']) : null],
                    'flash' => ['success' => null, 'error' => null],
                    'glossary' => fn () => app()->isLocale('pt_BR') ? require database_path('data/glossary.php') : trans('glossary'),
                ]);

                return Inertia::render('Error', ['status' => $status])->toResponse($request)->setStatusCode($status);
            }

            return $response;
        });
    })->create();
