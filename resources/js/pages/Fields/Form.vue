<script setup lang="ts">
import { countryName, locale, t, tf } from '@/lib/i18n';
import { Head, useForm } from '@inertiajs/vue3';
import { url } from '@/lib/url';
import type { Polygon } from 'geojson';
import { computed, defineAsyncComponent, nextTick, ref } from 'vue';
import Icon, { type IconName } from '@/components/Icon.vue';
import type { MapLocation, PickedField } from '@/components/MapPicker.vue';
import MunicipalityPicker from '@/components/MunicipalityPicker.vue';
import type { Municipality } from '@/lib/municipalities';
import StarRating from '@/components/StarRating.vue';
import Term from '@/components/Term.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { confirmAction } from '@/lib/confirm';
import { PRIORITIES } from '@/lib/labels';
import type { Priorities } from '@/types/contract';

interface CropOption {
    slug: string;
    name: string;
    category: string;
    family: string;
}
interface HistoryRow {
    crop: string;
    sown_at: string;
    harvested_at: string;
}
interface Initial {
    id: number;
    farm: { name: string; municipality: string | null; state: string | null; country_code: string; has_livestock: boolean };
    field: { name: string; latitude: number; longitude: number; boundary: Polygon | null; area_ha: number | null; irrigated: boolean; irrigation_mm_day: number | null };
    soil: Record<string, string | number | null>;
    history: HistoryRow[];
    priorities: Priorities;
    constraints: { excluded_crops: string[]; buyer_crops: string[]; no_buyer_crops: string[]; missing_equipment: string[] };
}

const MapPicker = defineAsyncComponent(() => import('@/components/MapPicker.vue'));

const props = defineProps<{ crops: CropOption[]; equipment: { key: string; label: string }[]; initial: Initial | null }>();

const editing = !!props.initial;
const defaults: Priorities = { save_water: 3, soil_structure: 3, n_fixation: 3, erosion_control: 3, organic_matter: 3, pest_break: 3, forage: 3, extra_income: 3, market_fit: 3 };

const form = useForm({
    farm: {
        name: props.initial?.farm.name ?? '',
        municipality: props.initial?.farm.municipality ?? '',
        state: props.initial ? props.initial.farm.state : 'MG',
        country_code: props.initial?.farm.country_code ?? 'BR',
        has_livestock: props.initial?.farm.has_livestock ?? false,
    },
    field: {
        name: props.initial?.field.name ?? t('Talhão 1'),
        latitude: (props.initial?.field.latitude ?? null) as number | null,
        longitude: (props.initial?.field.longitude ?? null) as number | null,
        boundary: (props.initial?.field.boundary ?? null) as Polygon | null,
        area_ha: (props.initial?.field.area_ha ?? null) as number | null,
        irrigated: props.initial?.field.irrigated ?? false,
        irrigation_mm_day: (props.initial?.field.irrigation_mm_day ?? null) as number | null,
    },
    soil: {
        source: 'unknown',
        texture: null,
        clay_pct: null,
        ph_water: null,
        organic_matter_pct: null,
        p_mg_dm3: null,
        k_cmolc_dm3: null,
        ctc_cmolc_dm3: null,
        v_pct: null,
        sampled_at: null,
        ...(props.initial?.soil ?? {}),
    } as Record<string, string | number | null>,
    history: (props.initial?.history ?? []) as HistoryRow[],
    priorities: { ...defaults, ...(props.initial?.priorities ?? {}) } as Priorities,
    constraints: props.initial?.constraints ?? { excluded_crops: [] as string[], buyer_crops: [] as string[], no_buyer_crops: [] as string[], missing_equipment: [] as string[] },
});

const steps: { title: string; lead: string; icon: IconName; prefixes: string[] }[] = [
    { title: t('Onde fica'), lead: t('Dê um nome e marque o talhão no mapa. Desenhar o contorno melhora a área e o relevo.'), icon: 'pin', prefixes: ['farm.', 'field.name', 'field.latitude', 'field.longitude', 'field.boundary', 'field.area_ha'] },
    { title: t('Solo e água'), lead: t('Dados de solo e irrigação aumentam a confiança da análise.'), icon: 'droplet', prefixes: ['soil.', 'field.irrigated', 'field.irrigation_mm_day'] },
    { title: t('O que você planta'), lead: t('O histórico do último ano mostra a sua rotação atual e os períodos de solo descoberto.'), icon: 'sprout', prefixes: ['history'] },
    { title: t('O que importa'), lead: t('As estrelas viram os pesos da comparação. Você pode mudar depois.'), icon: 'heart', prefixes: ['priorities.'] },
    { title: t('Restrições'), lead: t('O que não dá para fazer na sua propriedade — o motor descarta essas opções.'), icon: 'shield', prefixes: ['constraints.'] },
];
const step = ref(0);
const stepHeading = ref<HTMLHeadingElement | null>(null);
const municipalityText = ref(form.farm.municipality);
const cityCenter = ref<MapLocation | null>(null);

const picked = computed<PickedField>({
    get: () => ({ latitude: form.field.latitude, longitude: form.field.longitude, boundary: form.field.boundary, area_ha: form.field.area_ha }),
    set: (v) => {
        form.field.latitude = v.latitude;
        form.field.longitude = v.longitude;
        form.field.boundary = v.boundary;
        form.field.area_ha = v.area_ha;
    },
});

const cashCrops = computed(() => props.crops.filter((c) => ['grain', 'legume', 'fiber'].includes(c.category)));

async function selectMunicipality(city: Municipality) {
    if (form.field.boundary) {
        const confirmed = await confirmAction({
            title: t('Mudar a localização do talhão?'),
            message: t('O mapa irá para o centro da cidade escolhida. O contorno atual e a área calculada serão removidos.'),
            confirmText: t('Mudar localização'),
            icon: 'pin',
        });
        if (!confirmed) {
            municipalityText.value = form.farm.municipality;
            return;
        }
        form.field.boundary = null;
        form.field.area_ha = null;
    }

    municipalityText.value = city.name;
    form.farm.municipality = city.name;
    form.farm.state = city.stateCode ?? city.state;
    form.farm.country_code = city.countryCode;
    form.field.latitude = city.latitude;
    form.field.longitude = city.longitude;
    cityCenter.value = { latitude: city.latitude, longitude: city.longitude };
}

function stepErrors(i: number): string[] {
    return Object.entries(form.errors)
        .filter(([k]) => steps[i].prefixes.some((p) => k.startsWith(p)))
        .map(([, v]) => v as string);
}

// Diz exatamente o que falta para o botão "Continuar" liberar (botão apagado sem motivo parece defeito).
const missingStep0 = computed(() => {
    if (step.value !== 0) return '';
    const miss = [
        !form.farm.name && t('o nome da fazenda'),
        !form.field.name && t('o nome do talhão'),
        form.field.latitude === null && t('o local no mapa'),
    ].filter(Boolean) as string[];
    if (!miss.length) return '';
    return tf('Para continuar, falta {fields}.', { fields: new Intl.ListFormat(locale).format(miss) });
});

function canAdvance(): boolean {
    if (step.value === 0) return !!form.farm.name && !!form.field.name && form.field.latitude !== null;
    return true;
}

async function goToStep(index: number) {
    if (index > step.value && !canAdvance()) return;
    step.value = index;
    await nextTick();
    stepHeading.value?.scrollIntoView({ block: 'start' });
    stepHeading.value?.focus({ preventScroll: true });
}

function addHistory(crop = 'soja', sown = '', harvested = '') {
    form.history.push({ crop, sown_at: sown, harvested_at: harvested });
}

function quickFill() {
    const y = new Date().getMonth() >= 7 ? new Date().getFullYear() : new Date().getFullYear() - 1;
    form.history = [
        { crop: 'soja', sown_at: `${y - 1}-10-25`, harvested_at: `${y}-02-20` },
        { crop: 'milho', sown_at: `${y}-02-28`, harvested_at: `${y}-07-05` },
    ];
}

function toggle(list: string[], slug: string) {
    const i = list.indexOf(slug);
    if (i >= 0) list.splice(i, 1);
    else list.push(slug);
}

function market(slug: string): 'buyer' | 'none' | 'unknown' {
    if (form.constraints.buyer_crops.includes(slug)) return 'buyer';
    if (form.constraints.no_buyer_crops.includes(slug)) return 'none';
    return 'unknown';
}

function setMarket(slug: string, v: 'buyer' | 'none' | 'unknown') {
    form.constraints.buyer_crops = form.constraints.buyer_crops.filter((s) => s !== slug);
    form.constraints.no_buyer_crops = form.constraints.no_buyer_crops.filter((s) => s !== slug);
    if (v === 'buyer') form.constraints.buyer_crops.push(slug);
    if (v === 'none') form.constraints.no_buyer_crops.push(slug);
}

async function removeHistory(i: number) {
    const ok = await confirmAction({ title: t('Remover esta safra do histórico?'), message: t('O histórico ajuda a avaliar a rotação atual. Você pode adicionar a safra de novo depois.'), confirmText: t('Remover safra'), tone: 'danger', icon: 'trash' });
    if (ok) form.history.splice(i, 1);
}

async function submit() {
    if (editing) {
        const ok = await confirmAction({ title: t('Salvar as alterações do talhão?'), message: t('As estratégias passam a considerar as informações novas.'), confirmText: t('Salvar alterações'), icon: 'check' });
        if (!ok) return;
    }
    form.farm.municipality = municipalityText.value;
    const opts = {
        preserveScroll: true,
        onError: () => {
            const first = steps.findIndex((_, i) => stepErrors(i).length);
            if (first >= 0) void goToStep(first);
        },
    };
    if (editing) form.put(url(`/talhoes/${props.initial!.id}`), opts);
    else form.post(url('/talhoes'), opts);
}
</script>

<template>
    <Head :title="editing ? $t('Editar talhão') : $t('Novo talhão')" />
    <AppLayout :title="editing ? $t('Editar talhão') : $t('Novo talhão')" :back="editing ? `/talhoes/${initial!.id}` : '/'">
        <div class="mx-auto max-w-5xl">
        <div class="mb-5 rounded-2xl border border-[#e0e8da] bg-[#edf2e7] p-4 sm:p-6">
            <p class="text-sm font-semibold text-safra-700">{{ editing ? $t('Editar talhão') : $t('Novo talhão') }} {{ $t('· etapa') }} {{ step + 1 }} {{ $t('de') }} {{ steps.length }}</p>
            <h1 ref="stepHeading" tabindex="-1" class="mt-1 scroll-mt-24 text-2xl font-extrabold tracking-tight text-[#142b21] focus:outline-none sm:text-3xl">{{ steps[step].title }}</h1>
            <p class="mt-1.5 text-[15px] text-stone-600">{{ steps[step].lead }}</p>
        </div>

        <!-- progresso -->
        <ol class="mb-5 grid grid-cols-5 gap-1.5 sm:gap-2" :aria-label="$t('Etapas')">
            <li v-for="(s, i) in steps" :key="s.title" class="min-w-0">
                <button
                    type="button"
                    class="group flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-stone-200 bg-white p-1 text-left transition hover:border-safra-600 sm:p-1.5 lg:justify-start"
                    :class="i === step ? 'border-safra-600 bg-safra-50' : ''"
                    :aria-current="i === step ? 'step' : undefined"
                    :aria-label="tf('Etapa {step}: {title}', { step: i + 1, title: s.title })"
                    :disabled="i > step && !canAdvance()"
                    @click="goToStep(i)"
                >
                    <span
                        class="grid size-9 shrink-0 place-items-center rounded-lg transition"
                        :class="[
                            i === step ? 'bg-gradient-to-br from-safra-800 to-safra-950 text-lime-300 shadow-[0_6px_16px_-6px_rgb(5_46_22/0.6)]'
                                : i < step ? 'bg-safra-100 text-safra-800' : 'border border-stone-200 bg-white text-stone-400 group-hover:border-stone-300',
                            stepErrors(i).length ? 'ring-2 ring-red-500 ring-offset-2' : '',
                        ]"
                    >
                        <Icon :name="i < step && !stepErrors(i).length ? 'check' : s.icon" class="h-[18px] w-[18px]" :stroke-width="i < step ? 2.6 : 2" />
                    </span>
                    <span class="hidden text-xs leading-tight font-semibold lg:inline" :class="i === step ? 'text-stone-900' : 'text-stone-500'">{{ s.title }}</span>
                </button>
            </li>
        </ol>

        <div v-if="stepErrors(step).length" class="notice-error mb-5" role="alert">
            <Icon name="alert" />
            <div><p v-for="e in stepErrors(step)" :key="e">{{ e }}</p></div>
        </div>

        <form class="space-y-5" @submit.prevent="submit">
            <!-- 1. ONDE -->
            <section v-show="step === 0" class="card grid gap-4 !p-3 sm:gap-5 sm:!p-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.55fr)]">
                <div class="relative z-10 min-w-0 space-y-4">
                  <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                    <label>
                        <span class="label">{{ $t('Nome da propriedade') }}</span>
                        <input v-model="form.farm.name" class="input" required :placeholder="$t('Ex.: Sítio Boa Vista')" />
                    </label>
                    <label>
                        <span class="label">{{ $t('Nome do talhão') }}</span>
                        <input v-model="form.field.name" class="input" required />
                    </label>
                    <div class="grid gap-2 sm:col-span-2 lg:col-span-1" :class="{ 'grid-cols-[minmax(0,1fr)_4.2rem]': form.farm.country_code === 'BR' }">
                        <MunicipalityPicker v-model="municipalityText" :state="form.farm.country_code === 'BR' ? form.farm.state : null" @select="selectMunicipality" />
                        <label>
                            <span class="label">{{ $t(form.farm.country_code === 'BR' ? 'UF' : 'Estado ou região') }}</span>
                            <input v-model="form.farm.state" class="input" :class="{ uppercase: form.farm.country_code === 'BR' }" :maxlength="form.farm.country_code === 'BR' ? 2 : 150" />
                        </label>
                        <p v-if="form.farm.municipality" class="col-span-full text-sm text-stone-600">{{ $t('País') }} · {{ countryName(form.farm.country_code) }} ({{ form.farm.country_code }})</p>
                    </div>
                  </div>
                  <details class="rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm">
                      <summary class="cursor-pointer font-semibold text-stone-700">{{ $t('Prefiro digitar a coordenada') }}</summary>
                      <div class="mt-3 grid grid-cols-2 gap-2">
                          <label class="min-w-0"><span class="label">Latitude</span><input v-model.number="form.field.latitude" type="number" step="0.000001" class="input" /></label>
                          <label class="min-w-0"><span class="label">Longitude</span><input v-model.number="form.field.longitude" type="number" step="0.000001" class="input" /></label>
                          <label class="min-w-0"><span class="label">{{ $t('Área (ha)') }}</span><input v-model.number="form.field.area_ha" type="number" step="0.01" class="input" /></label>
                      </div>
                  </details>
                </div>
                <MapPicker v-model="picked" :city-center="cityCenter" class="min-w-0" />
            </section>

            <!-- 2. SOLO E ÁGUA -->
            <section v-show="step === 1" class="space-y-4">
                <fieldset class="card space-y-4">
                    <legend class="sr-only">{{ $t('Análise de solo') }}</legend>
                    <div class="flex items-center gap-3">
                        <span class="icon-tile-good"><Icon name="layers" /></span>
                        <h2 class="card-title">{{ $t('Você tem análise de solo?') }}</h2>
                    </div>
                    <div class="grid gap-2.5 sm:grid-cols-3">
                        <label v-for="o in [
                            { v: 'lab_analysis', t: 'Sim, de laboratório' },
                            { v: 'farmer_estimate', t: 'Sei mais ou menos' },
                            { v: 'unknown', t: 'Não tenho' },
                        ]" :key="o.v" class="choice">
                            <input v-model="form.soil.source" type="radio" :value="o.v" class="accent-safra-700" /> {{ o.t }}
                        </label>
                    </div>
                    <div v-if="form.soil.source !== 'unknown'" class="grid gap-3 sm:grid-cols-3">
                        <label>
                            <span class="label">{{ $t('Textura') }}</span>
                            <select v-model="form.soil.texture" class="input">
                                <option :value="null">{{ $t('Não sei') }}</option>
                                <option value="arenosa">{{ $t('Arenosa (solo leve)') }}</option>
                                <option value="media">{{ $t('Média', 'Form') }}</option>
                                <option value="argilosa">{{ $t('Argilosa') }}</option>
                                <option value="muito_argilosa">{{ $t('Muito argilosa') }}</option>
                            </select>
                        </label>
                        <label><span class="label">{{ $t('pH (água)') }}</span><input v-model.number="form.soil.ph_water" type="number" step="0.1" class="input" /></label>
                        <label v-if="form.soil.source === 'lab_analysis'"><span class="label">{{ $t('V% (saturação por bases)') }}</span><input v-model.number="form.soil.v_pct" type="number" step="1" class="input" /></label>
                        <template v-if="form.soil.source === 'lab_analysis'">
                            <label><span class="label">{{ $t('Argila (%)') }}</span><input v-model.number="form.soil.clay_pct" type="number" step="1" class="input" /></label>
                            <label><span class="label">{{ $t('Matéria orgânica (%)') }}</span><input v-model.number="form.soil.organic_matter_pct" type="number" step="0.1" class="input" /></label>
                            <label><span class="label">{{ $t('Data da coleta') }}</span><input v-model="form.soil.sampled_at" type="date" class="input" /></label>
                        </template>
                    </div>
                    <p v-else class="text-sm text-stone-600">{{ $t('Sem problema: a análise fica marcada como') }} <em>{{ $t('“estimada — confirmar localmente”') }}</em> {{ $t('e a confiança será menor.') }}</p>
                </fieldset>

                <fieldset class="card space-y-4">
                    <legend class="sr-only">{{ $t('Irrigação') }}</legend>
                    <div class="flex items-center gap-3">
                        <span class="icon-tile-info"><Icon name="droplet" /></span>
                        <h2 class="card-title">{{ $t('Irrigação') }}</h2>
                    </div>
                    <label class="choice"><input v-model="form.field.irrigated" type="checkbox" class="h-5 w-5 accent-safra-700" /> {{ $t('Este talhão tem irrigação') }}</label>
                    <label v-if="form.field.irrigated">
                        <span class="label">{{ $t('Quanto consegue aplicar? (mm por dia)') }}</span>
                        <input v-model.number="form.field.irrigation_mm_day" type="number" step="0.5" min="0" max="20" class="input" />
                    </label>
                </fieldset>
            </section>

            <!-- 3. HISTÓRICO -->
            <section v-show="step === 2" class="space-y-3">
                <p class="text-stone-600">{{ $t('Conte o que você plantou neste talhão no último ano. É assim que encontramos os períodos de') }} <Term k="solo_descoberto" :label="$t('solo descoberto')" />.</p>
                <button v-if="!form.history.length" type="button" class="btn-secondary w-full" @click="quickFill"><Icon name="sprout" /> {{ $t('Preencher com “Soja → Milho safrinha” (comum no Cerrado)') }}</button>
                <div v-for="(h, i) in form.history" :key="i" class="card grid gap-3 sm:grid-cols-[auto_1fr_1fr_1fr_auto] sm:items-end">
                    <span class="hidden h-[50px] w-9 place-items-center rounded-lg bg-stone-100 text-sm font-bold text-stone-500 tabular-nums sm:grid">{{ i + 1 }}</span>
                    <label>
                        <span class="label">{{ $t('Cultura') }}</span>
                        <select v-model="h.crop" class="input">
                            <option v-for="c in crops" :key="c.slug" :value="c.slug">{{ $t(c.name) }}</option>
                        </select>
                    </label>
                    <label><span class="label">{{ $t('Plantio') }}</span><input v-model="h.sown_at" type="date" class="input" required /></label>
                    <label><span class="label">{{ $t('Colheita') }}</span><input v-model="h.harvested_at" type="date" class="input" required /></label>
                    <button type="button" class="btn-danger !px-3.5" :aria-label="$t('Remover safra')" @click="removeHistory(i)"><Icon name="trash" /></button>
                </div>
                <button type="button" class="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-stone-300 p-4 text-sm font-semibold text-stone-600 transition hover:border-safra-600 hover:bg-safra-50 hover:text-safra-800" @click="addHistory()"><Icon name="plus" class="h-4 w-4" /> {{ $t('Adicionar safra') }}</button>
            </section>

            <!-- 4. PRIORIDADES -->
            <section v-show="step === 3" class="grid gap-3 md:grid-cols-2">
                <div v-for="p in PRIORITIES" :key="p.key" class="card flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <p class="flex items-center gap-2 font-semibold"><Icon :name="p.icon" class="h-[18px] w-[18px] text-safra-700" /> {{ p.label }}</p>
                        <p class="text-sm text-stone-500">{{ p.help }}</p>
                    </div>
                    <StarRating v-model="form.priorities[p.key]" :label="p.label" />
                </div>
            </section>

            <!-- 5. RESTRIÇÕES -->
            <section v-show="step === 4" class="space-y-4">
                <fieldset class="card space-y-4">
                    <legend class="sr-only">{{ $t('Culturas excluídas') }}</legend>
                    <div class="flex items-center gap-3">
                        <span class="icon-tile-bad"><Icon name="x" :stroke-width="2.5" /></span>
                        <div><h2 class="card-title">{{ $t('Culturas que você não quer ou não pode plantar') }}</h2><p class="text-sm text-stone-500">{{ $t('Toque para excluir.') }}</p></div>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button
                            v-for="c in crops"
                            :key="c.slug"
                            type="button"
                            class="inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-sm font-medium transition"
                            :class="form.constraints.excluded_crops.includes(c.slug) ? 'border-red-300 bg-red-50 text-red-800' : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300'"
                            :aria-pressed="form.constraints.excluded_crops.includes(c.slug)"
                            @click="toggle(form.constraints.excluded_crops, c.slug)"
                        ><Icon v-if="form.constraints.excluded_crops.includes(c.slug)" name="x" class="h-3.5 w-3.5" :stroke-width="2.5" />{{ $t(c.name) }}</button>
                    </div>
                </fieldset>
                <fieldset class="card space-y-3">
                    <legend class="sr-only">{{ $t('Mercado') }}</legend>
                    <div class="flex items-center gap-3">
                        <span class="icon-tile-good"><Icon name="target" /></span>
                        <h2 class="card-title">{{ $t('Tem comprador na sua região?') }}</h2>
                    </div>
                    <div class="divide-y divide-stone-100">
                        <div v-for="c in cashCrops" :key="c.slug" class="flex items-center justify-between gap-3 py-2.5">
                            <span class="text-sm font-medium">{{ $t(c.name) }}</span>
                            <div class="flex rounded-xl border border-stone-200 bg-stone-50 p-0.5 text-xs font-semibold">
                                <button v-for="o in [{ v: 'buyer', t: 'Tem' }, { v: 'unknown', t: $t('Não sei') }, { v: 'none', t: 'Não tem' }] as const" :key="o.v" type="button"
                                    class="rounded-lg px-2.5 py-1.5 transition" :class="market(c.slug) === o.v ? (o.v === 'none' ? 'bg-red-600 text-white shadow' : 'bg-safra-700 text-white shadow') : 'text-stone-600 hover:text-stone-900'" :aria-pressed="market(c.slug) === o.v" @click="setMarket(c.slug, o.v)">{{ o.t }}</button>
                            </div>
                        </div>
                    </div>
                </fieldset>
                <fieldset class="card space-y-3">
                    <legend class="sr-only">{{ $t('Equipamentos') }}</legend>
                    <div class="flex items-center gap-3">
                        <span class="icon-tile-warn"><Icon name="tractor" /></span>
                        <h2 class="card-title">{{ $t('Equipamentos que você NÃO tem') }}</h2>
                    </div>
                    <div class="grid gap-2 sm:grid-cols-2">
                        <label v-for="e in equipment" :key="e.key" class="choice">
                            <input type="checkbox" class="h-5 w-5 accent-safra-700" :checked="form.constraints.missing_equipment.includes(e.key)" @change="toggle(form.constraints.missing_equipment, e.key)" />
                            {{ $t(e.label) }}
                        </label>
                    </div>
                </fieldset>
                <label class="choice"><input v-model="form.farm.has_livestock" type="checkbox" class="h-5 w-5 accent-safra-700" /> {{ $t('Tenho gado (forragem tem uso na propriedade)') }}</label>
            </section>

            <div class="sticky bottom-[max(0.5rem,env(safe-area-inset-bottom))] z-10 flex gap-2 rounded-2xl border border-stone-200 bg-white/95 p-2 shadow-[var(--shadow-lift)] backdrop-blur sm:gap-3 sm:p-3">
                <button v-if="step > 0" type="button" class="btn-secondary min-h-11 min-w-0 flex-1 !px-2 text-center !text-sm !whitespace-normal sm:flex-none sm:!px-5" @click="goToStep(step - 1)"><Icon name="arrowLeft" /> {{ $t('Voltar') }}</button>
                <span class="hidden flex-1 items-center text-sm text-stone-500 sm:flex">
                    <template v-if="missingStep0"><Icon name="info" class="mr-1.5 h-4 w-4 shrink-0" /> {{ missingStep0 }}</template>
                </span>
                <button v-if="step < steps.length - 1" type="button" class="btn-primary min-h-11 min-w-0 flex-1 !px-2 text-center !text-sm !whitespace-normal sm:flex-none sm:!px-5" :disabled="!canAdvance()" @click="goToStep(step + 1)">{{ $t('Continuar') }} <Icon name="arrowRight" /></button>
                <button v-else type="submit" class="btn-primary min-h-11 min-w-0 flex-1 !px-2 text-center !text-sm !whitespace-normal sm:flex-none sm:!px-5" :disabled="form.processing">
                    <Icon name="check" :stroke-width="2.5" /> {{ form.processing ? $t('Salvando…') : editing ? $t('Salvar alterações') : $t('Salvar e analisar') }}
                </button>
            </div>
            <p v-if="missingStep0" class="text-center text-sm text-stone-500 sm:hidden">{{ missingStep0 }}</p>
        </form>
        </div>
    </AppLayout>
</template>
