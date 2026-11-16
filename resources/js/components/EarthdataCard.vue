<script setup lang="ts">
import { locale, t } from '@/lib/i18n';
import { computed } from 'vue';
import { VChart } from '@/lib/echarts';
import type { Earthdata } from '@/types/contract';
import DatasetBadge from './DatasetBadge.vue';
import Icon from './Icon.vue';
import Term from './Term.vue';

const props = defineProps<{ data: Earthdata; powerMonthly: (number | null)[] }>();
const smap = computed(() => props.data.smap);
const gpm = computed(() => props.data.gpm);
const eco = computed(() => props.data.ecostress);
const grace = computed(() => props.data.grace);

// O motivo técnico (ex.: termo de uso da conta) fica nas notas da API e no log; ao produtor basta saber o que faltou.
const missing = computed(() => (
    [['SMAP', smap.value], ['GPM', gpm.value], ['ECOSTRESS', eco.value], ['GRACE-FO', grace.value]] as const
).filter(([, v]) => !v).map(([n]) => n));

const fmt = (x: number | null | undefined, d = 1) => (x === null || x === undefined ? '—' : x.toLocaleString(locale, { minimumFractionDigits: d, maximumFractionDigits: d }));
const sign = (x: number) => (x > 0 ? '+' : '');
const TONE = { baixo: 'bg-safra-50 text-safra-800 ring-safra-200', moderado: 'bg-amber-50 text-amber-800 ring-amber-200', alto: 'bg-red-50 text-red-700 ring-red-200' };

const smapChart = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x == null ? '—' : `${x.toFixed(3)} m³/m³`) },
    grid: { left: 40, right: 10, top: 14, bottom: 26 },
    xAxis: { type: 'category', data: smap.value!.monthly.map((m) => m.name) },
    yAxis: { type: 'value', min: 0, splitNumber: 3 },
    series: [{
        name: 'Umidade (mediana)', type: 'bar', barWidth: '55%',
        data: smap.value!.monthly.map((m) => ({ value: m.p50, itemStyle: { color: m.level === 2 ? '#d97706' : m.level === 1 ? '#fbbf24' : '#0ea5e9' } })),
    }],
}));

const gpmChart = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x == null ? '—' : `${Math.round(x)} mm`) },
    legend: { bottom: 0 },
    grid: { left: 40, right: 10, top: 14, bottom: 44 },
    xAxis: { type: 'category', data: gpm.value!.monthly.map((m) => m.name) },
    yAxis: { type: 'value', name: 'mm' },
    series: [
        { name: t('GPM (satélite)'), type: 'bar', barWidth: '55%', data: gpm.value!.monthly.map((m) => m.mean_mm), itemStyle: { color: '#2563eb' } },
        { name: 'POWER (modelo)', type: 'line', smooth: true, data: props.powerMonthly, itemStyle: { color: '#0d9488' } },
    ],
}));

const graceChart = computed(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (x: number) => (x == null ? '—' : `${x.toFixed(1)} cm`) },
    grid: { left: 40, right: 10, top: 14, bottom: 26 },
    xAxis: { type: 'time', axisLabel: { formatter: '{yyyy}' } },
    yAxis: { type: 'value', name: 'cm' },
    series: [{
        name: t('Água armazenada'), type: 'line', showSymbol: false, smooth: true,
        data: grace.value!.series.map((p) => [p.date, p.cm]),
        itemStyle: { color: '#4f46e5' },
        areaStyle: { color: 'rgba(79, 70, 229, 0.10)', origin: 0 },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: '#a8a29e', type: 'dashed' }, label: { show: false }, data: [{ yAxis: 0 }] },
    }],
}));

const ecoChart = computed(() => ({
    tooltip: { trigger: 'item', formatter: (p: { value: [string, number] }) => `${p.value[0].slice(0, 10)}<br/>ESI ${p.value[1].toFixed(2)}` },
    grid: { left: 36, right: 10, top: 14, bottom: 26 },
    xAxis: { type: 'time', axisLabel: { formatter: '{MMM} {yy}', fontSize: 10 } },
    yAxis: { type: 'value', min: 0, max: 1, splitNumber: 4 },
    series: [{
        type: 'scatter', symbolSize: 8,
        data: eco.value!.observations.map((o) => ({ value: [o.datetime, o.esi], itemStyle: { color: o.esi < 0.3 ? '#dc2626' : o.esi < 0.6 ? '#f59e0b' : '#16a34a' } })),
        markLine: { silent: true, symbol: 'none', lineStyle: { color: '#dc2626', type: 'dashed' }, label: { formatter: 'estresse alto', position: 'insideStartTop', fontSize: 10, color: '#b91c1c' }, data: [{ yAxis: 0.3 }] },
    }],
}));
</script>

<template>
    <div class="card">
        <div class="card-head">
            <div>
                <h2><span class="h-icon"><Icon name="satellite" /></span> {{ $t('Água no solo, na chuva e no subsolo') }}</h2>
                <p>{{ $t('Missões da NASA com acesso por conta Earthdata: umidade do solo, chuva por satélite, estresse da planta e água armazenada.') }}</p>
            </div>
            <div class="flex flex-wrap gap-1.5">
                <DatasetBadge v-if="smap" code="SMAP" /><DatasetBadge v-if="gpm" code="GPM" /><DatasetBadge v-if="eco" code="ECOSTRESS" /><DatasetBadge v-if="grace" code="GRACE-FO" />
            </div>
        </div>

        <div class="grid gap-5 lg:grid-cols-2">
            <!-- SMAP -->
            <section v-if="smap" class="rounded-xl border border-stone-200/80 p-4">
                <div class="flex items-start justify-between gap-2">
                    <div>
                        <h3 class="text-sm font-bold text-stone-900"><Term k="smap" :label="$t('Umidade do solo')" /> · SMAP 9 km</h3>
                        <p class="text-xs text-stone-500">{{ $t('Mais seco em') }} <strong class="capitalize">{{ smap.driest }}</strong>{{ $t(', mais úmido em') }} <strong class="capitalize">{{ smap.wettest }}</strong>.</p>
                    </div>
                    <div class="text-right">
                        <p class="metric-label justify-end">{{ $t('Último mês') }}</p>
                        <p class="text-lg font-bold tabular-nums">{{ fmt(smap.recent.sm, 2) }}</p>
                        <p v-if="smap.recent.anomaly !== null" class="text-[11px] tabular-nums" :class="smap.recent.anomaly < 0 ? 'text-amber-700' : 'text-safra-700'">{{ sign(smap.recent.anomaly) }}{{ fmt(smap.recent.anomaly, 2) }} vs. normal</p>
                    </div>
                </div>
                <VChart :option="smapChart" autoresize class="mt-2 h-44" />
                <p class="text-[11px] text-stone-500">{{ $t('m³ de água por m³ de solo, mediana do mês (') }}{{ smap.coverage.valid }} {{ $t('passagens). Laranja: meses mais secos para este solo.') }}</p>
            </section>

            <!-- GPM -->
            <section v-if="gpm" class="rounded-xl border border-stone-200/80 p-4">
                <div class="flex items-start justify-between gap-2">
                    <div>
                        <h3 class="text-sm font-bold text-stone-900"><Term k="gpm" :label="$t('Chuva por satélite')" /> · GPM IMERG</h3>
                        <p class="text-xs text-stone-500">{{ gpm.coverage.start.slice(0, 4) }}–{{ gpm.coverage.end.slice(0, 4) }}{{ $t(', pixel de ~11 km.') }}</p>
                    </div>
                    <div class="text-right">
                        <p class="metric-label justify-end">{{ $t('Média anual') }}</p>
                        <p class="text-lg font-bold tabular-nums">{{ gpm.annual_mm }} mm</p>
                        <p v-if="gpm.vs_power_pct !== undefined" class="text-[11px] tabular-nums text-stone-500">{{ sign(gpm.vs_power_pct) }}{{ gpm.vs_power_pct }}% vs. POWER</p>
                    </div>
                </div>
                <VChart :option="gpmChart" autoresize class="mt-2 h-44" />
                <p class="text-[11px] text-stone-500">{{ $t('Últimos 12 meses:') }} {{ gpm.last12_mm }} mm<template v-if="gpm.last12_anomaly_pct !== null"> ({{ sign(gpm.last12_anomaly_pct) }}{{ gpm.last12_anomaly_pct }}{{ $t('% da média)') }}</template>.</p>
            </section>

            <!-- ECOSTRESS -->
            <section v-if="eco" class="rounded-xl border border-stone-200/80 p-4">
                <div class="flex items-start justify-between gap-2">
                    <div>
                        <h3 class="text-sm font-bold text-stone-900"><Term k="ecostress" :label="$t('Estresse da planta')" /> · ECOSTRESS 70 m</h3>
                        <p class="text-xs text-stone-500">{{ eco.observations.length }} {{ $t('passagens sem nuvem de') }} {{ eco.passes }} {{ $t('sobre o talhão.') }}</p>
                    </div>
                    <div class="text-right">
                        <p class="metric-label justify-end">{{ $t('ESI mediano') }}</p>
                        <p class="text-lg font-bold tabular-nums">{{ fmt(eco.median_esi, 2) }}</p>
                        <span class="badge mt-0.5 capitalize ring-1 ring-inset" :class="TONE[eco.stress]">{{ $t('estresse') }} {{ eco.stress }}</span>
                    </div>
                </div>
                <VChart :option="ecoChart" autoresize class="mt-2 h-44" />
                <p class="text-[11px] text-stone-500">{{ $t('1 = a planta evaporou tudo o que podia; abaixo de 0,3 = forte falta de água.') }} {{ eco.high_stress_pct }}{{ $t('% das passagens com estresse alto.') }}</p>
            </section>

            <!-- GRACE -->
            <section v-if="grace" class="rounded-xl border border-stone-200/80 p-4">
                <div class="flex items-start justify-between gap-2">
                    <div>
                        <h3 class="text-sm font-bold text-stone-900"><Term k="grace" :label="$t('Água armazenada na região')" /> · GRACE-FO</h3>
                        <p class="text-xs text-stone-500">{{ $t('Solo + aquífero + rios, blocos de ~300 km, desde') }} {{ grace.coverage.start.slice(0, 4) }}.</p>
                    </div>
                    <div class="text-right">
                        <p class="metric-label justify-end">{{ $t('Tendência') }}</p>
                        <p class="text-lg font-bold tabular-nums" :class="(grace.trend_cm_per_decade ?? 0) < 0 ? 'text-red-600' : 'text-safra-700'">
                            {{ grace.trend_cm_per_decade === null ? '—' : `${sign(grace.trend_cm_per_decade)}${fmt(grace.trend_cm_per_decade)} cm` }}
                        </p>
                        <p class="text-[11px] text-stone-500">{{ $t('por década') }}<template v-if="grace.trend_p_value !== null"> · p = {{ fmt(grace.trend_p_value, 2) }}</template></p>
                    </div>
                </div>
                <VChart :option="graceChart" autoresize class="mt-2 h-44" />
                <p class="text-[11px] text-stone-500">{{ $t('cm de lâmina d’água em relação a 2004–2009. Hoje:') }} {{ fmt(grace.latest.cm) }} {{ $t('cm; menor nível:') }} {{ grace.record_low.date.slice(0, 7) }} ({{ fmt(grace.record_low.cm) }} cm).</p>
            </section>
        </div>

        <p v-if="missing.length" class="mt-4 flex items-center gap-2 text-xs text-stone-500">
            <Icon name="info" class="h-3.5 w-3.5" /> {{ missing.join(', ') }} {{ $t('indisponível nesta análise.') }}
        </p>
    </div>
</template>
