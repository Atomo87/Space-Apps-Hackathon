<?php

// Mensagens de validação em português (somente as regras usadas no GeoSafra).
return [
    'accepted' => 'O campo :attribute deve ser aceito.',
    'after' => 'O campo :attribute deve ser uma data posterior a :date.',
    'array' => 'O campo :attribute deve ser uma lista.',
    'between' => [
        'numeric' => 'O campo :attribute deve estar entre :min e :max.',
        'string' => 'O campo :attribute deve ter entre :min e :max caracteres.',
        'array' => 'O campo :attribute deve ter entre :min e :max itens.',
    ],
    'boolean' => 'O campo :attribute deve ser sim ou não.',
    'date' => 'O campo :attribute não é uma data válida.',
    'exists' => 'O valor escolhido em :attribute não existe no catálogo.',
    'in' => 'O valor escolhido em :attribute é inválido.',
    'integer' => 'O campo :attribute deve ser um número inteiro.',
    'max' => [
        'numeric' => 'O campo :attribute não pode ser maior que :max.',
        'string' => 'O campo :attribute não pode ter mais de :max caracteres.',
        'array' => 'O campo :attribute não pode ter mais de :max itens.',
    ],
    'min' => [
        'numeric' => 'O campo :attribute deve ser pelo menos :min.',
        'string' => 'O campo :attribute deve ter pelo menos :min caracteres.',
        'array' => 'O campo :attribute deve ter pelo menos :min itens.',
    ],
    'numeric' => 'O campo :attribute deve ser um número.',
    'required' => 'O campo :attribute é obrigatório.',
    'required_if' => 'O campo :attribute é obrigatório quando :other é :value.',
    'required_with' => 'O campo :attribute é obrigatório quando :values está presente.',
    'size' => [
        'string' => 'O campo :attribute deve ter :size caracteres.',
    ],
    'string' => 'O campo :attribute deve ser um texto.',

    'attributes' => [
        'farm.state' => 'UF',
        'farm.municipality' => 'município',
        'field.area_ha' => 'área',
        'soil.ph_water' => 'pH',
        'soil.v_pct' => 'V%',
        'soil.clay_pct' => 'argila',
        'soil.organic_matter_pct' => 'matéria orgânica',
    ],
];
