<?php

namespace Database\Seeders;

use App\Models\AssistantKnowledgeEntry;
use Illuminate\Database\Seeder;

class AssistantKnowledgeSeeder extends Seeder
{
    public function run(): void
    {
        $entries = [
            ['pt-BR', 'ndvi', 'O que é NDVI?', ['O que significa NDVI?'],
                'O NDVI é um índice de vegetação obtido por satélite. O GeoSafra usa o índice para acompanhar a cobertura verde do talhão ao longo do tempo. Palhada seca e solo exposto podem ter valores semelhantes.',
                'Glossário e metodologia do GeoSafra'],
            ['en-US', 'ndvi', 'What is NDVI?', ['What does NDVI mean?', 'What does NDVI stand for?'],
                'NDVI stands for Normalized Difference Vegetation Index. GeoSafra uses this satellite-derived index to track field greenness over time. Dry crop residue and bare soil can have similar values.',
                'GeoSafra glossary and methodology'],
            ['pt-BR', 'nasapower', 'O que é NASA POWER?', ['De onde vêm os dados climáticos do GeoSafra?'],
                'O NASA POWER é a fonte climática usada pelo GeoSafra. Ele combina observações e modelos em uma grade regional. Os dados representam as condições da região do talhão.',
                'Metodologia do GeoSafra · Dados da NASA'],
            ['en-US', 'nasapower', 'What is NASA POWER?', ['Where does GeoSafra get its weather data?'],
                'NASA POWER is the weather data source used by GeoSafra. It combines observations and models on a regional grid. The data represent conditions around the field.',
                'GeoSafra methodology · NASA data'],
            ['pt-BR', 'rotacoes', 'Como o GeoSafra compara rotações?', ['Como são calculadas as notas das rotações?'],
                'O GeoSafra compara a rotação atual e as alternativas com critérios como água, erosão, estrutura do solo, renda e mercado. As prioridades do produtor mudam o peso dos critérios na comparação.',
                'Metodologia do GeoSafra · Motor de rotação'],
            ['en-US', 'rotacoes', 'How does GeoSafra compare rotations?', ['How are crop rotation scores calculated?'],
                'GeoSafra compares the current crop rotation with alternatives using criteria such as water use, erosion, soil structure, income, and market fit. Grower priorities change the weight each criterion carries in the comparison.',
                'GeoSafra methodology · Crop rotation engine'],
        ];

        foreach ($entries as [$locale, $slug, $question, $aliases, $answer, $source]) {
            AssistantKnowledgeEntry::firstOrCreate(['locale' => $locale, 'slug' => $slug], [
                'question' => $question, 'aliases' => $aliases, 'answer' => $answer, 'source' => $source,
                'source_url' => '/metodologia', 'published_at' => now(),
            ]);
        }
    }
}
