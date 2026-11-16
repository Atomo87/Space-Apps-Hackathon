<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class SetLocale
{
    public function handle(Request $request, Closure $next): Response
    {
        $isPortuguese = $request->cookies->get('geosafra_locale') === 'pt-BR';
        app()->setLocale($isPortuguese ? 'pt_BR' : 'en');

        $response = $next($request);
        $response->headers->set('Content-Language', $isPortuguese ? 'pt-BR' : 'en-US');

        return $response;
    }
}
