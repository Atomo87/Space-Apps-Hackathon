<script setup lang="ts">
import { t } from '@/lib/i18n';
import { computed } from 'vue';
import { VChart } from '@/lib/echarts';
import type { Diagnosis } from '@/types/contract';

const props = defineProps<{ diagnosis: Diagnosis }>();
const months = computed(() => props.diagnosis.monthly.map((m) => m.name));

const water = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => (v === null ? '—' : `${Math.round(v)} mm`) },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: 40, right: 10, top: 20, bottom: 68 },
    xAxis: { type: 'category', data: months.value },
    yAxis: { type: 'value', name: t('mm/mês'), nameTextStyle: { fontSize: 10 } },
    series: [
        { name: t('Chuva (média)'), type: 'bar', data: props.diagnosis.monthly.map((m) => m.rain_mm.mean), itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] } },
        { name: t('Chuva em ano seco (P10)'), type: 'line', data: props.diagnosis.monthly.map((m) => m.rain_mm.p10), lineStyle: { type: 'dashed' }, itemStyle: { color: '#93c5fd' }, symbol: 'none' },
        { name: t('ETo (demanda do ar)'), type: 'line', data: props.diagnosis.monthly.map((m) => m.eto_mm), itemStyle: { color: '#ea580c' }, smooth: true },
    ],
}));

const temp = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => (v === null ? '—' : `${v.toFixed(1)} °C`) },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: 40, right: 10, top: 20, bottom: 68 },
    xAxis: { type: 'category', data: months.value },
    yAxis: { type: 'value', name: '°C', min: (v: { min: number }) => Math.floor(v.min - 2), nameTextStyle: { fontSize: 10 } },
    series: [
        { name: t('Máxima'), type: 'line', data: props.diagnosis.monthly.map((m) => m.tmax_c), itemStyle: { color: '#dc2626' }, smooth: true },
        { name: t('Média', 'ClimateCharts'), type: 'line', data: props.diagnosis.monthly.map((m) => m.tmean_c), itemStyle: { color: '#a8a29e' }, smooth: true, symbol: 'none' },
        { name: t('Mínima'), type: 'line', data: props.diagnosis.monthly.map((m) => m.tmin_c), itemStyle: { color: '#2563eb' }, smooth: true },
    ],
}));

const yearly = computed(() => ({
    tooltip: { trigger: 'axis' },
    grid: { left: 45, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: props.diagnosis.yearly.years },
    yAxis: [
        { type: 'value', name: 'mm/ano', nameTextStyle: { fontSize: 10 } },
        { type: 'value', name: '°C', min: 'dataMin', nameTextStyle: { fontSize: 10 } },
    ],
    series: [
        { name: t('Chuva anual'), type: 'bar', data: props.diagnosis.yearly.rain_mm, itemStyle: { color: '#60a5fa' } },
        { name: t('Máxima média anual'), type: 'line', yAxisIndex: 1, data: props.diagnosis.yearly.tmax_c, itemStyle: { color: '#dc2626' } },
    ],
}));

const hasSoilMoisture = computed(() => props.diagnosis.monthly.some((m) => m.soil_moisture_root !== null));
const soil = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (v: number) => (v === null ? '—' : v.toFixed(2)) },
    grid: { left: 40, right: 10, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: months.value },
    yAxis: { type: 'value', min: 0, max: 1 },
    series: [{ name: t('Umidade na zona das raízes'), type: 'line', areaStyle: { opacity: 0.2 }, data: props.diagnosis.monthly.map((m) => m.soil_moisture_root), itemStyle: { color: '#0d9488' }, smooth: true }],
}));
</script>

<template>
    <div class="grid gap-4 lg:grid-cols-2">
        <div class="card">
            <h3 class="text-[15px] font-bold tracking-tight text-stone-900">{{ $t('Chuva × demanda de água') }}</h3>
            <p class="mt-0.5 text-xs text-stone-500">{{ $t('Quando a linha laranja passa das barras, falta água.') }}</p>
            <VChart :option="water" autoresize class="mt-2 h-64" />
        </div>
        <div class="card">
            <h3 class="text-[15px] font-bold tracking-tight text-stone-900">{{ $t('Temperaturas médias do mês') }}</h3>
            <p class="mt-0.5 text-xs text-stone-500">{{ $t('Máxima, média e mínima do ar, em °C.') }}</p>
            <VChart :option="temp" autoresize class="mt-2 h-64" />
        </div>
        <div class="card">
            <h3 class="text-[15px] font-bold tracking-tight text-stone-900">{{ $t('Ano a ano') }}</h3>
            <p class="mt-0.5 text-xs text-stone-500">{{ $t('Chuva total e temperatura máxima média de cada ano.') }}</p>
            <VChart :option="yearly" autoresize class="mt-2 h-56" />
        </div>
        <div v-if="hasSoilMoisture" class="card">
            <h3 class="text-[15px] font-bold tracking-tight text-stone-900">{{ $t('Umidade do solo') }}</h3>
            <p class="mt-0.5 text-xs text-stone-500">{{ $t(diagnosis.source.dataset_code === 'DEMO' ? 'Dados climáticos ilustrativos · 0 = seco, 1 = saturado.' : 'Modelo NASA POWER/MERRA-2 · 0 = seco, 1 = saturado.') }}</p>
            <VChart :option="soil" autoresize class="mt-2 h-56" />
        </div>
    </div>
</template>
