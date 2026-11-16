<?php

namespace App\Policies;

use App\Models\Farm;
use App\Models\User;

/** Acesso livre: prioridades de qualquer fazenda podem ser salvas, menos as do exemplo público. */
class FarmPolicy
{
    public function update(?User $user, Farm $farm): bool
    {
        return ! $farm->isPublicDemo();
    }
}
