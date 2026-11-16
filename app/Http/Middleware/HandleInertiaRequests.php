<?php

namespace App\Http\Middleware;

use Illuminate\Http\Request;
use Inertia\Middleware;

class HandleInertiaRequests extends Middleware
{
    protected $rootView = 'app';

    public function version(Request $request): ?string
    {
        return parent::version($request);
    }

    /**
     * @return array<string, mixed>
     */
    public function share(Request $request): array
    {
        return [
            ...parent::share($request),
            'app' => [
                'name' => config('app.name'),
                'disclaimer' => __(config('geosafra.disclaimer')),
                'footerWarning' => __(config('geosafra.footer_warning')),
                'powerCitation' => __(config('geosafra.power_citation')),
            ],
            'auth' => [
                'user' => fn () => $request->user()?->only(['id', 'name', 'email']),
            ],
            'flash' => [
                'success' => fn () => $request->session()->get('success'),
                'error' => fn () => $request->session()->get('error'),
            ],
            // Glossário (doc 09) — carregado uma vez e usado pelos ícones "?".
            'glossary' => fn () => app()->isLocale('pt_BR') ? require database_path('data/glossary.php') : trans('glossary'),
        ];
    }
}
