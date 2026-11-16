<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Modelo de dados do MVP (recorte do doc 05).
 * Simplificações do hackathon, registradas no README:
 *  - geometria guardada como GeoJSON (JSON) + latitude/longitude do centróide,
 *    em vez de POLYGON/POINT espaciais — o POWER responde por ponto;
 *  - estratégias calculadas sob demanda pelo geo-service (determinísticas) em vez de persistidas;
 *  - o cache das respostas da NASA POWER fica no geo-service (Python), não no MySQL.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('crops', function (Blueprint $table) {
            $table->id();
            $table->string('slug', 60)->unique();
            $table->string('name_pt', 80);
            $table->string('scientific_name', 120)->nullable();
            $table->string('family', 60);
            $table->string('category', 20);
            $table->json('traits');       // atributos agronômicos (fonte: geo-service/app/catalog/crops.json)
            $table->json('sources');      // fonte de cada atributo ou "hipótese a validar"
            $table->timestamps();
        });

        Schema::create('farms', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->nullable()->constrained()->nullOnDelete();
            $table->string('name', 150);
            $table->string('municipality', 150)->nullable();
            $table->char('state', 2)->nullable();
            $table->char('country_code', 2)->default('BR');
            $table->boolean('has_livestock')->default(false);
            $table->timestamps();
        });

        Schema::create('fields', function (Blueprint $table) {
            $table->id();
            $table->foreignId('farm_id')->constrained()->cascadeOnDelete();
            $table->string('name', 100);
            $table->decimal('latitude', 9, 6);
            $table->decimal('longitude', 9, 6);
            $table->json('boundary')->nullable();          // GeoJSON Polygon (SRID 4326)
            $table->decimal('area_ha', 10, 2)->nullable();
            $table->boolean('irrigated')->default(false);
            $table->decimal('irrigation_mm_day', 5, 2)->nullable();
            $table->string('status', 20)->default('pending'); // pending|processing|ready|error
            $table->text('status_message')->nullable();
            $table->timestamp('analyzed_at')->nullable();
            $table->timestamps();
        });

        Schema::create('field_soil_profiles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('field_id')->unique()->constrained()->cascadeOnDelete();
            $table->string('source', 30);                   // lab_analysis|farmer_estimate|unknown
            $table->date('sampled_at')->nullable();
            $table->string('texture', 20)->nullable();      // arenosa|media|argilosa|muito_argilosa
            $table->decimal('clay_pct', 5, 2)->nullable();
            $table->decimal('ph_water', 4, 2)->nullable();
            $table->decimal('organic_matter_pct', 5, 2)->nullable();
            $table->decimal('p_mg_dm3', 7, 2)->nullable();
            $table->decimal('k_cmolc_dm3', 6, 3)->nullable();
            $table->decimal('ctc_cmolc_dm3', 6, 2)->nullable();
            $table->decimal('v_pct', 5, 2)->nullable();     // saturação por bases
            $table->smallInteger('depth_cm')->nullable();
            $table->timestamps();
        });

        Schema::create('crop_history', function (Blueprint $table) {
            $table->id();
            $table->foreignId('field_id')->constrained()->cascadeOnDelete();
            $table->foreignId('crop_id')->constrained()->restrictOnDelete();
            $table->date('sown_at');
            $table->date('harvested_at');
            $table->decimal('yield_t_ha', 6, 2)->nullable();
            $table->text('notes')->nullable();
            $table->timestamps();
            $table->index(['field_id', 'sown_at']);
        });

        // Um peso (0–5) para cada critério do motor — correspondência 1:1.
        Schema::create('farmer_priorities', function (Blueprint $table) {
            $table->foreignId('farm_id')->primary()->constrained()->cascadeOnDelete();
            foreach (['save_water', 'soil_structure', 'n_fixation', 'erosion_control', 'organic_matter',
                'pest_break', 'forage', 'extra_income', 'market_fit'] as $col) {
                $table->unsignedTinyInteger($col)->default(3);
            }
            $table->timestamps();
        });

        Schema::create('farm_constraints', function (Blueprint $table) {
            $table->foreignId('farm_id')->primary()->constrained()->cascadeOnDelete();
            $table->json('excluded_crops');      // slugs que o produtor não quer/ não pode plantar
            $table->json('buyer_crops');         // slugs com comprador conhecido
            $table->json('no_buyer_crops');      // slugs sem comprador na região
            $table->json('missing_equipment');   // ex.: ["plantio_graos_miudos"]
            $table->text('notes')->nullable();
            $table->timestamps();
        });

        Schema::create('field_analyses', function (Blueprint $table) {
            $table->id();
            $table->foreignId('field_id')->unique()->constrained()->cascadeOnDelete();
            $table->string('engine_version', 20);
            $table->longText('climate');         // ClimateProfile devolvido pelo geo-service (JSON)
            $table->timestamp('computed_at');
            $table->timestamps();
        });

        Schema::create('feedbacks', function (Blueprint $table) {
            $table->id();
            $table->foreignId('field_id')->constrained()->cascadeOnDelete();
            $table->string('strategy_key', 60);
            $table->string('verdict', 20);       // makes_sense|not_applicable|needs_adjustment
            $table->text('comment')->nullable();
            $table->json('snapshot')->nullable(); // estratégia como foi exibida
            $table->timestamps();
        });
    }

    public function down(): void
    {
        foreach (['feedbacks', 'field_analyses', 'farm_constraints', 'farmer_priorities',
            'crop_history', 'field_soil_profiles', 'fields', 'farms', 'crops'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
