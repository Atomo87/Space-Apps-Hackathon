<script setup lang="ts">
import { t } from '@/lib/i18n';
import { ref } from 'vue';
import { api } from '@/lib/api';
import { CRITERIA_ICONS, scoreColor } from '@/lib/labels';
import type { Strategy } from '@/types/contract';
import ConfidenceBadge from './ConfidenceBadge.vue';
import Icon, { type IconName } from './Icon.vue';
import RotationBar from './RotationBar.vue';

const props = defineProps<{ strategy: Strategy; fieldId: number; best?: boolean }>();
const showEvidence = ref(false);
const showCriteria = ref(false);
const verdict = ref<string | null>(null);
const comment = ref('');
const sent = ref<string | null>(null);
const sending = ref(false);

const VERDICTS: { v: string; t: string; icon: IconName }[] = [
    { v: 'makes_sense', t: t('Faz sentido'), icon: 'check' },
    { v: 'needs_adjustment', t: t('Precisa de ajuste'), icon: 'edit' },
    { v: 'not_applicable', t: t('Não se aplica'), icon: 'x' },
];

async function sendFeedback() {
    if (!verdict.value) return;
    sending.value = true;
    try {
        const r = await api<{ message: string }>(`/api/v1/fields/${props.fieldId}/feedback`, {
            method: 'POST',
            body: JSON.stringify({ strategy_key: props.strategy.key, verdict: verdict.value, comment: comment.value || null, snapshot: { title: props.strategy.title, score: props.strategy.score } }),
        });
        sent.value = r.message;
    } catch (e) {
        sent.value = (e as Error).message;
    } finally {
        sending.value = false;
    }
}
</script>

<template>
    <article class="card flex flex-col gap-5 break-inside-avoid" :class="best ? 'card-accent border-safra-600 ring-4 ring-safra-100' : ''">
        <header class="flex items-start gap-3.5">
            <span
                class="grid h-11 w-11 shrink-0 place-items-center rounded-xl text-lg font-black"
                :class="strategy.is_current ? 'bg-stone-100 text-stone-600 ring-1 ring-stone-200 ring-inset' : 'bg-gradient-to-br from-safra-800 to-safra-950 text-lime-300 shadow-[0_6px_16px_-6px_rgb(5_46_22/0.6)]'"
            >{{ strategy.label }}</span>
            <div class="min-w-0 flex-1">
                <p v-if="strategy.is_current" class="text-[11px] font-bold tracking-[0.12em] text-stone-500 uppercase">{{ $t('Sua rotação atual') }}</p>
                <h3 class="text-[17px] leading-snug font-bold tracking-tight text-stone-900">{{ $t(strategy.title) }}</h3>
                <p class="mt-0.5 text-sm text-stone-600">{{ $t(strategy.focus) }}</p>
            </div>
            <div class="shrink-0 rounded-2xl bg-stone-50 px-3 py-2 text-center ring-1 ring-stone-200 ring-inset">
                <p class="text-3xl leading-none font-black tabular-nums" :class="scoreColor(strategy.score)">{{ strategy.score }}</p>
                <p class="mt-0.5 text-[10px] font-semibold text-stone-500 uppercase">{{ $t('de 100') }}</p>
                <p v-if="strategy.score_range" class="text-[10px] text-stone-500 tabular-nums" :title="$t('Variação entre anos secos e chuvosos')">{{ strategy.score_range.p10 }}–{{ strategy.score_range.p90 }}</p>
            </div>
        </header>

        <div class="flex flex-wrap items-center gap-2">
            <ConfidenceBadge :level="strategy.confidence.level" :value="strategy.confidence.value" />
            <span v-if="best" class="badge bg-gradient-to-r from-safra-700 to-safra-800 text-white"><Icon name="star" class="h-3 w-3" :stroke-width="2.5" /> {{ $t('Melhor nota com suas prioridades') }}</span>
            <span v-if="strategy.low_confidence_badge" class="badge bg-red-600 text-white"><Icon name="alert" class="h-3 w-3" :stroke-width="2.5" /> {{ $t('Baixa confiança — validar com técnico') }}</span>
        </div>

        <RotationBar :strategy="strategy" />

        <section>
            <h4 class="mb-1.5 flex items-center gap-1.5 text-xs font-bold tracking-[0.1em] text-stone-500 uppercase"><Icon name="info" class="h-3.5 w-3.5" /> {{ $t('Por quê') }}</h4>
            <p class="text-[15px] leading-relaxed text-stone-700">{{ strategy.rationale }}</p>
        </section>

        <section v-if="strategy.benefits.length">
            <h4 class="mb-2 flex items-center gap-1.5 text-xs font-bold tracking-[0.1em] text-safra-700 uppercase"><Icon name="check" class="h-3.5 w-3.5" :stroke-width="2.5" /> {{ $t('Benefícios') }}</h4>
            <ul class="space-y-1.5 text-sm text-stone-700">
                <li v-for="b in strategy.benefits" :key="b" class="flex gap-2.5"><span class="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-safra-600" />{{ b }}</li>
            </ul>
        </section>

        <section v-if="strategy.conflicts.length" class="flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <Icon name="scale" class="mt-0.5 h-4 w-4 shrink-0" />{{ strategy.conflicts.join(' ') }}
        </section>

        <div class="flex flex-wrap gap-2">
            <button type="button" class="btn-secondary btn-sm" :aria-expanded="showCriteria" @click="showCriteria = !showCriteria">
                <Icon name="bars" /> {{ showCriteria ? $t('Esconder') : $t('Ver') }} {{ $t('notas por critério') }}
            </button>
            <button type="button" class="btn-secondary btn-sm" :aria-expanded="showEvidence" @click="showEvidence = !showEvidence">
                <Icon name="database" /> {{ showEvidence ? $t('Esconder') : $t('Ver') }} {{ $t('evidências') }}
            </button>
        </div>

        <ul v-if="showCriteria" class="animate-fade-up space-y-3 rounded-xl bg-stone-50 p-3.5">
            <li v-for="c in strategy.criteria" :key="c.key" class="text-sm">
                <div class="flex items-center gap-2">
                    <Icon :name="CRITERIA_ICONS[c.key] ?? 'info'" class="h-4 w-4 shrink-0 text-stone-500" />
                    <span class="flex-1 font-medium text-stone-800">{{ $t(c.label) }} <span class="text-xs font-normal text-stone-400">{{ $t('peso') }} {{ c.weight }}</span></span>
                    <span v-if="c.delta_vs_current !== null && c.delta_vs_current !== 0" class="badge text-[11px] tabular-nums" :class="c.delta_vs_current > 0 ? 'bg-safra-100 text-safra-800' : 'bg-red-100 text-red-700'">{{ c.delta_vs_current > 0 ? '+' : '' }}{{ c.delta_vs_current }}</span>
                    <span class="w-8 text-right font-black tabular-nums" :class="scoreColor(c.score)">{{ c.score }}</span>
                </div>
                <div class="mt-1.5 ml-6 h-1.5 overflow-hidden rounded-full bg-stone-200"><div class="h-full rounded-full bg-gradient-to-r from-safra-600 to-lime-400" :style="{ width: `${c.score}%` }" /></div>
                <p class="mt-1 ml-6 text-xs text-stone-500">{{ c.explanation }}</p>
            </li>
        </ul>

        <ul v-if="showEvidence" class="animate-fade-up space-y-2 text-sm">
            <li v-for="e in strategy.evidences" :key="e.text" class="rounded-xl border border-stone-200 bg-stone-50 p-3 text-stone-700">
                {{ e.text }}
                <span class="mt-1.5 flex flex-wrap gap-1"><span v-for="d in e.datasets" :key="d" class="badge bg-white text-[10px] text-stone-600 ring-1 ring-stone-200">{{ $t(d) }}</span><span class="badge bg-white text-[10px] text-stone-500 ring-1 ring-stone-200">{{ $t(e.period) }}</span></span>
            </li>
        </ul>

        <div class="grid gap-4 sm:grid-cols-2">
            <section class="rounded-xl bg-stone-50 p-3.5">
                <h4 class="mb-2 flex items-center gap-1.5 text-xs font-bold tracking-[0.1em] text-stone-500 uppercase"><Icon name="info" class="h-3.5 w-3.5" /> {{ $t('O que não sabemos') }}</h4>
                <ul class="space-y-1.5 text-[13px] text-stone-700">
                    <li v-for="g in strategy.information_gaps" :key="g" class="flex gap-2"><span class="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-stone-400" />{{ g }}</li>
                </ul>
            </section>
            <section class="rounded-xl bg-amber-50/70 p-3.5">
                <h4 class="mb-2 flex items-center gap-1.5 text-xs font-bold tracking-[0.1em] text-amber-800 uppercase"><Icon name="user" class="h-3.5 w-3.5" /> {{ $t('Confirme no campo') }}</h4>
                <ul class="space-y-1.5 text-[13px] text-stone-700">
                    <li v-for="r in strategy.local_review_risks" :key="r" class="flex gap-2"><span class="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-amber-500" />{{ r }}</li>
                </ul>
            </section>
        </div>

        <section class="mt-auto border-t border-stone-100 pt-4 print:hidden">
            <p class="mb-2.5 flex items-center gap-2 text-sm font-semibold text-stone-800"><Icon name="message" class="h-4 w-4 text-stone-500" /> {{ $t('Isso faz sentido para o seu talhão?') }}</p>
            <div v-if="!sent" class="space-y-2.5">
                <div class="flex flex-wrap gap-2">
                    <button v-for="o in VERDICTS" :key="o.v" type="button"
                        class="inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition"
                        :class="verdict === o.v ? 'border-safra-600 bg-safra-50 text-safra-900 ring-4 ring-safra-100' : 'border-stone-200 text-stone-700 hover:border-stone-300'"
                        :aria-pressed="verdict === o.v" @click="verdict = o.v"><Icon :name="o.icon" class="h-3.5 w-3.5" /> {{ o.t }}</button>
                </div>
                <div v-if="verdict" class="flex animate-fade-up gap-2">
                    <input v-model="comment" class="input !py-2 text-sm" :placeholder="$t('Comentário (opcional)')" maxlength="2000" :aria-label="$t('Comentário')" />
                    <button type="button" class="btn-primary btn-sm" :disabled="sending" @click="sendFeedback">{{ $t('Enviar') }}</button>
                </div>
            </div>
            <p v-else class="notice-info !py-2.5 text-sm"><Icon name="check" :stroke-width="2.5" />{{ sent }}</p>
        </section>
    </article>
</template>
