<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

/**
 * Conta de TESTE para desenvolvimento local (XAMPP / artisan serve).
 *
 *   E-mail: produtor.teste@geosafra.test
 *   Senha:  safra-teste-2026
 *
 * Só roda em APP_ENV=local. Em produção, nenhuma conta é criada por seeder.
 * Uso: php artisan db:seed --class=TestUserSeeder (recria a senha se a conta já existir).
 */
class TestUserSeeder extends Seeder
{
    public const EMAIL = 'produtor.teste@geosafra.test';

    public const PASSWORD = 'safra-teste-2026';

    public function run(): void
    {
        if (! app()->isLocal()) {
            $this->command?->warn('TestUserSeeder ignorado: só roda com APP_ENV=local.');

            return;
        }

        User::updateOrCreate(
            ['email' => self::EMAIL],
            ['name' => 'Produtor Teste', 'password' => Hash::make(self::PASSWORD)],
        );

        $this->command?->info('Conta de teste pronta: '.self::EMAIL.' (senha no topo de database/seeders/TestUserSeeder.php).');
    }
}
