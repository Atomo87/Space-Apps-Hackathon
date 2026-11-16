<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            // Estresse observado por satélite (POST /v1/stress): MODIS LST e ET/PET. Nulo se o serviço falhou.
            $table->json('stress')->nullable()->after('vegetation');
        });
    }

    public function down(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            $table->dropColumn('stress');
        });
    }
};
