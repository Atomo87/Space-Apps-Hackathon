<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            // Resumo do NDVI MODIS (POST /v1/vegetation). Nulo quando o serviço de imagens falhou.
            $table->json('vegetation')->nullable()->after('terrain');
        });
    }

    public function down(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            $table->dropColumn('vegetation');
        });
    }
};
