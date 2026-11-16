<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        $this->call(CropSeeder::class);
        $this->call(AssistantKnowledgeSeeder::class);
        $this->call(TestUserSeeder::class); // só age em APP_ENV=local
    }
}
