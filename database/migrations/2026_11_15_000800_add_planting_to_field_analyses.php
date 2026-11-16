<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            // Janela de plantio calculada com a chuva e a temperatura diárias da NASA POWER.
            $table->json('planting')->nullable()->after('earthdata');
        });
    }

    public function down(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            $table->dropColumn('planting');
        });
    }
};
