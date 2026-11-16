<!DOCTYPE html>
<html lang="{{ app()->getLocale() === 'pt_BR' ? 'pt-BR' : 'en-US' }}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#052e16">
        <meta name="description" content="{{ app()->getLocale() === 'pt_BR' ? 'GeoSafra usa observações da Terra da NASA para comparar rotações de culturas e fortalecer a saúde do solo.' : 'GeoSafra uses NASA Earth observations to compare crop rotations and improve soil health.' }}">
        {{-- Prefixo do app quando ele roda em subpasta (ex.: /geosafra/public no XAMPP); vazio na raiz do domínio. --}}
        <meta name="base-path" content="{{ request()->getBaseUrl() }}">
        <link rel="icon" href="{{ asset('favicon.svg') }}" type="image/svg+xml">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&amp;family=Inter:wght@400;500;600;700;800;900&amp;display=swap" rel="stylesheet">
        <title inertia>{{ config('app.name', 'GeoSafra') }}</title>
        @vite(['resources/js/app.ts'])
        @inertiaHead
    </head>
    <body class="min-h-full bg-stone-50 font-sans text-stone-900 antialiased">
        @inertia
    </body>
</html>
