<?php

/*
 * Sobrescreve só o necessário do pacote inertiajs/inertia-laravel:
 * as páginas ficam em resources/js/pages (minúsculo). Em Linux/CI o padrão "js/Pages" não as encontraria.
 */
return [

    'page_paths' => [
        resource_path('js/pages'),
    ],

    'page_extensions' => ['vue', 'ts'],

    'testing' => [
        'ensure_pages_exist' => true,
        'page_paths' => [
            resource_path('js/pages'),
        ],
        'page_extensions' => ['vue', 'ts'],
    ],

];
