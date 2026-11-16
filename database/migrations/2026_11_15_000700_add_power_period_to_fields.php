<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('fields', function (Blueprint $table) {
            // Período do clima (NASA POWER) escolhido pelo produtor. Nulo = padrão do geo-service.
            $table->unsignedSmallInteger('power_start_year')->nullable()->after('irrigation_mm_day');
            $table->unsignedSmallInteger('power_end_year')->nullable()->after('power_start_year');
        });
    }

    public function down(): void
    {
        Schema::table('fields', function (Blueprint $table) {
            $table->dropColumn(['power_start_year', 'power_end_year']);
        });
    }
};
