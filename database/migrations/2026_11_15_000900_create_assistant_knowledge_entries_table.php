<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('assistant_knowledge_entries', function (Blueprint $table) {
            $table->id();
            $table->string('locale', 5);
            $table->string('slug', 120);
            $table->string('question', 500);
            $table->json('aliases')->nullable();
            $table->text('answer');
            $table->string('source');
            $table->text('source_url')->nullable();
            $table->timestamp('published_at')->nullable();
            $table->timestamps();
            $table->unique(['locale', 'slug']);
            $table->index(['locale', 'published_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('assistant_knowledge_entries');
    }
};
