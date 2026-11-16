<?php

return [

    // Serviço Python (FastAPI) da frente B: NASA POWER, indicadores e motor de rotação.
    'geo_service' => [
        'url' => rtrim(env('GEO_SERVICE_URL', 'http://127.0.0.1:8001'), '/'),
        'timeout' => (int) env('GEO_SERVICE_TIMEOUT', 240),
        // Mesmo valor de GEOSAFRA_TOKEN no Render (cabeçalho X-GeoSafra-Token).
        'token' => env('GEO_SERVICE_TOKEN', ''),
        // Faixa de anos da climatologia (o geo-service usa o próprio padrão se vazio).
        'start_year' => env('POWER_START_YEAR') ? (int) env('POWER_START_YEAR') : null,
        'end_year' => env('POWER_END_YEAR') ? (int) env('POWER_END_YEAR') : null,
    ],

    // NASA FIRMS (focos de queimada MODIS/VIIRS). Chave gratuita: https://firms.modaps.eosdis.nasa.gov/api/map_key/
    // Sem chave, o mapa ainda mostra os focos pela camada pública da NASA GIBS.
    'firms' => [
        'key' => env('FIRMS_MAP_KEY', ''),
        'days' => (int) env('FIRMS_DAYS', 7),
        'radius_km' => (int) env('FIRMS_RADIUS_KM', 50),
    ],

    // Assistente com IA (Google Gemini) + RAG. Sem chave, o assistente responde só com as evidências (sem IA).
    'ai' => [
        'enabled' => filter_var(env('INSIGHTS_ENABLED', true), FILTER_VALIDATE_BOOL),
        'key' => trim((string) env('GEMINI_API_KEY', '')),
        'model' => trim((string) env('GEMINI_MODEL', 'gemini-2.5-flash')),
        'endpoint' => env('GEMINI_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta'),
    ],

    'disclaimer' => 'Esta ferramenta apoia, mas não substitui, o conhecimento do agricultor e da assistência técnica local.',
    'footer_warning' => 'Estas sugestões se baseiam em dados de satélite e médias históricas. Confirme com seu conhecimento do campo e com um técnico antes de decidir.',
    'power_citation' => 'Dados: NASA Langley Research Center (LaRC) POWER Project, financiado pelo NASA Earth Science/Applied Science Program. https://power.larc.nasa.gov',
];
