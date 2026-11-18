<script setup lang="ts">
import { countryName, t, locale, tf } from '@/lib/i18n';
import { Head, Link, router, usePage } from '@inertiajs/vue3';
import { url } from '@/lib/url';
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import ConfidenceBadge from '@/components/ConfidenceBadge.vue';
import DatasetBadge from '@/components/DatasetBadge.vue';
import DemoPicker, { type DemoRegion } from '@/components/DemoPicker.vue';
import EarthdataCard from '@/components/EarthdataCard.vue';
import Icon from '@/components/Icon.vue';
import StarRating from '@/components/StarRating.vue';
import StrategyCard from '@/components/StrategyCard.vue';
import Term from '@/components/Term.vue';
import StressCard from '@/components/StressCard.vue';
import VegetationCard from '@/components/VegetationCard.vue';
import VulnerabilityCalendar from '@/components/VulnerabilityCalendar.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { api, ApiError } from '@/lib/api';
import { confirmAction } from '@/lib/confirm';
import { fmt, PRIORITIES, monthName } from '@/lib/labels';
import type { AnalysisResponse, FieldStatus, Fires, Priorities } from '@/types/contract';
import type { Polygon } from 'geojson';
import CropMonitorCard from '@/components/CropMonitorCard.vue';
import PlantingCard from '@/components/PlantingCard.vue';
import type { SharedProps } from '@/types/global';

interface FieldProps {
    id: number;
    name: string;
    latitude: number;
    longitude: number;
    area_ha: number | null;
    irrigated: boolean;
    status: FieldStatus['status'];
    status_message: string | null;
    is_demo: boolean;
    is_public_demo: boolean;
    demo_region: string | null;
    farm: { id: number; name: string; municipality: string | null; state: string | null; country_code: string };
    soil_source: string;
    history: { crop: string; sown_at: string; harvested_at: string }[];
    priorities: Priorities;
    power_period: { start_year: number | null; end_year: number | null; first_year: number; last_year: number; min_years: number };
    boundary: Polygon | null;
}
const props = defineProps<{ field: FieldProps; can: { update: boolean; delete: boolean }; demoRegions: DemoRegion[] }>();
const fixedDemo = computed(() => props.field.demo_region === 'texas');
const page = usePage<SharedProps>();
// Gráficos carregados depois do resumo (conexão fraca — RNF08).
const ClimateCharts = defineAsyncComponent(() => import('@/components/ClimateCharts.vue'));
const CriteriaRadar = defineAsyncComponent(() => import('@/components/CriteriaRadar.vue'));
const FieldImagery = defineAsyncComponent(() => import('@/components/FieldImagery.vue'));
const AssistantModal = defineAsyncComponent(() => import('@/components/AssistantModal.vue'));
const askOpen = ref(false);

// Focos de queimada (NASA FIRMS): carregados à parte, depois da análise.
const fires = ref<Fires | null>(null);
const firesLoading = ref(false);
async function loadFires() {
    if (props.field.is_public_demo || fires.value || firesLoading.value) return;
    firesLoading.value = true;
    try {
        fires.value = await api<Fires>(`/api/v1/fields/${props.field.id}/fires`);
    } catch {
        fires.value = null;
    } finally {
        firesLoading.value = false;
    }
}

type Tab = 'diag' | 'compare' | 'whatif';
const tab = ref<Tab>('diag');
const status = ref<FieldStatus['status']>(props.field.status);
const statusMsg = ref<string | null>(props.field.status_message);
const elapsed = ref(0);
let timer: ReturnType<typeof setInterval> | undefined;

const data = ref<AnalysisResponse | null>(null);
const baseline = ref<AnalysisResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const priorities = ref<Priorities>({ ...props.field.priorities });
const prioritiesDirty = ref(false);
const savingPriorities = ref(false);

const rain = ref(0);
const temp = ref(0);
let debounce: ReturnType<typeof setTimeout> | undefined;

const progressText = computed(() => {
    if (elapsed.value < 8) return t('Conectando ao serviço de dados…');
    if (elapsed.value < 70) return t('Calculando evapotranspiração (FAO-56), veranicos, geada e chuvas extremas…');
    if (elapsed.value < 110) return t('Medindo a declividade (SRTM) e lendo o NDVI dos satélites (MODIS 250 m e HLS 30 m)…');
    if (elapsed.value < 150) return t('Medindo o calor da superfície e a evapotranspiração (MODIS)…');
    if (elapsed.value < 240) return t('Lendo umidade do solo (SMAP), estresse da planta (ECOSTRESS) e água no subsolo (GRACE-FO)…');
    return t('Quase lá. Na primeira vez o servidor pode demorar a “acordar”.');
});

/** Progresso gravado no servidor (etapa atual). Sem ele, uma estimativa pelo tempo. */
const progress = ref<number | null>(null);

/** Aplica o estado do servidor: tempo real desde o início e etapa atual (não recomeça ao voltar à página). */
function applyStatus(s: FieldStatus) {
    status.value = s.status;
    statusMsg.value = s.message;
    if (typeof s.elapsed_s === 'number') elapsed.value = s.elapsed_s;
    progress.value = s.progress ?? null;
}

function startTimer() {
    clearInterval(timer);
    timer = setInterval(() => elapsed.value++, 1000);
}

async function process(force = false) {
    status.value = 'processing';
    error.value = null;
    startTimer();
    try {
        const s = await api<FieldStatus>(`/api/v1/fields/${props.field.id}/process${force ? '?force=1' : ''}`, { method: 'POST' });
        applyStatus(s);
        if (s.status === 'processing' || s.status === 'pending') setTimeout(poll, 4000);
        if (s.status === 'ready') await load();
    } catch (e) {
        status.value = 'error';
        statusMsg.value = (e as Error).message;
    } finally {
        if (status.value !== 'processing') clearInterval(timer);
    }
}

async function poll() {
    const s = await api<FieldStatus>(`/api/v1/fields/${props.field.id}/status`).catch(() => null);
    if (!s) return setTimeout(poll, 5000);
    applyStatus(s);
    if (s.status === 'processing' || s.status === 'pending') setTimeout(poll, 4000);
    else {
        clearInterval(timer);
        if (s.status === 'ready') await load();
    }
}

async function load() {
    loading.value = true;
    error.value = null;
    try {
        const q = new URLSearchParams({ rain_delta_pct: String(rain.value), temp_delta_c: String(temp.value) });
        // Quem não pode gravar (ex.: visitante no exemplo) simula com os pesos da tela, sem salvar.
        if (!props.can.update) for (const [k, v] of Object.entries(priorities.value)) q.set(`priorities[${k}]`, String(v));
        const r = await api<AnalysisResponse>(`/api/v1/fields/${props.field.id}/analysis?${q}`);
        data.value = r;
        if (rain.value === 0 && temp.value === 0) baseline.value = r;
        loadFires();
    } catch (e) {
        // Dados sendo atualizados no servidor (em segundo plano): acompanha o andamento em vez de mostrar erro.
        const fs = e instanceof ApiError ? (e.body as { field_status?: FieldStatus['status'] } | null)?.field_status : undefined;
        if (e instanceof ApiError && e.status === 409 && (fs === 'processing' || fs === 'pending')) {
            status.value = 'processing';
            statusMsg.value = e.message;
            startTimer();
            poll();
            return;
        }
        error.value = e instanceof ApiError ? e.message : t('Não foi possível carregar a análise.');
    } finally {
        loading.value = false;
    }
}

async function savePriorities() {
    if (props.can.update) {
        const ok = await confirmAction({
            title: t('Salvar estas prioridades?'),
            message: t('Elas passam a valer para todos os talhões desta fazenda, e o ranking das estratégias é recalculado.'),
            confirmText: t('Salvar prioridades'),
            icon: 'star',
        });
        if (!ok) return;
    }
    savingPriorities.value = true;
    try {
        if (props.can.update) await api(`/api/v1/farms/${props.field.farm.id}/priorities`, { method: 'PUT', body: JSON.stringify(priorities.value) });
        prioritiesDirty.value = false;
        await load();
    } catch (e) {
        error.value = (e as Error).message;
    } finally {
        savingPriorities.value = false;
    }
}

watch(priorities, () => (prioritiesDirty.value = true), { deep: true });
watch([rain, temp], () => {
    clearTimeout(debounce);
    debounce = setTimeout(load, 350);
});

const best = computed(() => {
    const alts = data.value?.strategies.filter((s) => !s.is_current) ?? [];
    return alts.reduce<string | null>((acc, s) => (!acc || s.score > (alts.find((a) => a.key === acc)?.score ?? -1) ? s.key : acc), null);
});

const scenarioRows = computed(() => {
    if (!data.value || !baseline.value) return [];
    return data.value.strategies.map((s) => {
        const b = baseline.value!.strategies.find((x) => x.key === s.key);
        const water = s.criteria.find((c) => c.key === 'save_water')?.score ?? 0;
        const waterB = b?.criteria.find((c) => c.key === 'save_water')?.score ?? water;
        return { label: s.label, title: s.title, score: s.score, base: b?.score ?? null, water, waterB, risk: s.criteria.find((c) => c.key === 'climate_risk')?.score ?? 0 };
    });
});

// Resumo executivo do topo: o que o produtor precisa saber antes de ler o resto.
const kpis = computed(() => {
    const d = data.value;
    if (!d) return null;
    const current = d.strategies.find((s) => s.is_current) ?? null;
    const top = d.strategies.find((s) => s.key === best.value) ?? null;
    const risky = (['heat', 'frost', 'drought', 'heavy_rain'] as const);
    const highMonths = d.diagnosis.calendar.filter((c) => risky.some((k) => c[k] === 2)).map((c) => monthName(c.month));
    const deficitMonths = d.diagnosis.monthly.filter((m) => (m.water_balance_mm ?? 0) < -20).length;
    return {
        current,
        top,
        delta: top && current ? top.score - current.score : null,
        highMonths,
        et: d.diagnosis.stress?.et ?? null,
        deficitMonths,
        datasets: d.sources.filter((s) => s.code !== 'CATALOGO').length,
    };
});

const TABS = [
    { k: 'diag', l: t('Diagnóstico'), s: t('Diagnóstico'), i: 'calendar' },
    { k: 'compare', l: t('Comparar estratégias'), s: t('Comparar'), i: 'scale' },
    { k: 'whatif', l: t('E se o clima mudar?'), s: t('E se…?'), i: 'sliders' },] as const;

const visibleTabs = computed(() => TABS.filter((entry) => !fixedDemo.value || entry.k !== 'whatif'));

const reliefTone = computed(() => {
    const s = data.value?.diagnosis.terrain?.slope_pct.mean ?? 0;
    return s < 3 ? 'bg-safra-100 text-safra-800' : s < 8 ? 'bg-lime-100 text-lime-800' : s < 20 ? 'bg-amber-100 text-amber-900' : 'bg-red-100 text-red-800';
});

function printReport() {
    tab.value = 'compare';
    setTimeout(() => window.print(), 300);
}

// ---- Período do clima (NASA POWER) ----
const pp = reactive({ ...props.field.power_period });
const periodOpen = ref(false);
const periodSaving = ref(false);
const periodError = ref<string | null>(null);
/** Período efetivamente usado na análise (o que o geo-service devolveu); antes disso, o salvo no talhão. */
const usedPeriod = computed(() => {
    const p = data.value?.diagnosis.source.period;
    if (p) return { start: Number(p.start.slice(0, 4)), end: Number(p.end.slice(0, 4)), years: p.years };
    if (pp.start_year && pp.end_year) return { start: pp.start_year, end: pp.end_year, years: pp.end_year - pp.start_year + 1 };
    return null;
});
const startSel = ref<number>(pp.start_year ?? usedPeriod.value?.start ?? pp.last_year - 19);
const endSel = ref<number>(pp.end_year ?? usedPeriod.value?.end ?? pp.last_year);
const yearOptions = Array.from({ length: pp.last_year - pp.first_year + 1 }, (_, i) => pp.last_year - i);
const periodYears = computed(() => endSel.value - startSel.value + 1);
const periodValid = computed(() => periodYears.value >= pp.min_years);
const PRESETS = [
    { label: t('Últimos 10 anos'), years: 10 },
    { label: t('Últimos 20 anos'), years: 20 },
    { label: t('Últimos 30 anos'), years: 30 },
];

function openPeriod() {
    if (usedPeriod.value) {
        startSel.value = usedPeriod.value.start;
        endSel.value = usedPeriod.value.end;
    }
    periodError.value = null;
    periodOpen.value = true;
}

function preset(years: number) {
    endSel.value = pp.last_year;
    startSel.value = pp.last_year - years + 1;
}

async function applyPeriod(useDefault = false) {
    if (!useDefault && !periodValid.value) return;
    const label = useDefault ? t('o período padrão') : `${startSel.value}–${endSel.value} (${periodYears.value} anos)`;
    const ok = await confirmAction({
        title: tf('Recalcular com {period}?', { period: label }),
        message: t('O GeoSafra vai consultar o NASA POWER de novo para este período e refazer o diagnóstico, o calendário e as notas. Pode levar de 1 a 3 minutos.'),
        confirmText: t('Recalcular análise'),
        icon: 'calendar',
    });
    if (!ok) return;
    periodSaving.value = true;
    periodError.value = null;
    try {
        const body = useDefault ? { start_year: null, end_year: null } : { start_year: startSel.value, end_year: endSel.value };
        const r = await api<{ changed: boolean }>(`/api/v1/fields/${props.field.id}/period`, { method: 'PUT', body: JSON.stringify(body) });
        pp.start_year = body.start_year;
        pp.end_year = body.end_year;
        periodOpen.value = false;
        data.value = null;
        baseline.value = null;
        await process(!r.changed);
    } catch (e) {
        periodError.value = (e as Error).message;
    } finally {
        periodSaving.value = false;
    }
}

async function destroy() {
    const ok = await confirmAction({
        title: tf('Excluir “{field}”?', { field: props.field.name }),
        message: t('O talhão, o histórico de safras e todas as análises dele serão apagados de vez. Esta ação não pode ser desfeita.'),
        confirmText: t('Excluir talhão'),
        tone: 'danger',
        icon: 'trash',
    });
    if (ok) router.delete(url(`/talhoes/${props.field.id}`));
}

onMounted(() => {
    if (status.value === 'ready') load();
    else if (status.value === 'processing') {
        // Voltou à página no meio do processamento: retoma o acompanhamento com o andamento do servidor.
        startTimer();
        poll();
    } else if (status.value === 'pending') process();
});
onBeforeUnmount(() => {
    clearInterval(timer);
    clearTimeout(debounce);
});
</script>

<template>
    <Head :title="field.name" />
    <AppLayout :title="field.name" back="/" wide :show-warning="status === 'ready'">
        <!-- CABEÇALHO DO TALHÃO -->
        <header class="mb-5">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div class="flex min-w-0 items-start gap-4">
                    <span class="hidden h-12 w-12 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-safra-700 to-safra-950 text-lime-300 shadow-[0_8px_20px_-8px_rgb(5_46_22/0.6)] sm:grid"><Icon name="sprout" class="h-6 w-6" /></span>
                    <div class="min-w-0">
                        <p class="text-[13px] font-medium text-stone-500">
                            {{ field.farm.name }}<template v-if="field.farm.municipality"> · {{ [field.farm.municipality, field.farm.state, field.farm.country_code !== 'BR' ? countryName(field.farm.country_code) : null].filter(Boolean).join(', ') }}</template>
                        </p>
                        <div class="mt-0.5 flex flex-wrap items-center gap-2">
                            <h1 class="text-2xl font-extrabold tracking-tight text-stone-900 sm:text-[1.75rem]">{{ field.name }}</h1>
                            <span v-if="field.is_demo" class="badge bg-amber-100 text-amber-800 ring-1 ring-amber-200 ring-inset">{{ $t('exemplo') }}</span>
                            <span v-if="status === 'ready'" class="badge bg-safra-50 text-safra-800 ring-1 ring-safra-200 ring-inset"><span class="h-1.5 w-1.5 rounded-full bg-safra-600" /> {{ $t('análise pronta') }}</span>
                        </div>
                        <dl class="mt-2.5 flex flex-wrap gap-x-5 gap-y-1.5 text-[13px] text-stone-600">
                            <div v-if="field.area_ha" class="flex items-center gap-1.5"><dt class="sr-only">{{ $t('Área') }}</dt><Icon name="grid" class="h-3.5 w-3.5 text-stone-400" /><dd class="font-medium">{{ fmt(field.area_ha, 1) }} ha</dd></div>
                            <div class="flex items-center gap-1.5"><dt class="sr-only">{{ $t('Coordenadas') }}</dt><Icon name="target" class="h-3.5 w-3.5 text-stone-400" /><dd class="tabular-nums">{{ field.latitude.toFixed(4) }}, {{ field.longitude.toFixed(4) }}</dd></div>
                            <div class="flex items-center gap-1.5"><dt class="sr-only">{{ $t('Solo') }}</dt><Icon name="layers" class="h-3.5 w-3.5 text-stone-400" /><dd>{{ $t('Solo') }} {{ { lab_analysis: $t('por análise de laboratório'), farmer_estimate: $t('estimado pelo produtor'), unknown: $t('a confirmar') }[field.soil_source] }}</dd></div>
                            <div class="flex items-center gap-1.5"><dt class="sr-only">{{ $t('Histórico') }}</dt><Icon name="sprout" class="h-3.5 w-3.5 text-stone-400" /><dd class="capitalize">{{ field.history.map((h) => $t(h.crop)).join(' → ') || $t('sem histórico') }}</dd></div>
                            <div class="flex items-center gap-1.5">
                                <dt class="sr-only">{{ $t('Período do clima') }}</dt><Icon name="calendar" class="h-3.5 w-3.5 text-stone-400" />
                                <dd>
                                    {{ $t(field.is_public_demo ? 'Dados climáticos ilustrativos' : 'Clima NASA POWER') }}
                                    <span v-if="usedPeriod" class="font-medium tabular-nums">{{ usedPeriod.start }}–{{ usedPeriod.end }}</span>
                                    <span v-else>{{ $t('período padrão') }}</span>
                                    <button v-if="can.update && status !== 'processing'" type="button" class="ml-1 font-semibold text-safra-700 underline-offset-2 hover:underline print:hidden" :aria-expanded="periodOpen" aria-controls="period-panel" @click="periodOpen ? (periodOpen = false) : openPeriod()">{{ $t('alterar') }}</button>
                                </dd>
                            </div>
                        </dl>
                    </div>
                </div>
                <div class="flex shrink-0 flex-wrap gap-2 print:hidden">
                    <Link v-if="can.update" :href="$url(`/talhoes/${field.id}/editar`)" class="btn-secondary btn-sm"><Icon name="edit" /> {{ $t('Editar') }}</Link>
                    <button type="button" class="btn-secondary btn-sm" :disabled="!data" @click="printReport"><Icon name="printer" /> {{ $t('Relatório') }}</button>
                    <button v-if="can.delete" type="button" class="btn-danger btn-sm" :aria-label="$t('Excluir talhão')" @click="destroy"><Icon name="trash" /><span class="hidden sm:inline">{{ $t('Excluir') }}</span></button>
                </div>
            </div>
        </header>

        <!-- PERÍODO DO NASA POWER -->
        <section v-if="periodOpen && can.update" id="period-panel" class="card mb-6 p-5 print:hidden" aria-labelledby="period-title">
            <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 id="period-title" class="font-bold text-stone-900">{{ $t('Período do clima na análise') }}</h2>
                    <p class="mt-1 max-w-2xl text-sm text-stone-600">
                        {{ $t('Escolha os anos do NASA POWER usados no diagnóstico, no calendário de riscos e nas notas. Períodos curtos mostram o clima recente; longos dão estatísticas mais estáveis. Mínimo de') }} {{ pp.min_years }} {{ $t('anos.') }}
                    </p>
                </div>
                <button type="button" class="btn-ghost btn-sm" :aria-label="$t('Fechar')" @click="periodOpen = false"><Icon name="x" /></button>
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
                <button v-for="p in PRESETS" :key="p.years" type="button" class="rounded-full px-3 py-1.5 text-sm font-semibold ring-1 ring-inset transition" :class="startSel === pp.last_year - p.years + 1 && endSel === pp.last_year ? 'bg-safra-700 text-white ring-safra-700' : 'bg-white text-stone-700 ring-stone-300 hover:bg-stone-50'" @click="preset(p.years)">{{ p.label }}</button>
            </div>
            <div class="mt-4 flex flex-wrap items-end gap-3">
                <label class="block">
                    <span class="mb-1 block text-xs font-semibold text-stone-600">{{ $t('De') }}</span>
                    <select v-model.number="startSel" class="input w-28 tabular-nums"><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option></select>
                </label>
                <label class="block">
                    <span class="mb-1 block text-xs font-semibold text-stone-600">{{ $t('Até') }}</span>
                    <select v-model.number="endSel" class="input w-28 tabular-nums"><option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option></select>
                </label>
                <p class="pb-2 text-sm tabular-nums" :class="periodValid ? 'text-stone-600' : 'font-semibold text-red-700'" aria-live="polite">
                    {{ periodYears > 0 ? `${periodYears} anos` : $t('Período inválido') }}<template v-if="!periodValid && periodYears > 0"> {{ $t('· mínimo de') }} {{ pp.min_years }}</template>
                </p>
            </div>
            <p v-if="periodError" class="field-error mt-3">{{ periodError }}</p>
            <div class="mt-5 flex flex-wrap gap-2">
                <button type="button" class="btn-primary" :disabled="!periodValid || periodSaving" @click="applyPeriod()"><Icon name="refresh" /> {{ periodSaving ? $t('Salvando…') : $t('Recalcular com este período') }}</button>
                <button v-if="pp.start_year" type="button" class="btn-secondary" :disabled="periodSaving" @click="applyPeriod(true)">{{ $t('Voltar ao padrão') }}</button>
            </div>
        </section>

        <div v-if="!can.update" class="notice-warn mb-6 flex-wrap items-center justify-between print:hidden">
            <div class="flex w-full items-start gap-3"><Icon name="eye" class="mt-0.5 h-5 w-5 shrink-0" /><span>{{ $t('Este é o') }} <strong>{{ $t('exemplo público') }}</strong> {{ $t(fixedDemo ? 'do Texas, com clima e histórico de safras ilustrativos e cenário fixo.' : 'de referência: não pode ser editado nem excluído. Mude prioridades e cenários à vontade: nada é gravado.') }} <template v-if="field.is_public_demo && !fixedDemo">{{ $t('Os dados climáticos deste exemplo são ilustrativos.') }}</template></span></div>
            <DemoPicker v-if="field.is_public_demo" :regions="demoRegions" :current="field.demo_region" />
            <Link :href="$url('/talhoes/novo')" class="btn-primary btn-sm"><Icon name="plus" /> {{ $t('Analisar o meu talhão') }}</Link>
        </div>

        <!-- PROCESSAMENTO -->
        <div v-if="status === 'processing' || status === 'pending'" class="card flex flex-col items-center gap-4 px-6 py-14 text-center" role="status" aria-live="polite">
            <div class="relative grid h-16 w-16 place-items-center">
                <span class="absolute inset-0 animate-spin rounded-full border-4 border-safra-100 border-t-safra-700" />
                <Icon name="satellite" class="h-6 w-6 text-safra-700" />
            </div>
            <div>
                <p class="text-lg font-bold tracking-tight">{{ statusMsg ? $t(statusMsg) : progressText }}</p>
                <p class="mt-1 text-sm text-stone-500 tabular-nums">{{ elapsed >= 60 ? `${Math.floor(elapsed / 60)} min ${elapsed % 60} s` : `${elapsed} s` }} {{ $t('desde o início') }}</p>
            </div>
            <div class="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-stone-100"><div class="h-full rounded-full bg-gradient-to-r from-safra-600 to-lime-400 transition-[width] duration-1000" :style="{ width: `${progress ?? Math.min(95, elapsed * 1.1)}%` }" /></div>
            <p v-if="progress !== null" class="-mt-2 text-xs font-semibold text-stone-500 tabular-nums">{{ progress }}{{ $t('% concluído') }}</p>
            <p class="flex max-w-md items-start gap-2 rounded-xl bg-safra-50 px-4 py-3 text-left text-sm text-safra-900">
                <Icon name="info" class="mt-0.5 h-4 w-4 shrink-0" />
                <span>{{ $t('O processamento roda') }} <strong>{{ $t('em segundo plano') }}</strong> {{ $t('no servidor. Pode sair desta tela ou fechar o navegador: quando voltar, a análise estará pronta.') }}</span>
            </p>
            <Link :href="$url('/')" class="btn-secondary btn-sm"><Icon name="arrowLeft" /> {{ $t('Voltar aos meus talhões') }}</Link>
        </div>
        <div v-else-if="status === 'error'" class="card flex flex-col items-start gap-4 border-red-200 sm:flex-row sm:items-center" role="alert">
            <span class="icon-tile-bad"><Icon name="alert" /></span>
            <div class="flex-1">
                <p class="font-bold">{{ $t('Não conseguimos buscar os dados da NASA agora.') }}</p>
                <p class="text-sm text-stone-600">{{ statusMsg ? $t(statusMsg) : '' }}</p>
            </div>
            <button type="button" class="btn-primary" @click="process(true)"><Icon name="refresh" /> {{ $t('Tentar de novo') }}</button>
        </div>

        <template v-else>
            <div class="sticky top-[64px] z-20 -mx-4 mb-6 bg-stone-50/90 px-4 backdrop-blur-md sm:-mx-6 sm:px-6 print:hidden">
                <nav class="tabs" role="tablist" :aria-label="$t('Seções da análise')">
                    <button v-for="t in visibleTabs" :key="t.k" type="button" role="tab" class="tab" :aria-selected="tab === t.k" @click="tab = t.k">
                        <Icon :name="t.i" /> <span class="sm:hidden">{{ t.s }}</span><span class="hidden sm:inline">{{ t.l }}</span>
                    </button>
                    <button
                        type="button"
                        class="my-1.5 ml-auto inline-flex shrink-0 items-center gap-1.5 self-center rounded-full bg-gradient-to-r from-safra-700 to-safra-900 px-3.5 py-1.5 text-sm font-semibold whitespace-nowrap text-white shadow-[0_4px_14px_-4px_rgb(21_128_61/0.6)] transition hover:-translate-y-px"
                        aria-haspopup="dialog"
                        :aria-expanded="askOpen"
                        :disabled="!data"
                        @click="askOpen = true"
                    >
                        <Icon name="message" class="h-4 w-4 text-lime-300" /> <span class="sm:hidden">{{ $t('IA') }}</span><span class="hidden sm:inline">{{ $t('Pergunte à IA') }}</span>
                    </button>
                </nav>
            </div>

            <!-- RESUMO EXECUTIVO -->
            <section v-if="kpis" class="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4" :aria-label="$t('Resumo')">
                <div class="kpi">
                    <span class="kpi-icon bg-safra-50 text-safra-700 ring-safra-200"><Icon name="target" /></span>
                    <div class="min-w-0">
                        <p class="metric-label">{{ $t('Alternativa mais forte') }}</p>
                        <p v-if="kpis.top" class="mt-1 truncate text-[15px] font-bold text-stone-900" :title="$t(kpis.top.title)">{{ kpis.top.label }} · {{ $t(kpis.top.title) }}</p>
                        <p v-else class="mt-1 text-[15px] font-bold text-stone-900">—</p>
                        <p class="metric-hint">
                            <template v-if="kpis.top">{{ $t('Nota') }} {{ kpis.top.score }}<template v-if="kpis.delta !== null"> · <span :class="kpis.delta >= 0 ? 'font-semibold text-safra-700' : 'font-semibold text-red-600'">{{ kpis.delta >= 0 ? '+' : '' }}{{ kpis.delta }}</span> {{ $t('vs. atual') }}</template></template>
                        </p>
                    </div>
                </div>
                <div class="kpi">
                    <span class="kpi-icon bg-red-50 text-red-600 ring-red-200"><Icon name="alert" /></span>
                    <div class="min-w-0">
                        <p class="metric-label">{{ $t('Meses de risco alto') }}</p>
                        <p class="mt-1 text-[15px] font-bold text-stone-900">{{ kpis.highMonths.length }} <span class="font-medium text-stone-500">{{ $t('de 12') }}</span></p>
                        <p class="metric-hint truncate capitalize">{{ kpis.highMonths.join(', ') || $t('nenhum mês crítico') }}</p>
                    </div>
                </div>
                <div class="kpi">
                    <span class="kpi-icon bg-sky-50 text-sky-700 ring-sky-200"><Icon name="droplet" /></span>
                    <div class="min-w-0">
                        <p class="metric-label">{{ $t('Água') }}</p>
                        <template v-if="kpis.et">
                            <p class="mt-1 text-[15px] font-bold text-stone-900 capitalize">{{ $t('Estresse') }} {{ kpis.et.stress }}</p>
                            <p class="metric-hint">{{ $t('Evaporou') }} {{ Math.round(kpis.et.ratio * 100) }}{{ $t('% do potencial (satélite)') }}</p>
                        </template>
                        <template v-else>
                            <p class="mt-1 text-[15px] font-bold text-stone-900">{{ kpis.deficitMonths }} {{ $t('meses com déficit') }}</p>
                            <p class="metric-hint">{{ $t('chuva abaixo da evapotranspiração') }}</p>
                        </template>
                    </div>
                </div>
                <div class="kpi">
                    <span class="kpi-icon bg-violet-50 text-violet-700 ring-violet-200"><Icon name="shield" /></span>
                    <div class="min-w-0">
                        <p class="metric-label">{{ $t('Confiança') }}</p>
                        <p class="mt-1 text-[15px] font-bold text-stone-900">{{ { alta: $t('Alta'), media: $t('Média', 'Show'), baixa: $t('Baixa') }[data!.diagnosis.confidence.level] }} · {{ Math.round(data!.diagnosis.confidence.value * 100) }}%</p>
                        <p class="metric-hint">{{ kpis.datasets }} {{ $t('conjuntos de dados da NASA') }}</p>
                    </div>
                </div>
            </section>

            <div v-if="error" class="notice-error mb-5" role="alert">
                <Icon name="alert" />
                <p class="flex-1">{{ error }}</p>
                <button type="button" class="font-semibold underline" @click="load">{{ $t('Tentar de novo') }}</button>
            </div>
            <div v-if="loading && !data" class="space-y-4" aria-busy="true" :aria-label="$t('Carregando análise')">
                <div class="card h-56 animate-pulse bg-stone-100/60" />
                <div class="grid gap-4 sm:grid-cols-4"><div v-for="n in 4" :key="n" class="card h-28 animate-pulse bg-stone-100/60" /></div>
            </div>

            <template v-if="data">
                <div v-for="w in data.warnings" :key="w" class="notice-warn mb-4"><Icon name="alert" /><p>{{ w }}</p></div>

                <!-- DIAGNÓSTICO -->
                <section v-show="tab === 'diag'" class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                    <div class="min-w-0 space-y-5">
                        <h2 class="section-kicker">{{ $t('Agora no talhão') }}</h2>
                        <CropMonitorCard v-if="!field.is_public_demo" :vegetation="data.diagnosis.vegetation" :earthdata="data.diagnosis.earthdata" :fires="fires" :fires-loading="firesLoading" />
                        <FieldImagery :latitude="field.latitude" :longitude="field.longitude" :boundary="field.boundary" :vegetation="data.diagnosis.vegetation" :fires="fires" />

                        <template v-if="data.planting">
                            <h2 class="section-kicker">{{ $t('Quando plantar') }}</h2>
                            <PlantingCard :planting="data.planting" :illustrative="field.is_public_demo" :texas-demo="fixedDemo" />
                        </template>

                        <h2 class="section-kicker">{{ $t('Riscos ao longo do ano') }}</h2>
                        <div class="card">
                            <div class="card-head">
                                <div>
                                    <h2><span class="h-icon"><Icon name="calendar" /></span> {{ $t('Calendário de vulnerabilidade') }}</h2>
                                    <p>{{ $t(field.is_public_demo ? 'Clima ilustrativo e histórico de safras do exemplo, mês a mês.' : 'Clima de 20 anos (NASA POWER), seu histórico de safras e o que os satélites observam, mês a mês.') }}</p>
                                </div>
                                <ConfidenceBadge :level="data.diagnosis.confidence.level" :value="data.diagnosis.confidence.value" />
                            </div>
                            <VulnerabilityCalendar :calendar="data.diagnosis.calendar" />
                        </div>

                        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            <div class="metric">
                                <p class="metric-label"><Icon name="sun" class="h-3.5 w-3.5 text-amber-600" /> <Term k="veranico" /></p>
                                <p class="metric-value">{{ fmt(data.diagnosis.season.pct_seasons_dry_spell_ge_10) }}%</p>
                                <p class="metric-hint">{{ $t('das safras com ≥ 10 dias secos') }}</p>
                            </div>
                            <div class="metric">
                                <p class="metric-label"><Icon name="rain" class="h-3.5 w-3.5 text-blue-600" /> <Term k="chuva_extrema" /></p>
                                <p class="metric-value">{{ fmt(data.diagnosis.extremes.annual_max_1day_mm_mean) }} mm</p>
                                <p class="metric-hint">{{ $t('maior chuva do ano (média)') }}</p>
                            </div>
                            <div class="metric">
                                <p class="metric-label"><Icon name="thermometer" class="h-3.5 w-3.5 text-red-600" /> <Term k="tendencia" :label="$t('Tendência da máxima')" /></p>
                                <p class="metric-value">{{ data.diagnosis.trends.tmax_c.per_decade === null ? '—' : `${data.diagnosis.trends.tmax_c.per_decade > 0 ? '+' : ''}${fmt(data.diagnosis.trends.tmax_c.per_decade, 1)} °C` }}</p>
                                <p class="metric-hint">{{ $t('por década (p =') }} {{ fmt(data.diagnosis.trends.tmax_c.p_value, 2) }})</p>
                            </div>
                            <div class="metric">
                                <p class="metric-label"><Icon name="chart" class="h-3.5 w-3.5 text-safra-700" /> {{ $t('Últimos 3 anos') }}</p>
                                <p class="metric-value">{{ data.diagnosis.recent.rain_anomaly_pct === null ? '—' : `${data.diagnosis.recent.rain_anomaly_pct > 0 ? '+' : ''}${fmt(data.diagnosis.recent.rain_anomaly_pct)}%` }}</p>
                                <p class="metric-hint">{{ $t('de chuva em relação à média') }}</p>
                            </div>
                        </div>

                        <h2 class="section-kicker">{{ $t('Observações de satélite') }}</h2>
                        <div v-if="data.diagnosis.terrain" class="card">
                            <div class="card-head">
                                <div>
                                    <h2><span class="h-icon"><Icon name="mountain" /></span> {{ $t('Relevo do talhão') }}</h2>
                                    <p><Term k="declividade" /> {{ $t('e fator de erosão pela elevação do SRTM (30 m).') }}</p>
                                </div>
                                <span class="badge capitalize" :class="reliefTone">{{ $t(data.diagnosis.terrain.relief_class) }}</span>
                            </div>
                            <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
                                <div class="metric"><p class="metric-label">{{ $t('Declividade média') }}</p><p class="metric-value">{{ fmt(data.diagnosis.terrain.slope_pct.mean, 1) }}%</p></div>
                                <div class="metric"><p class="metric-label">{{ $t('10% mais íngremes') }}</p><p class="metric-value">≥ {{ fmt(data.diagnosis.terrain.slope_pct.p90, 1) }}%</p></div>
                                <div class="metric"><p class="metric-label">{{ $t('Altitude') }}</p><p class="metric-value">{{ data.diagnosis.terrain.elevation_m.min }}–{{ data.diagnosis.terrain.elevation_m.max }} m</p></div>
                                <div class="metric"><p class="metric-label"><Term k="erosao" :label="$t('Fator LS')" /></p><p class="metric-value">{{ fmt(data.diagnosis.terrain.ls_factor, 2) }}</p></div>
                            </div>
                            <p class="mt-4 text-sm text-stone-600">
                                {{ data.diagnosis.terrain.ls_relative > 1.05 ? $t('O relevo aumenta') : data.diagnosis.terrain.ls_relative < 0.95 ? $t('O relevo reduz') : $t('O relevo mantém') }}
                                {{ $t('o risco de erosão em relação a um terreno suave (3%) — por isso a cobertura do solo nos meses chuvosos pesa') }} {{ data.diagnosis.terrain.ls_relative > 1.05 ? $t('mais') : $t('menos') }} {{ $t('na nota de erosão.') }}
                            </p>
                            <p class="mt-1 text-xs text-stone-500">{{ data.diagnosis.terrain.source_note }} {{ $t('Comprimento de rampa assumido:') }} {{ data.diagnosis.terrain.slope_length_assumed_m }} m.</p>
                        </div>

                        <VegetationCard v-if="data.diagnosis.vegetation" :vegetation="data.diagnosis.vegetation" />

                        <StressCard v-if="data.diagnosis.stress" :stress="data.diagnosis.stress" :monthly="data.diagnosis.monthly" />

                        <EarthdataCard v-if="data.diagnosis.earthdata" :data="data.diagnosis.earthdata" :power-monthly="data.diagnosis.monthly.map((m) => m.rain_mm.mean)" />

                        <h2 class="section-kicker">{{ $t(field.is_public_demo ? 'Dados climáticos ilustrativos' : 'Clima histórico · NASA POWER') }}</h2>
                        <ClimateCharts :diagnosis="data.diagnosis" />

                        <details class="card text-sm">
                            <summary><span class="flex items-center gap-2.5"><Icon name="database" class="h-[18px] w-[18px] text-safra-700" /> {{ $t('Detalhes da série climática') }}</span></summary>
                            <ul class="mt-3 space-y-1.5 border-t border-stone-100 pt-3 text-stone-700">
                                <li><strong>{{ data.diagnosis.source.dataset }}</strong> · API {{ data.diagnosis.source.api_version ?? '—' }} {{ $t('· comunidade AG · horário solar local') }}</li>
                                <li>{{ $t('Período:') }} {{ data.diagnosis.source.period.start }} {{ $t('a') }} {{ data.diagnosis.source.period.end }} ({{ data.diagnosis.source.period.years }} {{ $t('anos)') }}</li>
                                <li><Term k="resolucao" />: {{ data.diagnosis.source.grid_note }}</li>
                                <li>{{ $t('Variáveis:') }} <span v-for="(p, code) in data.diagnosis.source.parameters" :key="code" class="mr-2 inline-block">{{ code }} ({{ p.units }})</span></li>
                                <li v-for="n in data.diagnosis.confidence.notes" :key="n">• {{ n }}</li>
                            </ul>
                        </details>
                    </div>

                    <!-- Coluna lateral: achados e fontes (vem primeiro no celular) -->
                    <aside class="order-first space-y-5 xl:sticky xl:top-[124px] xl:order-none xl:max-h-[calc(100vh-140px)] xl:self-start xl:overflow-y-auto xl:pb-2">
                        <div class="card !p-0">
                            <div class="flex items-center gap-2.5 border-b border-stone-100 px-5 py-4">
                                <span class="h-icon"><Icon name="info" /></span>
                                <div>
                                    <h2 class="text-[15px] font-bold tracking-tight text-stone-900">{{ $t('Principais achados') }}</h2>
                                    <p class="text-xs text-stone-500">{{ $t('Cada frase vem de um dado, com fonte e período.') }}</p>
                                </div>
                            </div>
                            <ol class="divide-y divide-stone-100">
                                <li v-for="(h, i) in data.diagnosis.highlights" :key="h.key" class="flex gap-3 px-5 py-3.5">
                                    <span class="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-stone-100 text-[10px] font-bold text-stone-600 tabular-nums">{{ i + 1 }}</span>
                                    <div class="min-w-0">
                                        <p class="text-[13.5px] leading-relaxed text-stone-700">{{ h.text }}</p>
                                        <p class="mt-1.5 flex flex-wrap items-center gap-1">
                                            <DatasetBadge v-for="d in h.datasets" :key="d" :code="d" />
                                            <span class="text-[11px] text-stone-400 tabular-nums">{{ h.period }}</span>
                                        </p>
                                    </div>
                                </li>
                            </ol>
                        </div>

                        <div v-if="data.diagnosis.current_crop_vulnerable.length" class="notice-error">
                            <Icon name="alert" />
                            <div>
                                <p class="font-bold">{{ $t('Quando a sua lavoura fica mais exposta') }}</p>
                                <p v-for="v in data.diagnosis.current_crop_vulnerable" :key="v.month" class="mt-1"><strong class="capitalize">{{ monthName(v.month) }}</strong> ({{ v.crops.map((crop) => $t(crop)).join(' + ') }}): {{ v.risks.map((risk) => $t(risk)).join('; ') }}</p>
                            </div>
                        </div>

                        <div class="card !p-0">
                            <div class="flex items-center gap-2.5 border-b border-stone-100 px-5 py-4">
                                <span class="h-icon"><Icon name="database" /></span>
                                <h2 class="text-[15px] font-bold tracking-tight text-stone-900">{{ $t('Dados usados') }}</h2>
                            </div>
                            <ul class="divide-y divide-stone-100">
                                <li v-for="s in data.sources" :key="s.code" class="px-5 py-3">
                                    <div class="flex items-center justify-between gap-2">
                                        <DatasetBadge :code="s.code === 'CATALOGO' ? $t('Catálogo') : s.code" />
                                        <span v-if="s.period" class="text-[11px] text-stone-400 tabular-nums">{{ s.period }}</span>
                                    </div>
                                    <p class="mt-1 text-[12.5px] font-medium text-stone-700">{{ s.name }}</p>
                                    <p v-if="s.resolution" class="text-[11.5px] text-stone-500">{{ s.resolution }}</p>
                                </li>
                            </ul>
                        </div>
                    </aside>
                </section>

                <!-- COMPARAR -->
                <section v-show="tab === 'compare'" class="space-y-5">
                    <div class="notice-info"><Icon name="info" /><p>{{ data.disclaimer }}</p></div>

                    <details v-if="!fixedDemo" class="card print:hidden" :open="prioritiesDirty">
                        <summary><span class="flex items-center gap-2.5"><Icon name="star" class="h-[18px] w-[18px] text-amber-500" /> {{ $t('Suas prioridades') }} <span class="hidden font-normal text-stone-500 sm:inline">{{ $t('— mude e veja a comparação mudar') }}</span></span></summary>
                        <div class="mt-4 grid gap-x-8 gap-y-1 border-t border-stone-100 pt-4 sm:grid-cols-2">
                            <div v-for="p in PRIORITIES" :key="p.key" class="flex items-center justify-between gap-2 py-1.5">
                                <span class="flex items-center gap-2 text-sm font-medium text-stone-700"><Icon :name="p.icon" class="h-4 w-4 text-safra-700" /> {{ p.label }}</span>
                                <StarRating v-model="priorities[p.key]" :label="p.label" />
                            </div>
                        </div>
                        <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <p class="text-xs text-stone-500">{{ $t('Segurança climática entra sempre com peso 3 (não ajustável).') }}</p>
                            <button type="button" class="btn-primary" :disabled="!prioritiesDirty || savingPriorities" @click="savePriorities">
                                <Icon name="refresh" /> {{ savingPriorities ? $t('Recalculando…') : can.update ? $t('Salvar e recalcular') : $t('Recalcular comparação') }}
                            </button>
                        </div>
                    </details>

                    <div class="grid gap-5 lg:grid-cols-2" :class="loading ? 'opacity-60 transition-opacity' : ''">
                        <StrategyCard v-for="s in data.strategies" :key="s.key" :strategy="s" :field-id="field.id" :best="s.key === best" />
                    </div>

                    <div class="card">
                        <div class="card-head">
                            <div>
                                <h2><span class="h-icon"><Icon name="target" /></span> {{ $t('Visão geral dos critérios') }}</h2>
                                <p>{{ $t('Notas de 0 a 100 de cada estratégia nos 10 critérios.') }}</p>
                            </div>
                        </div>
                        <CriteriaRadar :strategies="data.strategies" />
                    </div>

                    <details v-if="data.discarded.length" class="card text-sm">
                        <summary><span class="flex items-center gap-2.5"><Icon name="x" class="h-[18px] w-[18px] text-red-500" /> {{ $t('Opções descartadas e por quê (') }}{{ data.discarded.length }})</span></summary>
                        <ul class="mt-3 space-y-3 border-t border-stone-100 pt-3">
                            <li v-for="d in data.discarded" :key="d.key"><strong class="text-stone-900">{{ $t(d.title) }}</strong><br /><span class="text-stone-600">{{ d.reasons.join(' ') }}</span></li>
                        </ul>
                    </details>

                    <div class="notice-warn">
                        <Icon name="user" />
                        <div>
                            <p class="font-bold">{{ $t('Onde o seu julgamento é essencial') }}</p>
                            <ul class="mt-1.5 space-y-1">
                                <li v-for="h in data.human_judgment" :key="h">{{ h }}</li>
                            </ul>
                        </div>
                    </div>
                </section>

                <!-- E SE -->
                <AssistantModal v-if="data" :field-id="field.id" :open="askOpen" @close="askOpen = false" />

                <section v-if="!fixedDemo" v-show="tab === 'whatif'" class="space-y-5">
                    <div class="card space-y-6">
                        <div class="card-head !mb-0">
                            <div>
                                <h2><span class="h-icon"><Icon name="sliders" /></span> <Term k="cenario" :label="$t('E se o clima mudar?')" /></h2>
                                <p>{{ $t('Ajuste chuva e temperatura sobre o clima histórico e veja as notas mudarem.') }}</p>
                            </div>
                        </div>
                        <div class="grid gap-6 md:grid-cols-2">
                            <label class="block rounded-2xl bg-stone-50 p-4">
                                <span class="flex items-center justify-between text-sm font-semibold text-stone-700"><span class="flex items-center gap-2"><Icon name="droplet" class="h-4 w-4 text-sky-600" /> {{ $t('Chuva') }}</span><span class="badge bg-white text-base tabular-nums shadow-[var(--shadow-soft)]">{{ rain > 0 ? '+' : '' }}{{ rain }}%</span></span>
                                <input v-model.number="rain" type="range" min="-40" max="20" step="5" class="mt-4 w-full accent-safra-700" />
                                <span class="mt-1 flex justify-between text-xs text-stone-400"><span>−40%</span><span>+20%</span></span>
                            </label>
                            <label class="block rounded-2xl bg-stone-50 p-4">
                                <span class="flex items-center justify-between text-sm font-semibold text-stone-700"><span class="flex items-center gap-2"><Icon name="thermometer" class="h-4 w-4 text-orange-600" /> {{ $t('Temperatura') }}</span><span class="badge bg-white text-base tabular-nums shadow-[var(--shadow-soft)]">+{{ temp.toLocaleString(locale) }} °C</span></span>
                                <input v-model.number="temp" type="range" min="0" max="3" step="0.5" class="mt-4 w-full accent-safra-700" />
                                <span class="mt-1 flex justify-between text-xs text-stone-400"><span>+0 °C</span><span>+3 °C</span></span>
                            </label>
                        </div>
                        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <p v-if="data.diagnosis.scenario" class="text-xs text-stone-500">{{ data.diagnosis.scenario.notes.join(' ') }}</p>
                            <button type="button" class="btn-secondary btn-sm shrink-0" @click="() => { rain = 0; temp = 0; }"><Icon name="refresh" /> {{ $t('Voltar ao clima histórico') }}</button>
                        </div>
                    </div>

                    <div class="card overflow-x-auto !p-0" :class="loading ? 'opacity-60' : ''">
                        <table class="w-full text-sm">
                            <thead class="bg-stone-50 text-left text-xs tracking-wide text-stone-500 uppercase">
                                <tr class="[&>th]:px-4 [&>th]:py-3"><th>{{ $t('Opção') }}</th><th>{{ $t('Nota') }}</th><th>Δ</th><th><span class="inline-flex items-center gap-1"><Icon name="droplet" class="h-3.5 w-3.5" /> {{ $t('Água') }}</span></th><th><span class="inline-flex items-center gap-1"><Icon name="shield" class="h-3.5 w-3.5" /> {{ $t('Clima') }}</span></th></tr>
                            </thead>
                            <tbody>
                                <tr v-for="r in scenarioRows" :key="r.label" class="border-t border-stone-100 [&>td]:px-4 [&>td]:py-3">
                                    <td><span class="mr-2 inline-grid h-7 w-7 place-items-center rounded-lg bg-stone-100 text-xs font-black">{{ r.label }}</span><span class="text-stone-700">{{ $t(r.title) }}</span></td>
                                    <td class="text-base font-black tabular-nums">{{ r.score }}</td>
                                    <td class="font-semibold tabular-nums" :class="r.base !== null && r.score < r.base ? 'text-red-600' : 'text-safra-700'">{{ r.base === null ? '—' : r.score - r.base === 0 ? '=' : `${r.score - r.base > 0 ? '+' : ''}${r.score - r.base}` }}</td>
                                    <td class="tabular-nums">{{ r.water }} <span class="text-xs text-stone-400">({{ r.waterB }})</span></td>
                                    <td class="tabular-nums">{{ r.risk }}</td>
                                </tr>
                            </tbody>
                        </table>
                        <p class="border-t border-stone-100 px-4 py-3 text-xs text-stone-500">{{ $t('Δ = mudança da nota em relação ao clima histórico. Água = nota de uso de água (entre parênteses, no clima histórico). Clima = segurança climática.') }}</p>
                    </div>
                    <div class="card"><VulnerabilityCalendar :calendar="data.diagnosis.calendar" /></div>
                </section>

                <div class="mt-8 space-y-1 border-t border-stone-200 pt-5 text-xs text-stone-500">
                    <p class="font-semibold text-stone-600">{{ $t('Motor') }} {{ data.engine_version }} {{ $t('· catálogo') }} {{ data.catalog_version }}</p>
                    <p v-for="s in data.sources" :key="s.code"><strong>{{ s.name }}</strong><template v-if="s.citation">: {{ s.citation }}</template></p>
                </div>
            </template>
        </template>
    </AppLayout>
</template>

<style>
@media print {
    .print\:hidden { display: none !important; }
    .card { box-shadow: none; break-inside: avoid; }
}
</style>
