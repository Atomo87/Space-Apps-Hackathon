<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/** Relevo do talhão (declividade e fator LS a partir do SRTM), devolvido por POST /v1/terrain do geo-service. */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            $table->json('terrain')->nullable()->after('climate');
        });
    }

    public function down(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            $table->dropColumn('terrain');
        });
    }
};
