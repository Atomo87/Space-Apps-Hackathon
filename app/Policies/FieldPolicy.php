<?php

namespace App\Policies;

use App\Models\Field;
use App\Models\User;

/**
 * Acesso livre (sem login): qualquer visitante vê, edita e exclui talhões.
 * Exceção: o exemplo público de referência (Uberlândia) pode ser visto, processado e simulado,
 * mas não editado nem excluído, para continuar disponível a todos.
 */
class FieldPolicy
{
    public function view(?User $user, Field $field): bool
    {
        return true;
    }

    public function update(?User $user, Field $field): bool
    {
        return ! $field->farm->isPublicDemo();
    }

    public function delete(?User $user, Field $field): bool
    {
        return ! $field->farm->isPublicDemo();
    }
}
