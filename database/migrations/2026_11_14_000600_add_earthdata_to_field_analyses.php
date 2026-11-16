<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            // SMAP, GPM IMERG, ECOSTRESS e GRACE-FO (POST /v1/earthdata). Nulo sem token Earthdata ou se tudo falhou.
            $table->json('earthdata')->nullable()->after('stress');
        });
    }

    public function down(): void
    {
        Schema::table('field_analyses', function (Blueprint $table) {
            $table->dropColumn('earthdata');
        });
    }
};
