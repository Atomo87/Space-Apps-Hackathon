<?php

namespace App\Services\Assistant;

/**
 * Catálogo de evidências verificáveis do talhão: cada número que a IA pode citar vira um "fato"
 * com identificador, indicador, valor, unidade, período e fonte. A IA só pode afirmar o que
 * estiver aqui (ou na base de conhecimento), e o servidor confere cada citação.
 */
class EvidenceCatalog
{
    private const MONTHS = [1 => 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

    private const EN_MONTHS = [1 => 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    /** @var array<string, array{id:string,label:string,value:float|int|string,unit:?string,period:?string,source:string,dataset:string}> */
    private array $facts = [];

    /**
     * @param  array<string,mixed>  $analysis  resposta de /v1/analysis
     * @param  array<string,mixed>|null  $planting  janela de plantio (NASA POWER diário)
     * @param  array<string,mixed>|null  $fires  focos de queimada (NASA FIRMS)
     */
    public static function build(array $analysis, ?array $planting = null, ?array $fires = null): self
    {
        $c = new self;
        $months = app()->isLocale('pt_BR') ? self::MONTHS : self::EN_MONTHS;
        $d = $analysis['diagnosis'] ?? [];
        $src = $d['source']['period'] ?? null;
        $climate = $src ? substr((string) $src['start'], 0, 4).'–'.substr((string) $src['end'], 0, 4) : null;
        $power = 'NASA POWER (clima diário, grade ~50 km)';

        // ---- Clima (NASA POWER) ----
        $monthly = $d['monthly'] ?? [];
        $rain = array_sum(array_map(fn ($m) => (float) ($m['rain_mm']['mean'] ?? 0), $monthly));
        if ($rain > 0) {
            $c->add('clima.chuva_anual', 'Chuva média anual', round($rain), 'mm/ano', $climate, $power, 'POWER');
        }
        $deficit = array_values(array_filter($monthly, fn ($m) => ($m['water_balance_mm'] ?? 0) < -20));
        if ($monthly) {
            $c->add('clima.meses_deficit', 'Meses com balanço hídrico negativo (< −20 mm)', count($deficit) ? implode(', ', array_map(fn ($m) => $months[$m['month']] ?? $m['name'], $deficit)) : 'nenhum', null, $climate, $power, 'POWER');
        }
        $s = $d['season'] ?? [];
        $c->add('clima.veranico_10', 'Safras com veranico de 10 dias ou mais', $s['pct_seasons_dry_spell_ge_10'] ?? null, '%', $climate, $power, 'POWER');
        $c->add('clima.veranico_p90', 'Veranico mais longo em 9 de cada 10 safras', $s['dry_spell_p90_days'] ?? null, 'dias', $climate, $power, 'POWER');
        $e = $d['extremes'] ?? [];
        $c->add('clima.chuva_max_dia', 'Maior chuva em um dia (média dos anos)', $e['annual_max_1day_mm_mean'] ?? null, 'mm', $climate, $power, 'POWER');
        $t = $d['trends'] ?? [];
        if (($t['tmax_c']['per_decade'] ?? null) !== null) {
            $c->add('clima.tendencia_tmax', __('Tendência da temperatura máxima (p = :p)', ['p' => round((float) ($t['tmax_c']['p_value'] ?? 1), 2)]), round((float) $t['tmax_c']['per_decade'], 2), '°C por década', $climate, $power, 'POWER');
        }
        if (($t['rain_mm']['per_decade'] ?? null) !== null) {
            $c->add('clima.tendencia_chuva', __('Tendência da chuva anual (p = :p)', ['p' => round((float) ($t['rain_mm']['p_value'] ?? 1), 2)]), round((float) $t['rain_mm']['per_decade']), 'mm por década', $climate, $power, 'POWER');
        }
        $r = $d['recent'] ?? [];
        if (($r['rain_anomaly_pct'] ?? null) !== null) {
            $years = $r['years'] ?? [];
            $c->add('clima.chuva_recente', 'Chuva dos últimos anos em relação à média', round((float) $r['rain_anomaly_pct']), '%', $years ? min($years).'–'.max($years) : null, $power, 'POWER');
        }
        $frost = collect($monthly)->filter(fn ($m) => ($m['frost_prob'] ?? 0) > 0)->sortByDesc('frost_prob')->first();
        $c->add('clima.geada', 'Maior chance mensal de geada', $frost ? __(':value% em :month', ['value' => round((float) $frost['frost_prob'] * 100), 'month' => $months[$frost['month']] ?? '']) : '0%', null, $climate, $power, 'POWER');
        $heat = collect($monthly)->sortByDesc('heat_days_34')->first();
        if ($heat && ($heat['heat_days_34'] ?? 0) > 0) {
            $c->add('clima.calor', 'Mês com mais dias acima de 34 °C', __(':value dias/mês em :month', ['value' => round((float) $heat['heat_days_34'], 1), 'month' => $months[$heat['month']] ?? '']), null, $climate, $power, 'POWER');
        }
        $risky = collect($d['calendar'] ?? [])->filter(fn ($m) => collect(['heat', 'frost', 'drought', 'heavy_rain'])->contains(fn ($k) => ($m[$k] ?? 0) === 2));
        if ($d['calendar'] ?? null) {
            $c->add('clima.meses_risco_alto', 'Meses com risco climático alto', $risky->count() ? $risky->map(fn ($m) => $months[$m['month']] ?? $m['name'])->implode(', ') : 'nenhum', null, $climate, 'Calendário de vulnerabilidade (NASA POWER + histórico do produtor)', 'POWER');
        }

        // ---- Relevo (SRTM) ----
        if ($tr = $d['terrain'] ?? null) {
            $srtm = 'NASA SRTM (elevação, 30 m)';
            $c->add('relevo.declividade', 'Declividade média do talhão', $tr['slope_pct']['mean'] ?? null, '%', 'missão de 2000', $srtm, 'SRTM');
            $c->add('relevo.classe', 'Classe de relevo', $tr['relief_class'] ?? null, null, 'missão de 2000', $srtm, 'SRTM');
            $c->add('relevo.ls', 'Fator LS de erosão (relevo)', $tr['ls_factor'] ?? null, null, 'missão de 2000', $srtm, 'SRTM');
        }

        // ---- Vegetação (HLS / MODIS) ----
        if ($v = $d['vegetation'] ?? null) {
            $useHls = ! empty($v['hls']['recent']);
            $veg = $useHls ? $v['hls'] : $v;
            $vSrc = $useHls ? 'NASA HLS (Landsat + Sentinel-2, 30 m)' : 'NASA MODIS NDVI (250 m)';
            $vCode = $useHls ? 'HLS' : 'MODIS';
            $cov = $veg['coverage'] ?? [];
            $vPeriod = isset($cov['start'], $cov['end']) ? $cov['start'].__(' a ').$cov['end'] : null;
            if ($rec = $veg['recent'] ?? null) {
                $c->add('veg.ndvi_recente', 'NDVI da imagem mais recente', $rec['ndvi'] ?? null, null, $rec['date'] ?? null, $vSrc, $vCode);
                if (($rec['anomaly'] ?? null) !== null) {
                    $c->add('veg.anomalia', 'Diferença do NDVI recente para o normal do mês', $rec['anomaly'], null, $rec['date'] ?? null, $vSrc, $vCode);
                }
            }
            $low = $veg['low_green_months'] ?? [];
            $c->add('veg.meses_pouco_verde', 'Meses com pouco verde (solo exposto ou palhada)', $low ? implode(', ', array_map(fn ($m) => $months[$m] ?? $m, $low)) : 'nenhum', null, $vPeriod, $vSrc, $vCode);
            if ($peak = $veg['peak'] ?? null) {
                $c->add('veg.pico', 'Mês de maior verde', ($months[$peak['month']] ?? $peak['name']).' (NDVI '.$peak['ndvi'].')', null, $vPeriod, $vSrc, $vCode);
            }
        }

        // ---- Estresse (MODIS LST e ET/PET) ----
        if ($st = $d['stress'] ?? null) {
            if ($et = $st['et'] ?? null) {
                $years = array_column($et['yearly'] ?? [], 'year');
                $c->add('estresse.et_pet', 'Razão ET/PET (água usada ÷ água pedida pelo clima)', $et['ratio'] ?? null, null, $years ? min($years).'–'.max($years) : null, 'NASA MODIS ET/PET (500 m)', 'MODIS ET');
                $c->add('estresse.nivel', 'Nível de estresse hídrico observado', $et['stress'] ?? null, null, $years ? min($years).'–'.max($years) : null, 'NASA MODIS ET/PET (500 m)', 'MODIS ET');
            }
            if (($lst = $st['lst'] ?? null) && ($h = $lst['hottest'] ?? null)) {
                $cov = $lst['coverage'] ?? [];
                $c->add('estresse.lst', 'Superfície mais quente (mediana do mês)', __(':value °C em :month', ['value' => round((float) $h['p50'], 1), 'month' => $months[$h['month']] ?? $h['name']]), null, isset($cov['start']) ? $cov['start'].__(' a ').$cov['end'] : null, 'NASA MODIS LST (1 km)', 'MODIS LST');
            }
        }

        // ---- Earthdata (SMAP, GPM, ECOSTRESS, GRACE-FO) ----
        $ed = $d['earthdata'] ?? [];
        if ($sm = $ed['smap'] ?? null) {
            $cov = $sm['coverage'] ?? [];
            $p = isset($cov['start']) ? $cov['start'].__(' a ').$cov['end'] : null;
            if (($sm['recent']['anomaly'] ?? null) !== null) {
                $c->add('smap.anomalia', 'Umidade do solo recente em relação ao normal', $sm['recent']['anomaly'], 'm³/m³', $p, 'NASA SMAP (umidade do solo, 9 km)', 'SMAP');
            }
            $c->add('smap.meses_secos', 'Meses de solo mais seco', ($sm['dry_months'] ?? []) ? implode(', ', array_map(fn ($m) => $months[$m] ?? $m, $sm['dry_months'])) : 'nenhum', null, $p, 'NASA SMAP (umidade do solo, 9 km)', 'SMAP');
        }
        if ($g = $ed['gpm'] ?? null) {
            $cov = $g['coverage'] ?? [];
            $p = isset($cov['start']) ? $cov['start'].__(' a ').$cov['end'] : null;
            $c->add('gpm.chuva_anual', 'Chuva anual medida por satélite', $g['annual_mm'] ?? null, 'mm/ano', $p, 'NASA GPM IMERG (~11 km)', 'GPM');
            if (isset($g['vs_power_pct'])) {
                $c->add('gpm.vs_power', 'Diferença da chuva do GPM para a do POWER', $g['vs_power_pct'], '%', $p, 'NASA GPM IMERG × NASA POWER', 'GPM');
            }
        }
        if ($eco = $ed['ecostress'] ?? null) {
            $c->add('ecostress.esi', 'Índice de estresse evaporativo (mediana)', $eco['median_esi'] ?? null, null, __(':count passagens sem nuvem', ['count' => $eco['passes'] ?? '?']), 'NASA ECOSTRESS (70 m)', 'ECOSTRESS');
        }
        if ($gr = $ed['grace'] ?? null) {
            $cov = $gr['coverage'] ?? [];
            $c->add('grace.tendencia', __('Tendência da água armazenada na região (p = :p)', ['p' => round((float) ($gr['trend_p_value'] ?? 1), 2)]), $gr['trend_cm_per_decade'] ?? null, 'cm por década', isset($cov['start']) ? $cov['start'].__(' a ').$cov['end'] : null, 'NASA GRACE-FO (regional)', 'GRACE');
        }

        // ---- Janela de plantio (NASA POWER diário) ----
        foreach ($planting['seasons'] ?? [] as $season) {
            $b = $season['best'] ?? null;
            if (! $b) {
                continue;
            }
            $value = $b['start'] ? $b['start'].($b['end'] !== $b['start'] ? ' a '.$b['end'] : '').' ('.__(':score% dos anos bons', ['score' => round($b['score'] * 100)]).')' : 'sem janela segura sem irrigação';
            $per = isset($planting['period']) ? $planting['period']['start'].'–'.$planting['period']['end'] : null;
            $c->add('plantio.'.$season['key'], __('Melhor janela de plantio — :season', ['season' => __($season['label'])]), $value, null, $per, 'NASA POWER diário (chuva e temperatura)', 'POWER');
        }

        // ---- Queimadas (NASA FIRMS) ----
        if (($fires['configured'] ?? false) && ($fires['counts'] ?? null)) {
            $p = __('últimos :days dias', ['days' => $fires['days']]);
            $c->add('fogo.10km', 'Focos de queimada a até 10 km', $fires['counts']['10'] ?? 0, 'focos', $p, 'NASA FIRMS (VIIRS e MODIS)', 'FIRMS');
            $c->add('fogo.25km', 'Focos de queimada a até 25 km', $fires['counts']['25'] ?? 0, 'focos', $p, 'NASA FIRMS (VIIRS e MODIS)', 'FIRMS');
            if ($fires['nearest_km'] !== null) {
                $c->add('fogo.mais_proximo', 'Distância do foco mais próximo', $fires['nearest_km'], 'km', $p, 'NASA FIRMS (VIIRS e MODIS)', 'FIRMS');
            }
        }

        // ---- Estratégias (motor de critérios) ----
        foreach ($analysis['strategies'] ?? [] as $i => $str) {
            $range = $str['score_range'] ?? null;
            $c->add('estrategia.'.($str['label'] ?? $i), __($str['is_current'] ?? false ? 'Nota da rotação atual: :title' : 'Nota da estratégia :label: :title', ['label' => $str['label'] ?? '', 'title' => $str['title'] ?? '']), $str['score'] ?? null, __('pontos de 100').($range ? ' ('.__('faixa :p10–:p90 entre anos secos e chuvosos', $range).')' : ''), $climate, 'Motor GeoSafra (10 critérios, prioridades do produtor)', 'GeoSafra');
        }

        if (($d['source']['dataset_code'] ?? null) === 'DEMO') {
            foreach ($c->facts as $id => $fact) {
                if ($fact['dataset'] === 'POWER' || $fact['dataset'] === 'GeoSafra') {
                    $c->facts[$id]['source'] = __('Dados climáticos ilustrativos');
                    $c->facts[$id]['dataset'] = 'DEMO';
                }
            }
        }

        return $c;
    }

    private function add(string $id, string $label, mixed $value, ?string $unit, ?string $period, string $source, string $dataset): void
    {
        if ($value === null || $value === '') {
            return;
        }
        if (is_float($value)) {
            $value = round($value, 3);
        }
        $label = __($label);
        $value = is_string($value) ? __($value) : $value;
        $unit = $unit === null ? null : __($unit);
        $period = $period === null ? null : __($period);
        $source = __($source);
        $this->facts[$id] = compact('id', 'label', 'value', 'unit', 'period', 'source', 'dataset');
    }

    /** @return array<string, array<string,mixed>> */
    public function all(): array
    {
        return $this->facts;
    }

    public function has(string $id): bool
    {
        return isset($this->facts[$id]);
    }

    /** Números presentes nos fatos citados (para conferir os números escritos pela IA). */
    public function numbersOf(array $ids): array
    {
        $nums = [];
        foreach ($ids as $id) {
            $f = $this->facts[$id] ?? null;
            if (! $f) {
                continue;
            }
            $text = $f['value'].' '.$f['unit'].' '.$f['label'].' '.$f['period'].' '.$f['source'];
            preg_match_all('/-?\d+(?:[.,]\d+)?/', $text, $m);
            foreach ($m[0] as $n) {
                $nums[] = (float) str_replace(',', '.', $n);
            }
        }

        return $nums;
    }
}
