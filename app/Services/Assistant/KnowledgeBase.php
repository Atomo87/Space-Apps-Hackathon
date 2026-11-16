<?php

namespace App\Services\Assistant;

use App\Models\AssistantKnowledgeEntry;
use Illuminate\Database\Eloquent\Collection;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Str;

/**
 * Base de conhecimento do assistente (o "R" do RAG): trechos curtos e rastreáveis de
 *  - glossário do GeoSafra (database/data/glossary.php);
 *  - metodologia: indicadores e motor (docs/indicadores.md, docs/motor.md);
 *  - catálogo de culturas com a fonte de cada atributo (geo-service/app/catalog/crops.json).
 * A busca BM25 usa o vocabulário em português e inglês, sem acentos nem palavras vazias.
 */
class KnowledgeBase
{
    private const STOP = ['a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'no', 'na', 'nos', 'nas', 'um', 'uma', 'uns', 'umas', 'para', 'por', 'com', 'sem', 'que', 'se', 'ao', 'aos', 'ou', 'mais', 'menos', 'como', 'qual', 'quais', 'quando', 'onde', 'meu', 'minha', 'meus', 'minhas', 'seu', 'sua', 'e', 'é', 'ser', 'esta', 'este', 'isso', 'isto', 'ha', 'tem', 'ter', 'pelo', 'pela', 'entre', 'sobre', 'muito', 'devo', 'posso', 'vale', 'pena', 'talhao', 'lavoura'];

    private const EN_STOP = ['the', 'of', 'to', 'and', 'or', 'in', 'on', 'at', 'by', 'for', 'is', 'are', 'was', 'with', 'it', 'what', 'which', 'when', 'how', 'why', 'do', 'does', 'can', 'should', 'my', 'this', 'about', 'your', 'field'];

    /** @return list<array{id:string,title:string,text:string,source:string,url:?string}> */
    public function chunks(): array
    {
        $locale = app()->getLocale();
        $files = [database_path('data/glossary.php'), lang_path('en/glossary.php'), lang_path('en.json'), base_path('docs/indicadores.md'), base_path('docs/motor.md'), base_path('geo-service/app/catalog/crops.json')];
        $version = md5(implode('|', array_map(fn ($f) => is_file($f) ? filemtime($f).filesize($f) : 'x', $files)));

        $files = Cache::rememberForever("kb-chunks:{$locale}:{$version}", fn () => array_merge($this->glossary(), $this->docs(), $this->crops()));

        return array_merge($files, $this->publishedEntries()->map(fn (AssistantKnowledgeEntry $entry) => $entry->toReference() + [
            'search_terms' => implode(' ', $entry->aliases ?? []),
        ])->all());
    }

    public function matchAnswer(string $question): ?array
    {
        $normalized = $this->normalizeQuestion($question);
        if ($normalized === '') {
            return null;
        }

        $matches = $this->publishedEntries()->filter(fn (AssistantKnowledgeEntry $entry) => in_array(
            $normalized,
            array_map($this->normalizeQuestion(...), [$entry->question, ...($entry->aliases ?? [])]),
            true,
        ));

        return $matches->count() === 1 ? $matches->first()->toReference() : null;
    }

    private function normalizeQuestion(string $question): string
    {
        $text = Str::lower(Str::ascii($question));

        // Não remova sinais matemáticos, números ou palavras: mudam o sentido da pergunta.
        return trim(preg_replace('/\s+/', ' ', trim($text, " \t\n\r?.!¿¡")));
    }

    /** @return Collection<int, AssistantKnowledgeEntry> */
    private function publishedEntries(): Collection
    {
        return AssistantKnowledgeEntry::query()
            ->where('locale', app()->isLocale('pt_BR') ? 'pt-BR' : 'en-US')
            ->where('published_at', '<=', now())
            ->orderBy('id')
            ->get();
    }

    /**
     * Os trechos mais relevantes para a pergunta (BM25).
     *
     * @return list<array{id:string,title:string,text:string,source:string,url:?string,score:float}>
     */
    public function search(string $query, int $k = 6): array
    {
        $chunks = $this->chunks();
        $q = array_unique($this->tokens($query));
        if (! $q || ! $chunks) {
            return [];
        }
        $docs = array_map(fn ($c) => $this->tokens($c['title'].' '.$c['title'].' '.$c['text'].' '.($c['search_terms'] ?? '')), $chunks);
        $n = count($docs);
        $avg = array_sum(array_map('count', $docs)) / max(1, $n);
        $df = [];
        foreach ($docs as $tokens) {
            foreach (array_unique($tokens) as $t) {
                $df[$t] = ($df[$t] ?? 0) + 1;
            }
        }
        $scored = [];
        foreach ($docs as $i => $tokens) {
            $tf = array_count_values($tokens);
            $len = count($tokens);
            $score = 0.0;
            foreach ($q as $t) {
                if (! isset($tf[$t])) {
                    continue;
                }
                $idf = log(1 + ($n - $df[$t] + 0.5) / ($df[$t] + 0.5));
                $score += $idf * ($tf[$t] * 2.2) / ($tf[$t] + 1.2 * (0.25 + 0.75 * $len / $avg));
            }
            if ($score > 0) {
                $scored[] = array_diff_key($chunks[$i], ['search_terms' => true]) + ['score' => round($score, 3)];
            }
        }
        usort($scored, fn ($a, $b) => $b['score'] <=> $a['score']);

        return array_slice($scored, 0, $k);
    }

    /** @return list<string> */
    private function tokens(string $text): array
    {
        $text = Str::lower(Str::ascii($text));
        preg_match_all('/[a-z0-9]{2,}/', $text, $m);

        // Radical simples (plural e gênero) para "veranicos"/"veranico", "secas"/"seca".
        return array_values(array_map(
            fn ($w) => strlen($w) > 4 ? preg_replace('/(oes|aes|ais|eis|s)$/', '', $w) : $w,
            array_filter($m[0], fn ($w) => ! in_array($w, self::STOP, true) && ! in_array($w, self::EN_STOP, true)),
        ));
    }

    private function glossary(): array
    {
        $portuguese = app()->isLocale('pt_BR');
        $en = trans('glossary', [], 'en');
        $out = [];
        foreach (require database_path('data/glossary.php') as $key => $original) {
            $english = $en[$key] ?? $original;
            $g = $portuguese ? $original : $english;
            $other = $portuguese ? $english : $original;
            $out[] = [
                'id' => "glossario.{$key}", 'title' => $g['term'], 'text' => $g['text'],
                'source' => __('Glossário GeoSafra'), 'url' => null, 'locale' => $portuguese ? 'pt-BR' : 'en-US',
                'search_terms' => $other['term'].' '.$other['text'],
            ];
        }

        return $out;
    }

    /** Documentos de metodologia, quebrados por seção e por linha de tabela. */
    private function docs(): array
    {
        $out = [];
        foreach (['indicadores' => 'Metodologia GeoSafra — indicadores históricos', 'motor' => 'Metodologia GeoSafra — motor de rotação'] as $file => $source) {
            $path = base_path("docs/{$file}.md");
            if (! is_file($path)) {
                continue;
            }
            $section = '';
            $i = 0;
            foreach (preg_split('/\R/', (string) file_get_contents($path)) as $line) {
                $line = trim($line);
                if (str_starts_with($line, '#')) {
                    $section = trim($line, "# \t");

                    continue;
                }
                if ($line === '' || preg_match('/^\|?\s*-{3,}/', $line) || str_starts_with($line, '| Indicador') || str_starts_with($line, '| Critério') || str_starts_with($line, '| Risco')) {
                    continue;
                }
                $text = trim(preg_replace(['/\*\*|`/', '/\s*\|\s*/'], ['', ' — '], $line), ' —');
                if (mb_strlen($text) < 25) {
                    continue;
                }
                $out[] = ['id' => "metodologia.{$file}.".(++$i), 'title' => $section, 'text' => $text, 'source' => __($source), 'url' => null, 'locale' => 'pt-BR'];
            }
        }

        return $out;
    }

    /** Uma ficha por cultura, com a fonte declarada de cada atributo. */
    private function crops(): array
    {
        $path = base_path('geo-service/app/catalog/crops.json');
        if (! is_file($path)) {
            return [];
        }
        $out = [];
        $tol = ['none' => 'nenhuma', 'low' => 'baixa', 'medium' => 'média', 'high' => 'alta'];
        foreach (json_decode((string) file_get_contents($path), true)['crops'] ?? [] as $c) {
            $name = __($c['name_pt']);
            $parts = [
                __(':crop (:scientific, família :family)', ['crop' => $name, 'scientific' => $c['scientific_name'], 'family' => $c['family']]),
                isset($c['cycle_days']) ? __('ciclo de :range dias', ['range' => implode(__(' a '), (array) $c['cycle_days'])]) : null,
                isset($c['t_base_c']) ? __('temperatura-base :value °C', ['value' => $c['t_base_c']]) : null,
                isset($c['t_heat_stress_c']) ? __('estresse por calor acima de :value °C', ['value' => $c['t_heat_stress_c']]) : null,
                isset($c['frost_tolerance']) ? __('tolerância a geada :value', ['value' => __($tol[$c['frost_tolerance']] ?? $c['frost_tolerance'])]) : null,
                isset($c['drought_tolerance']) ? __('tolerância à seca :value', ['value' => __($tol[$c['drought_tolerance']] ?? $c['drought_tolerance'])]) : null,
                isset($c['root_system']) ? __('raiz :value', ['value' => __($c['root_system'])]) : null,
                isset($c['n_credit_kg_ha']) ? __('crédito de nitrogênio :value kg/ha', ['value' => $c['n_credit_kg_ha']]) : null,
                isset($c['residue_t_ha']) ? __('palhada :value t/ha', ['value' => $c['residue_t_ha']]) : null,
                isset($c['ph_range']) ? 'pH '.implode(__(' a '), $c['ph_range']) : null,
            ];
            $risks = $c['local_review_risks'] ?? [];
            $sources = collect($c['sources'] ?? [])->map(fn ($s, $k) => "{$k}: {$s}")->implode('; ');
            $out[] = [
                'id' => "cultura.{$c['slug']}",
                'title' => __('Ficha da cultura: :crop', ['crop' => $name]),
                'text' => implode('; ', array_filter($parts)).'.'.($risks ? ' '.__('Conferir no campo: :risks.', ['risks' => implode('; ', array_map('__', $risks))]) : '').($sources ? ' '.__('Fontes dos atributos — :sources.', ['sources' => $sources]) : ''),
                'source' => __('Catálogo de culturas GeoSafra (atributos com fonte declarada)'),
                'url' => null,
                'locale' => app()->isLocale('pt_BR') ? 'pt-BR' : 'en-US',
                'search_terms' => $c['name_pt'].' '.trans($c['name_pt'], [], 'en'),
            ];
        }

        return $out;
    }
}
