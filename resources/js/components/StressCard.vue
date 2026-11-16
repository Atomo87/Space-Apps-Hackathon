<script setup lang="ts">
import { locale, t } from '@/lib/i18n';
import { computed } from 'vue';
import { VChart } from '@/lib/echarts';
import type { MonthlyClimate, Stress } from '@/types/contract';
import DatasetBadge from './DatasetBadge.vue';
import Icon from './Icon.vue';
import Term from './Term.vue';

const props = defineProps<{ stress: Stress; monthly: MonthlyClimate[] }>();
const lst = computed(() => props.stress.lst);
const et = computed(() => props.stress.et);

const fmt = (x: number | null | undefined, d = 1) => (x === null || x === undefined ? '—' : x.toLocaleString(locale, { minimumFractionDigits: d, maximumFractionDigits: d }));

const STRESS_TONE = { baixo: 'bg-safra-50 text-safra-800 ring-1 ring-safra-100', moderado: 'bg-amber-50 text-amber-800 ring-1 ring-amber-200', alto: 'bg-red-50 text-red-700 ring-1 ring-red-200' };

// Superfície (satélite, ~10h30) × máxima do ar (POWER): a diferença mostra solo exposto ou planta sem água.
const lstChart = computed(() => {
    const l = lst.value!;
    return {
        tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x === null || x === undefined ? '—' : `${x.toFixed(1)} °C`) },
        legend: { bottom: 0, textStyle: { fontSize: 10 } },
        grid: { left: 36, right: 12, top: 16, bottom: 46 },
        xAxis: { type: 'category', data: l.monthly.map((m) => m.name) },
        yAxis: { type: 'value', name: '°C', min: (v: { min: number }) => Math.floor(v.min - 3), nameTextStyle: { fontSize: 10 } },
        series: [
            {
                name: t('Superfície (mediana)'), type: 'bar', barWidth: '55%', itemStyle: { color: '#fb923c' },
                data: l.monthly.map((m) => ({
                    value: m.p50,
                    itemStyle: { color: m.level === 2 ? '#ef4444' : m.level === 1 ? '#f59e0b' : '#fdba74', borderRadius: [4, 4, 0, 0] },
                })),
                markLine: {
                    silent: true, symbol: 'none', lineStyle: { color: '#dc2626', type: 'dashed' },
                    label: { formatter: `${l.thresholds.warm_c} °C`, position: 'insideStartTop', color: '#b91c1c', fontSize: 10 },
                    data: [{ yAxis: l.thresholds.warm_c }],
                },
            },
            { name: t('Máxima do ar (POWER)'), type: 'line', smooth: true, data: props.monthly.map((m) => m.tmax_c), itemStyle: { color: '#2563eb' } },
        ],
    };
});

const etChart = computed(() => {
    const e = et.value!;
    return {
        tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x === null || x === undefined ? '—' : `${Math.round(x)} mm`) },
        legend: { bottom: 0, textStyle: { fontSize: 10 } },
        grid: { left: 44, right: 12, top: 16, bottom: 46 },
        xAxis: { type: 'category', data: e.yearly.map((y) => String(y.year)) },
        yAxis: { type: 'value', name: 'mm/ano', nameTextStyle: { fontSize: 10 } },
        series: [
            { name: 'Potencial (PET)', type: 'bar', data: e.yearly.map((y) => y.pet_mm), itemStyle: { color: '#fed7aa', borderRadius: [4, 4, 0, 0] } },
            { name: 'Real (ET)', type: 'bar', data: e.yearly.map((y) => y.et_mm), itemStyle: { color: '#0d9488', borderRadius: [4, 4, 0, 0] } },
        ],
    };
});
</script>

<template>
    <div class="card">
        <div class="card-head">
            <div>
                <h2><span class="h-icon"><Icon name="thermometer" /></span> {{ $t('Calor e água vistos do satélite') }}</h2>
                <p><Term k="lst" :label="$t('Temperatura da superfície')" /> {{ $t('e') }} <Term k="et_pet" :label="$t('evapotranspiração real × potencial')" />.</p>
            </div>
            <div class="flex flex-wrap gap-1.5">
                <DatasetBadge v-if="lst" code="MODIS LST" />
                <DatasetBadge v-if="et" code="MODIS ET" />
            </div>
        </div>

        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="metric">
                <p class="metric-label">{{ $t('Superfície mais quente') }}</p>
                <p class="metric-value">{{ lst?.hottest ? `${fmt(lst.hottest.p50)} °C` : '—' }}</p>
                <p class="metric-hint capitalize">{{ lst?.hottest?.name ?? $t('sem dado') }}</p>
            </div>
            <div class="metric">
                <p class="metric-label">{{ $t('Meses acima de') }} {{ lst?.thresholds.warm_c ?? 35 }} °C</p>
                <p class="metric-value">{{ lst ? lst.hot_months.length : '—' }}</p>
                <p class="metric-hint">{{ $t('na mediana, por volta das 10h30') }}</p>
            </div>
            <div class="metric">
                <p class="metric-label">{{ $t('Água evaporada') }}</p>
                <p class="metric-value">{{ et ? `${et.et_mm} mm` : '—' }}</p>
                <p class="metric-hint">{{ et ? `de ${et.pet_mm} mm possíveis por ano` : $t('sem dado') }}</p>
            </div>
            <div class="metric">
                <p class="metric-label">{{ $t('Estresse hídrico') }}</p>
                <p class="mt-1.5"><span v-if="et" class="badge text-[13px] capitalize" :class="STRESS_TONE[et.stress]">{{ et.stress }}</span><span v-else class="metric-value">—</span></p>
                <p class="metric-hint">{{ et ? `ET/PET = ${Math.round(et.ratio * 100)}%` : '' }}</p>
            </div>
        </div>

        <div class="mt-5 grid gap-5 lg:grid-cols-2">
            <div v-if="lst">
                <h3 class="text-sm font-semibold text-stone-800">{{ $t('Superfície × ar, mês a mês') }}</h3>
                <p class="text-xs text-stone-500">{{ $t('Barras bem acima da linha azul: chão exposto ou planta sem água para transpirar.') }}</p>
                <VChart :option="lstChart" autoresize class="h-60" />
            </div>
            <div v-if="et">
                <h3 class="text-sm font-semibold text-stone-800">{{ $t('Evapotranspiração por ano') }}</h3>
                <p class="text-xs text-stone-500">{{ $t('Quanto menor a barra verde perto da laranja, maior a falta de água. Ano mais seco:') }} {{ et.driest_year.year }}.</p>
                <VChart :option="etChart" autoresize class="h-60" />
            </div>
        </div>

        <p class="mt-3 text-xs text-stone-500">
            {{ [lst?.source_note, et?.source_note, $t('Indicadores observados, de apoio: entram no diagnóstico e nas evidências, não na nota das estratégias.')].filter(Boolean).join(' ') }}
        </p>
        <p v-for="n in stress.notes" :key="n" class="mt-1 text-xs text-amber-700">{{ n }}</p>
    </div>
</template>
