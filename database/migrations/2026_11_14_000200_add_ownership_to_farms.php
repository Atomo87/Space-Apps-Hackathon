<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Contas de usuário: cada propriedade pertence a um usuário (farms.user_id, já existente).
 * `is_demo` marca o caso público de demonstração (Uberlândia), visível sem login e somente leitura.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('farms', function (Blueprint $table) {
            $table->boolean('is_demo')->default(false)->after('user_id');
            $table->index(['user_id', 'is_demo']);
        });
    }

    public function down(): void
    {
        Schema::table('farms', function (Blueprint $table) {
            $table->dropIndex(['user_id', 'is_demo']);
            $table->dropColumn('is_demo');
        });
    }
};
