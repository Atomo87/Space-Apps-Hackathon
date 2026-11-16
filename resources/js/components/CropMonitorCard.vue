<script setup lang="ts">
import { locale, t, tf } from '@/lib/i18n';
import { computed } from 'vue';
import type { Earthdata, Fires, Vegetation } from '@/types/contract';
import DatasetBadge from './DatasetBadge.vue';
import Icon, { type IconName } from './Icon.vue';

/**
 * Monitor da safra atual: a imagem de satélite mais recente comparada com o normal do próprio talhão,
 * a umidade do solo do último mês (SMAP) e os focos de queimada da semana (FIRMS).
 */
const props = defineProps<{ vegetation: Vegetation | null | undefined; earthdata: Earthdata | null | undefined; fires: Fires | null; firesLoading: boolean }>();

type Tone = 'good' | 'warn' | 'bad' | 'neutral';
const TONE: Record<Tone, string> = {
    good: 'border-safra-200 bg-safra-50/60',
    warn: 'border-amber-200 bg-amber-50/70',
    bad: 'border-red-200 bg-red-50/70',
    neutral: 'border-stone-200 bg-stone-50',
};
const DOT: Record<Tone, string> = { good: 'bg-safra-600', warn: 'bg-amber-500', bad: 'bg-red-600', neutral: 'bg-stone-400' };

const num = (x: number | null | undefined, d = 2) => (x === null || x === undefined ? '—' : x.toLocaleString(locale, { minimumFractionDigits: d, maximumFractionDigits: d }));
const dateBr = (iso: string) => new Date(`${iso.slice(0, 10)}T12:00:00`).toLocaleDateString(locale, { day: '2-digit', month: 'short' });

/** Referência: HLS (30 m) quando tem imagem recente; senão MODIS (250 m). */
const green = computed(() => {
    const v = props.vegetation;
    if (!v) return null;
    const src = v.hls?.recent ? v.hls : v;
    const r = src.recent;
    if (!r) return null;
    const month = Number(r.date.slice(5, 7));
    const normal = src.monthly.find((m) => m.month === month)?.p50 ?? null;
    const a = r.anomaly ?? 0;
    const tone: Tone = r.below_p10 || a <= -0.1 ? 'bad' : a <= -0.05 ? 'warn' : 'good';
    const text = tone === 'bad' ? t('Bem abaixo do normal para a época') : tone === 'warn' ? t('Um pouco abaixo do normal') : a >= 0.05 ? t('Acima do normal para a época') : t('Dentro do normal para a época');
    return { code: src === v.hls ? 'HLS 30 m' : 'MODIS 250 m', date: r.date, daysAgo: r.days_ago, ndvi: r.ndvi, normal, anomaly: r.anomaly, tone, text };
});

const soil = computed(() => {
    const s = props.earthdata?.smap;
    if (!s?.recent || s.recent.sm === null) return null;
    const a = s.recent.anomaly ?? 0;
    const tone: Tone = a <= -0.05 ? 'bad' : a <= -0.02 ? 'warn' : 'good';
    const text = tone === 'bad' ? t('Solo bem mais seco que o normal') : tone === 'warn' ? t('Solo um pouco mais seco que o normal') : a >= 0.02 ? t('Solo mais úmido que o normal') : t('Umidade dentro do normal');
    const last = s.series.length ? s.series[s.series.length - 1].date : null;
    return { sm: s.recent.sm, anomaly: s.recent.anomaly, tone, text, last };
});

const fire = computed(() => {
    const f = props.fires;
    if (!f || !f.configured || !f.counts) return null;
    const near = f.counts['10'] ?? 0;
    const mid = f.counts['25'] ?? 0;
    const tone: Tone = near > 0 ? 'bad' : mid > 0 ? 'warn' : 'good';
    const total = f.counts[String(f.radius_km)] ?? f.points.length;
    const text = near > 0 ? tf('{count} foco(s) a até 10 km', { count: near }) : mid > 0 ? tf('{count} foco(s) a até 25 km', { count: mid }) : total > 0 ? tf('Nenhum foco a até 25 km ({count} a até {radius} km)', { count: total, radius: f.radius_km }) : tf('Nenhum foco a até {radius} km', { radius: f.radius_km });
    return { tone, text, nearest: f.nearest_km, days: f.days };
});

const actions = computed(() => {
    const out: { icon: IconName; text: string }[] = [];
    if (green.value && green.value.tone !== 'good') out.push({ icon: 'sprout', text: t('Percorra o talhão: veja falhas de estande, pragas, doenças ou sinais de falta d’água nas áreas mais claras da imagem.') });
    if (soil.value && soil.value.tone !== 'good') out.push({ icon: 'droplet', text: t('Solo mais seco que o normal: se for plantar, confira a umidade a 10–20 cm antes; se a lavoura já está no campo, priorize a irrigação disponível.') });
    if (fire.value && fire.value.tone !== 'good') out.push({ icon: 'flame', text: t('Há queimadas por perto: mantenha aceiros limpos, avise vizinhos e a brigada local e evite queimar palha nesses dias.') });
    if (!out.length) out.push({ icon: 'check', text: t('Nada fora do normal nas observações mais recentes. Continue acompanhando a cada nova imagem.') });
    return out;
});
</script>

<template>
    <div class="card">
        <div class="card-head">
            <div>
                <h2><span class="h-icon"><Icon name="satellite" /></span> {{ $t('Monitor da safra atual') }}</h2>
                <p>{{ $t('O que os satélites viram nas últimas semanas, comparado com o normal deste talhão.') }}</p>
            </div>
        </div>

        <div class="grid gap-3 md:grid-cols-3">
            <div class="rounded-xl border p-4" :class="TONE[green?.tone ?? 'neutral']">
                <p class="flex items-center justify-between gap-2 text-xs font-semibold text-stone-600">
                    <span class="inline-flex items-center gap-1.5"><Icon name="leaf" class="h-3.5 w-3.5" /> {{ $t('Verde da lavoura') }}</span>
                    <DatasetBadge v-if="green" :code="green.code" />
                </p>
                <template v-if="green">
                    <p class="mt-2 flex items-center gap-2 font-bold text-stone-900"><span class="h-2 w-2 rounded-full" :class="DOT[green.tone]" /> {{ green.text }}</p>
                    <p class="mt-1 text-sm text-stone-600 tabular-nums">NDVI {{ num(green.ndvi) }}<template v-if="green.normal !== null"> · normal {{ num(green.normal) }}</template></p>
                    <p class="mt-1 text-xs text-stone-500">{{ $t('Imagem de') }} {{ dateBr(green.date) }} {{ $t('(há') }} {{ green.daysAgo }} {{ $t('dias)') }}</p>
                </template>
                <p v-else class="mt-2 text-sm text-stone-500">{{ $t('Sem imagem recente sem nuvem.') }}</p>
            </div>

            <div class="rounded-xl border p-4" :class="TONE[soil?.tone ?? 'neutral']">
                <p class="flex items-center justify-between gap-2 text-xs font-semibold text-stone-600">
                    <span class="inline-flex items-center gap-1.5"><Icon name="droplet" class="h-3.5 w-3.5" /> {{ $t('Umidade do solo') }}</span>
                    <DatasetBadge v-if="soil" code="SMAP" />
                </p>
                <template v-if="soil">
                    <p class="mt-2 flex items-center gap-2 font-bold text-stone-900"><span class="h-2 w-2 rounded-full" :class="DOT[soil.tone]" /> {{ soil.text }}</p>
                    <p class="mt-1 text-sm text-stone-600 tabular-nums">{{ num(soil.sm) }} m³/m³<template v-if="soil.anomaly !== null"> · {{ soil.anomaly > 0 ? '+' : '' }}{{ num(soil.anomaly) }} {{ $t('do normal') }}</template></p>
                    <p v-if="soil.last" class="mt-1 text-xs text-stone-500">{{ $t('Última passagem:') }} {{ dateBr(soil.last) }}</p>
                </template>
                <p v-else class="mt-2 text-sm text-stone-500">{{ $t('SMAP indisponível nesta análise.') }}</p>
            </div>

            <div class="rounded-xl border p-4" :class="TONE[fire?.tone ?? 'neutral']">
                <p class="flex items-center justify-between gap-2 text-xs font-semibold text-stone-600">
                    <span class="inline-flex items-center gap-1.5"><Icon name="flame" class="h-3.5 w-3.5" /> {{ $t('Queimadas por perto') }}</span>
                    <DatasetBadge v-if="fire" code="FIRMS" />
                </p>
                <p v-if="firesLoading" class="mt-2 text-sm text-stone-500">{{ $t('Consultando a NASA FIRMS…') }}</p>
                <template v-else-if="fire">
                    <p class="mt-2 flex items-center gap-2 font-bold text-stone-900"><span class="h-2 w-2 rounded-full" :class="DOT[fire.tone]" /> {{ fire.text }}</p>
                    <p class="mt-1 text-sm text-stone-600">{{ $t('Últimos') }} {{ fire.days }} {{ $t('dias') }}<template v-if="fire.nearest !== null"> {{ $t('· mais próximo a') }} {{ fire.nearest.toLocaleString(locale) }} km</template></p>
                    <p class="mt-1 text-xs text-stone-500">{{ $t('Satélites VIIRS e MODIS, quase em tempo real') }}</p>
                </template>
                <p v-else class="mt-2 text-sm text-stone-500">{{ $t('Focos de queimada indisponíveis para este local.') }}</p>
            </div>
        </div>

        <ul class="mt-4 space-y-2">
            <li v-for="a in actions" :key="a.text" class="flex items-start gap-2.5 text-sm text-stone-700">
                <Icon :name="a.icon" class="mt-0.5 h-4 w-4 shrink-0 text-safra-700" /> {{ a.text }}
            </li>
        </ul>
    </div>
</template>
