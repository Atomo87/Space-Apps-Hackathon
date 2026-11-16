<script setup lang="ts">
import { t, locale, tf } from '@/lib/i18n';
import { ref } from 'vue';
import type { Planting, PlantingWeek } from '@/types/contract';
import DatasetBadge from './DatasetBadge.vue';
import Icon from './Icon.vue';

/** Janela de plantio: para cada safra, a chance de um ano "bom" semeando em cada semana (clima diário da NASA POWER). */
const props = defineProps<{ planting: Planting }>();

const pct = (x: number | null) => (x === null ? '—' : `${Math.round(x * 100)}%`);
const selected = ref<Record<string, PlantingWeek | null>>({});

function tone(score: number) {
    if (score >= 0.7) return 'bg-safra-600';
    if (score >= 0.5) return 'bg-lime-400';
    if (score >= 0.3) return 'bg-amber-300';
    if (score > 0) return 'bg-orange-300';
    return 'bg-stone-200';
}

function bestOf(weeks: PlantingWeek[]) {
    return weeks.reduce<PlantingWeek | null>((a, w) => (!a || w.score > a.score ? w : a), null);
}

function pick(season: string, w: PlantingWeek) {
    selected.value = { ...selected.value, [season]: selected.value[season]?.date === w.date ? null : w };
}

const BEST = {
    good: { cls: 'bg-safra-50 text-safra-800 ring-safra-200', text: t('Janela confiável') },
    medium: { cls: 'bg-amber-50 text-amber-900 ring-amber-200', text: t('Janela curta ou instável') },
    low: { cls: 'bg-red-50 text-red-800 ring-red-200', text: t('Sem janela segura sem irrigação') },
} as const;
const plantingDate = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', timeZone: 'UTC' });

function weekLabel(week: { date: string }): string {
    return plantingDate.format(new Date(`2000-${week.date}T00:00:00Z`));
}
</script>

<template>
    <div class="card">
        <div class="card-head">
            <div>
                <h2><span class="h-icon"><Icon name="calendar" /></span> {{ $t('Janela de plantio ideal') }}</h2>
                <p>
                    {{ $t('Semana a semana, em quantos anos (') }}{{ planting.period.start }}–{{ planting.period.end }}{{ $t(') semear naquela data teria dado certo: umidade para germinar, sem veranico no início, chuva suficiente no ciclo e sem geada.') }}
                </p>
            </div>
            <DatasetBadge code="POWER diário" />
        </div>

        <div class="space-y-6">
            <section v-for="s in props.planting.seasons" :key="s.key" :aria-label="$t(s.label)">
                <div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                    <div>
                        <h3 class="font-bold text-stone-900">{{ $t(s.label) }}</h3>
                        <p class="text-xs text-stone-500">{{ s.crops }} {{ $t('· precisa de ~') }}{{ s.need_mm }} {{ $t('mm em 90 dias') }}</p>
                    </div>
                    <span v-if="s.best" class="badge ring-1 ring-inset" :class="BEST[s.best.level].cls">
                        <template v-if="s.best.start">{{ s.best.start }}<template v-if="s.best.end !== s.best.start"> – {{ s.best.end }}</template> · {{ pct(s.best.score) }} {{ $t('dos anos') }}</template>
                        <template v-else>{{ BEST.low.text }}</template>
                    </span>
                </div>

                <div v-if="s.weeks.length" class="flex gap-[3px]" role="list">
                    <button
                        v-for="w in s.weeks"
                        :key="w.date"
                        type="button"
                        role="listitem"
                        class="group relative h-10 min-w-0 flex-1 rounded-[5px] transition hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-safra-700"
                        :class="[tone(w.score), selected[s.key]?.date === w.date ? 'ring-2 ring-stone-900 ring-offset-1' : '']"
                        :aria-label="tf('Semear em {date}: {pct} dos anos bons', { date: weekLabel(w), pct: pct(w.score) })"
                        :title="tf('{date}: {pct} dos anos bons', { date: weekLabel(w), pct: pct(w.score) })"
                        @click="pick(s.key, w)"
                    >
                        <span class="sr-only">{{ weekLabel(w) }}</span>
                    </button>
                </div>
                <div v-if="s.weeks.length" class="mt-1 flex justify-between text-[10.5px] text-stone-500 tabular-nums">
                    <span>{{ weekLabel(s.weeks[0]) }}</span>
                    <span v-if="s.weeks.length > 4">{{ weekLabel(s.weeks[Math.floor(s.weeks.length / 2)]) }}</span>
                    <span>{{ weekLabel(s.weeks[s.weeks.length - 1]) }}</span>
                </div>

                <div v-for="w in [selected[s.key] ?? bestOf(s.weeks)]" :key="w?.date ?? 'none'">
                    <div v-if="w" class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
                        <div class="metric !p-3"><p class="metric-label">{{ selected[s.key] ? $t('Semana escolhida') : $t('Melhor semana') }}</p><p class="metric-value !text-lg">{{ weekLabel(w) }}</p></div>
                        <div class="metric !p-3"><p class="metric-label">{{ $t('Anos bons') }}</p><p class="metric-value !text-lg">{{ pct(w.score) }}</p></div>
                        <div v-if="w.p_onset !== null" class="metric !p-3"><p class="metric-label">{{ $t('Umidade para semear') }}</p><p class="metric-value !text-lg">{{ pct(w.p_onset) }}</p></div>
                        <div class="metric !p-3"><p class="metric-label">{{ $t('Veranico no início') }}</p><p class="metric-value !text-lg">{{ pct(w.p_dry_spell) }}</p></div>
                        <div class="metric !p-3"><p class="metric-label">{{ $t('Chuva suficiente') }}</p><p class="metric-value !text-lg">{{ pct(w.p_water) }}</p></div>
                        <div v-if="w.p_frost !== null" class="metric !p-3"><p class="metric-label">{{ $t('Geada no ciclo') }}</p><p class="metric-value !text-lg">{{ pct(w.p_frost) }}</p></div>
                        <div class="metric !p-3"><p class="metric-label">{{ $t('Dias ≥ 35 °C na floração') }}</p><p class="metric-value !text-lg">{{ w.heat_days.toLocaleString(locale) }}</p></div>
                    </div>
                </div>
            </section>
        </div>

        <div class="mt-5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-stone-600">
            <span class="inline-flex items-center gap-1.5"><span class="h-3 w-3 rounded-sm bg-safra-600" /> {{ $t('≥ 70% dos anos bons') }}</span>
            <span class="inline-flex items-center gap-1.5"><span class="h-3 w-3 rounded-sm bg-lime-400" /> 50–69%</span>
            <span class="inline-flex items-center gap-1.5"><span class="h-3 w-3 rounded-sm bg-amber-300" /> 30–49%</span>
            <span class="inline-flex items-center gap-1.5"><span class="h-3 w-3 rounded-sm bg-orange-300" /> {{ $t('abaixo de 30%') }}</span>
            <span class="inline-flex items-center gap-1.5"><span class="h-3 w-3 rounded-sm bg-stone-200" /> {{ $t('nenhum ano') }}</span>
        </div>
        <p class="mt-3 text-xs leading-relaxed text-stone-500">
            {{ $t('Regras: ≥') }} {{ planting.rules.onset_mm }} {{ $t('mm nos 10 dias antes (só na safra de verão), sem') }} {{ planting.rules.dry_spell_days }} {{ $t('dias seguidos secos nos 30 dias depois, chuva do ciclo (90 dias) acima da necessidade e mínima acima de') }} {{ planting.rules.frost_tmin_c }} {{ $t('°C. Toque numa semana para ver os detalhes. É clima, não previsão: confira o') }} <strong>{{ $t('zoneamento agrícola (ZARC)') }}</strong>{{ $t(', a variedade e a umidade real do solo antes de plantar.') }}
        </p>
    </div>
</template>
