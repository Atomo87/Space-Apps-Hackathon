<script setup lang="ts">
import { locale, t } from '@/lib/i18n';
import { computed } from 'vue';
import { VChart } from '@/lib/echarts';
import type { NdviSummary, Vegetation } from '@/types/contract';
import DatasetBadge from './DatasetBadge.vue';
import Icon from './Icon.vue';
import Term from './Term.vue';

const props = defineProps<{ vegetation: Vegetation }>();
const modis = computed(() => props.vegetation);
const hls = computed(() => props.vegetation.hls ?? null);
// Referência: HLS 30 m (escala do talhão) quando cobre ao menos 10 meses; senão MODIS 250 m. Mesma regra do motor.
const usesHls = computed(() => !!hls.value && hls.value.monthly.filter((m) => m.p50 !== null).length >= 10);
const v = computed<NdviSummary>(() => (usesHls.value ? hls.value! : modis.value));

const fmt = (x: number | null | undefined, d = 2) => (x === null || x === undefined ? '—' : x.toLocaleString(locale, { minimumFractionDigits: d, maximumFractionDigits: d }));
const dateBr = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' });

const threshold = computed(() => ({
    silent: true,
    symbol: 'none',
    lineStyle: { color: '#d97706', type: 'dashed', width: 1.5 },
    label: { formatter: 'pouco verde', position: 'insideStartTop', color: '#b45309', fontSize: 10 },
    data: [{ yAxis: v.value.thresholds.low_green }],
}));

// Ano típico: faixa P10–P90 (área empilhada) + mediana da referência; mediana do MODIS em segundo plano.
const climatology = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x === null || x === undefined ? '—' : x.toFixed(2)) },
    legend: usesHls.value ? { bottom: 0, textStyle: { fontSize: 10 }, data: ['HLS 30 m', 'MODIS 250 m'] } : undefined,
    grid: { left: 36, right: 12, top: 16, bottom: usesHls.value ? 46 : 28 },
    xAxis: { type: 'category', data: v.value.monthly.map((m) => m.name), boundaryGap: false },
    yAxis: { type: 'value', min: 0, max: 1, splitNumber: 4 },
    series: [
        { name: 'P10', type: 'line', stack: 'band', symbol: 'none', lineStyle: { opacity: 0 }, data: v.value.monthly.map((m) => m.p10), tooltip: { show: false } },
        {
            name: 'Faixa P10–P90', type: 'line', stack: 'band', symbol: 'none', lineStyle: { opacity: 0 },
            areaStyle: { color: 'rgba(132, 204, 22, 0.22)' },
            data: v.value.monthly.map((m) => (m.p10 === null || m.p90 === null ? null : +(m.p90 - m.p10).toFixed(3))),
            tooltip: { show: false },
        },
        {
            name: usesHls.value ? 'HLS 30 m' : t('NDVI mediano'), type: 'line', smooth: true, connectNulls: true, data: v.value.monthly.map((m) => m.p50),
            itemStyle: { color: '#15803d' }, lineStyle: { width: 3 }, markLine: threshold.value,
        },
        ...(usesHls.value
            ? [{ name: 'MODIS 250 m', type: 'line', smooth: true, symbol: 'none', data: modis.value.monthly.map((m) => m.p50), itemStyle: { color: '#a8a29e' }, lineStyle: { width: 1.5, type: 'dashed' } }]
            : []),
    ],
}));

function withGaps(series: { date: string; ndvi: number }[], maxGapDays: number) {
    // Quebra a linha onde faltam imagens: não desenhar dado que não existe.
    return series.flatMap((p, i, arr) => {
        const gap = i > 0 && (new Date(p.date).getTime() - new Date(arr[i - 1].date).getTime()) / 86_400_000 > maxGapDays;
        return gap ? [[p.date, null], [p.date, p.ndvi]] : [[p.date, p.ndvi]];
    });
}

const since = computed(() => {
    const d = new Date(modis.value.coverage.end);
    d.setFullYear(d.getFullYear() - (hls.value ? 2 : 3));
    return d;
});
const timeline = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x === null || x === undefined ? '—' : x.toFixed(2)) },
    legend: hls.value ? { bottom: 0, textStyle: { fontSize: 10 } } : undefined,
    grid: { left: 36, right: 12, top: 16, bottom: hls.value ? 46 : 28 },
    xAxis: { type: 'time', axisLabel: { formatter: '{MMM} {yy}', fontSize: 10 } },
    yAxis: { type: 'value', min: 0, max: 1, splitNumber: 4 },
    series: [
        {
            name: 'MODIS 250 m', type: 'line', smooth: true, showSymbol: false, connectNulls: false,
            data: withGaps(modis.value.series.filter((p) => new Date(p.date) >= since.value), 48),
            itemStyle: { color: hls.value ? '#a8a29e' : '#16a34a' },
            ...(hls.value ? { lineStyle: { width: 1.5, type: 'dashed' } } : { areaStyle: { color: 'rgba(22, 163, 74, 0.12)' } }),
            markLine: threshold.value,
        },
        ...(hls.value
            ? [{
                  name: 'HLS 30 m', type: 'line', showSymbol: true, symbolSize: 4, connectNulls: false,
                  data: withGaps(hls.value.series, 45), itemStyle: { color: '#15803d' }, lineStyle: { width: 2 },
              }]
            : []),
    ],
}));

const recentTone = computed(() => {
    const a = v.value.recent.anomaly;
    if (v.value.recent.below_p10) return 'text-red-600';
    if (a !== null && a < -0.05) return 'text-amber-600';
    return 'text-safra-700';
});
</script>

<template>
    <div class="card">
        <div class="card-head">
            <div>
                <h2><span class="h-icon"><Icon name="leaf" /></span> {{ $t('Cobertura verde do talhão') }}</h2>
                <p>
                    <Term k="ndvi" label="NDVI" /> {{ $t('do satélite ·') }}
                    <template v-if="usesHls"><Term k="hls" label="HLS" /> {{ $t('30 m (referência) +') }} <Term k="modis" label="MODIS" /> 250 m</template>
                    <template v-else><Term k="modis" label="MODIS" /> 250 m</template>
                </p>
            </div>
            <div class="flex flex-wrap gap-1.5 text-[11px] text-stone-500">
                <span v-if="hls" class="inline-flex items-center gap-1.5"><DatasetBadge code="HLS" /> {{ hls.coverage.valid }} {{ $t('imagens ·') }} {{ hls.coverage.start.slice(0, 4) }}–{{ hls.coverage.end.slice(0, 4) }}</span>
                <span class="inline-flex items-center gap-1.5"><DatasetBadge code="MODIS" /> {{ modis.coverage.valid }} {{ $t('imagens ·') }} {{ modis.coverage.start.slice(0, 4) }}–{{ modis.coverage.end.slice(0, 4) }}</span>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="metric">
                <p class="metric-label">{{ $t('Pico de verde') }}</p>
                <p class="metric-value">{{ fmt(v.peak?.ndvi) }}</p>
                <p class="metric-hint capitalize">{{ v.peak?.name ?? '—' }}</p>
            </div>
            <div class="metric">
                <p class="metric-label">{{ $t('Menor verde') }}</p>
                <p class="metric-value">{{ fmt(v.trough?.ndvi) }}</p>
                <p class="metric-hint capitalize">{{ v.trough?.name ?? '—' }}</p>
            </div>
            <div class="metric">
                <p class="metric-label">{{ $t('Meses com pouco verde') }}</p>
                <p class="metric-value">{{ v.low_green_months.length }}</p>
                <p class="metric-hint">{{ $t('NDVI mediano <') }} {{ fmt(v.thresholds.low_green) }}</p>
            </div>
            <div class="metric">
                <p class="metric-label">{{ $t('Imagem mais recente') }}</p>
                <p class="metric-value" :class="recentTone">{{ fmt(v.recent.ndvi) }}</p>
                <p class="metric-hint">
                    {{ dateBr(v.recent.date) }}<template v-if="v.recent.anomaly !== null"> · {{ v.recent.anomaly >= 0 ? '+' : '' }}{{ fmt(v.recent.anomaly) }} vs. normal</template>
                </p>
            </div>
        </div>

        <div class="mt-5 grid gap-5 lg:grid-cols-2">
            <div>
                <h3 class="text-sm font-semibold text-stone-800">{{ $t('Ano típico') }}</h3>
                <p class="text-xs text-stone-500">{{ $t('Linha: mediana do mês. Faixa: 8 em cada 10 imagens.') }}</p>
                <VChart :option="climatology" autoresize class="h-60" />
            </div>
            <div>
                <h3 class="text-sm font-semibold text-stone-800">{{ $t('Últimos') }} {{ hls ? 2 : 3 }} {{ $t('anos') }}</h3>
                <p class="text-xs text-stone-500">{{ hls ? $t('Pontos verdes: imagens de 30 m sem nuvem. Linha cinza: composições MODIS de 16 dias.') : $t('Cada ponto é uma composição de 16 dias (Terra e Aqua).') }}</p>
                <VChart :option="timeline" autoresize class="h-60" />
            </div>
        </div>

        <p class="mt-3 text-sm text-stone-600">
            {{ $t('NDVI perto de 0,8 indica lavoura fechada e verde; abaixo de') }} {{ fmt(v.thresholds.low_green) }}{{ $t(', solo exposto, palhada seca ou pasto seco. O satélite') }} <strong>{{ $t('não distingue palhada de solo nu') }}</strong> {{ $t('— confira no campo antes de concluir.') }}
        </p>
        <p class="mt-1 text-xs text-stone-500">{{ (usesHls ? [v.source_note, modis.source_note] : [v.source_note]).join(' ') }}</p>
    </div>
</template>
