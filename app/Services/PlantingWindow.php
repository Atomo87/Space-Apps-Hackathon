<?php

namespace App\Services;

use Carbon\CarbonImmutable;

/**
 * Janela de plantio ideal a partir da chuva e da temperatura diárias da NASA POWER.
 *
 * Para cada data candidata (semana a semana) e cada ano da série, verifica regras simples e explicáveis:
 *  - umidade para semear: pelo menos ONSET_MM de chuva nos 10 dias anteriores;
 *  - estabelecimento: nenhum veranico (DRY_SPELL_DAYS dias seguidos com menos de 1 mm) nos 30 dias seguintes;
 *  - água no ciclo: chuva nos 90 dias seguintes acima da necessidade da safra;
 *  - geada: mínima do ar ≤ 2 °C nos 90 dias seguintes;
 *  - calor na floração: dias com máxima ≥ 35 °C entre os dias 40 e 80 após a semeadura.
 * A nota de cada data é a fração de anos em que TODAS as condições foram atendidas (anos "bons").
 * Não substitui o zoneamento agrícola (ZARC) nem a recomendação do agrônomo.
 */
class PlantingWindow
{
    public const ONSET_MM = 20.0;

    public const DRY_SPELL_DAYS = 10;

    /** Safras avaliadas: datas candidatas (mês-dia), necessidade de chuva em 90 dias (mm) e se geada importa. */
    public const SEASONS = [
        'verao' => [
            'label' => 'Safra de verão',
            'crops' => 'soja, milho verão, feijão das águas, algodão',
            'from' => '09-01', 'to' => '12-31', 'need_mm' => 450.0, 'onset' => true, 'frost' => false,
        ],
        'safrinha' => [
            'label' => 'Segunda safra (safrinha)',
            'crops' => 'milho safrinha, sorgo, feijão, girassol',
            'from' => '01-10', 'to' => '04-10', 'need_mm' => 250.0, 'onset' => false, 'frost' => true,
        ],
        'inverno' => [
            'label' => 'Inverno',
            'crops' => 'trigo, aveia, cevada, plantas de cobertura',
            'from' => '03-15', 'to' => '06-30', 'need_mm' => 150.0, 'onset' => false, 'frost' => true,
        ],
    ];

    /**
     * @param  array<string, array{rain: float, tmin: float, tmax: float}>  $daily  chave AAAAMMDD
     */
    public function compute(array $daily): array
    {
        ksort($daily);
        $days = array_keys($daily);
        $index = array_flip($days);
        $first = CarbonImmutable::createFromFormat('Ymd', (string) $days[0])->startOfDay();
        $last = CarbonImmutable::createFromFormat('Ymd', (string) end($days))->startOfDay();
        $years = range($first->year, $last->year);

        $seasons = [];
        foreach (self::SEASONS as $key => $cfg) {
            $weeks = [];
            [$fm, $fd] = array_map('intval', explode('-', $cfg['from']));
            [$tm, $td] = array_map('intval', explode('-', $cfg['to']));
            $cursor = CarbonImmutable::create(2001, $fm, $fd);
            $end = CarbonImmutable::create(2001, $tm, $td);

            while ($cursor <= $end) {
                $stats = ['n' => 0, 'onset' => 0, 'dry' => 0, 'water' => 0, 'frost' => 0, 'good' => 0, 'heat' => 0];
                foreach ($years as $y) {
                    $sow = CarbonImmutable::create($y, $cursor->month, $cursor->day);
                    $sowKey = $sow->format('Ymd');
                    if (! isset($index[$sowKey]) || $sow->subDays(10) < $first || $sow->addDays(90) > $last) {
                        continue;
                    }
                    $i = $index[$sowKey];
                    $before = array_slice($days, max(0, $i - 10), 10);
                    $after30 = array_slice($days, $i, 30);
                    $after90 = array_slice($days, $i, 90);
                    if (count($after90) < 85) {
                        continue;
                    }

                    $rainBefore = array_sum(array_map(fn ($d) => $daily[$d]['rain'], $before));
                    $onsetOk = ! $cfg['onset'] || $rainBefore >= self::ONSET_MM;
                    $dry = $this->longestDrySpell(array_map(fn ($d) => $daily[$d]['rain'], $after30)) >= self::DRY_SPELL_DAYS;
                    $water = array_sum(array_map(fn ($d) => $daily[$d]['rain'], $after90)) >= $cfg['need_mm'];
                    $frost = $cfg['frost'] && min(array_map(fn ($d) => $daily[$d]['tmin'], $after90)) <= 2.0;
                    $heat = count(array_filter(array_slice($after90, 40, 40), fn ($d) => $daily[$d]['tmax'] >= 35.0));

                    $stats['n']++;
                    $stats['onset'] += $onsetOk ? 1 : 0;
                    $stats['dry'] += $dry ? 1 : 0;
                    $stats['water'] += $water ? 1 : 0;
                    $stats['frost'] += $frost ? 1 : 0;
                    $stats['heat'] += $heat;
                    $stats['good'] += ($onsetOk && ! $dry && $water && ! $frost) ? 1 : 0;
                }

                if ($stats['n'] >= 5) {
                    $n = $stats['n'];
                    $weeks[] = [
                        'date' => $cursor->format('m-d'),
                        'label' => $cursor->locale('pt_BR')->isoFormat('D MMM'),
                        'years' => $n,
                        'score' => round($stats['good'] / $n, 2),
                        'p_onset' => $cfg['onset'] ? round($stats['onset'] / $n, 2) : null,
                        'p_dry_spell' => round($stats['dry'] / $n, 2),
                        'p_water' => round($stats['water'] / $n, 2),
                        'p_frost' => $cfg['frost'] ? round($stats['frost'] / $n, 2) : null,
                        'heat_days' => round($stats['heat'] / $n, 1),
                    ];
                }
                $cursor = $cursor->addDays(7);
            }

            $seasons[] = ['key' => $key] + array_intersect_key($cfg, array_flip(['label', 'crops', 'need_mm'])) + [
                'weeks' => $weeks,
                'best' => $this->bestWindow($weeks),
            ];
        }

        return [
            'source' => 'NASA POWER (diário: PRECTOTCORR, T2M_MIN, T2M_MAX)',
            'period' => ['start' => $first->year, 'end' => $last->year],
            'rules' => [
                'onset_mm' => self::ONSET_MM,
                'dry_spell_days' => self::DRY_SPELL_DAYS,
                'frost_tmin_c' => 2.0,
                'heat_tmax_c' => 35.0,
            ],
            'seasons' => $seasons,
        ];
    }

    private function longestDrySpell(array $rain): int
    {
        $best = $run = 0;
        foreach ($rain as $mm) {
            $run = $mm < 1.0 ? $run + 1 : 0;
            $best = max($best, $run);
        }

        return $best;
    }

    /** Maior sequência de semanas com nota ≥ 85% da melhor (e pelo menos 0,5). */
    private function bestWindow(array $weeks): ?array
    {
        if (! $weeks) {
            return null;
        }
        $top = max(array_column($weeks, 'score'));
        if ($top < 0.5) {
            return ['start' => null, 'end' => null, 'score' => $top, 'level' => 'low'];
        }
        $cut = max(0.5, $top * 0.85);
        $bestRun = $run = [];
        foreach ($weeks as $i => $w) {
            // Uma semana isolada abaixo do corte (entre duas boas) não quebra a janela.
            $gap = $w['score'] < $cut && $run && ($weeks[$i + 1]['score'] ?? 0) >= $cut && $w['score'] >= 0.5;
            if ($w['score'] >= $cut || $gap) {
                $run[] = $w;
                if (count($run) > count($bestRun)) {
                    $bestRun = $run;
                }
            } else {
                $run = [];
            }
        }

        return [
            'start' => $bestRun[0]['label'],
            'end' => end($bestRun)['label'],
            'score' => round(array_sum(array_column($bestRun, 'score')) / count($bestRun), 2),
            'level' => $top >= 0.7 ? 'good' : 'medium',
        ];
    }
}
