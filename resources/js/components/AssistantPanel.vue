<script setup lang="ts">
import { t, locale, tf } from '@/lib/i18n';
import { nextTick, ref } from 'vue';
import { api, ApiError } from '@/lib/api';
import DatasetBadge from './DatasetBadge.vue';
import Icon from './Icon.vue';

/**
 * Pergunte ao GeoSafra: IA (Gemini) com RAG. Cada afirmação mostra as evidências que a sustentam —
 * indicador, valor, período e fonte — e o servidor descarta o que não tiver respaldo.
 */
const props = defineProps<{ fieldId: number }>();

interface Fact { id: string; label: string; value: string | number; unit: string | null; period: string | null; source: string; dataset: string }
interface Ref { id: string; title: string; text: string; source: string; url?: string | null; locale?: string }
interface Claim { text: string; fact_ids: string[]; ref_ids: string[] }
interface Answer {
    question: string;
    mode: 'ai' | 'evidence' | 'reference';
    model: string | null;
    notice?: string;
    claims: Claim[];
    rejected: { text: string; reason: string }[];
    limitations: string[];
    follow_up_questions: string[];
    facts: Record<string, Fact>;
    refs: Ref[];
    evidence_count: number;
}

const SUGGESTIONS = [
    t('Quando devo plantar a soja e qual o risco de veranico?'),
    t('Vale a pena trocar o pousio por uma cultura de cobertura?'),
    t('A água da região está diminuindo?'),
    t('Como está a lavoura agora em relação ao normal?'),
    t('Quais meses deixam o solo mais exposto à erosão?'),
];

const question = ref('');
const loading = ref(false);
const error = ref<string | null>(null);
const history = ref<Answer[]>([]);
const openRef = ref<string | null>(null);
const list = ref<HTMLElement | null>(null);

function fmtValue(f: Fact) {
    const v = typeof f.value === 'number' ? f.value.toLocaleString(locale, { maximumFractionDigits: 3 }) : f.value;
    return f.unit ? `${v} ${f.unit}` : String(v);
}

async function ask(q?: string) {
    const text = (q ?? question.value).trim();
    if (text.length < 3 || loading.value) return;
    loading.value = true;
    error.value = null;
    try {
        const a = await api<Answer>(`/api/v1/fields/${props.fieldId}/ask`, { method: 'POST', body: JSON.stringify({ question: text }) });
        history.value = [a, ...history.value].slice(0, 6);
        question.value = '';
        await nextTick();
        list.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
        error.value = e instanceof ApiError ? e.message : t('Não foi possível consultar o assistente agora.');
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="space-y-5">
        <div class="card">
            <div class="card-head">
                <div>
                    <h2><span class="h-icon"><Icon name="message" /></span> {{ $t('Pergunte ao GeoSafra') }}</h2>
                    <p>
                        {{ $t('Respostas da IA baseadas') }} <strong>{{ $t('só nos dados deste talhão') }}</strong> {{ $t('e na metodologia do GeoSafra. Cada afirmação mostra o indicador, o período e a fonte; o que não tiver evidência é descartado.') }}
                    </p>
                </div>
                <span class="badge bg-safra-50 text-safra-800 ring-1 ring-safra-200 ring-inset"><Icon name="shield" class="h-3.5 w-3.5" /> {{ $t('Evidências verificadas') }}</span>
            </div>

            <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="ask()">
                <label for="ask-input" class="sr-only">{{ $t('Sua pergunta') }}</label>
                <input id="ask-input" v-model="question" type="text" maxlength="500" class="input flex-1" :placeholder="$t('Ex.: Qual a melhor época para plantar milho safrinha aqui?')" :disabled="loading" />
                <button type="submit" class="btn-primary" :disabled="loading || question.trim().length < 3">
                    <Icon :name="loading ? 'refresh' : 'message'" :class="loading ? 'animate-spin' : ''" /> {{ loading ? $t('Consultando…') : $t('Perguntar') }}
                </button>
            </form>
            <div class="mt-3 flex flex-wrap gap-2">
                <button v-for="s in SUGGESTIONS" :key="s" type="button" class="rounded-full bg-stone-100 px-3 py-1.5 text-xs font-medium text-stone-700 transition hover:bg-safra-50 hover:text-safra-800 disabled:opacity-50" :disabled="loading" @click="ask(s)">{{ s }}</button>
            </div>
            <p v-if="error" class="field-error mt-3">{{ error }}</p>
        </div>

        <div ref="list" class="scroll-mt-28 space-y-5">
            <article v-for="(a, i) in history" :key="`${i}-${a.question}`" class="card" :aria-label="tf('Resposta: {question}', { question: a.question })">
                <header class="mb-4 flex flex-wrap items-start justify-between gap-2 border-b border-stone-100 pb-3">
                    <p class="flex items-start gap-2 font-bold text-stone-900"><Icon name="user" class="mt-0.5 h-4 w-4 shrink-0 text-stone-400" /> {{ a.question }}</p>
                    <span v-if="a.mode === 'ai'" class="badge bg-sky-50 text-sky-800 ring-1 ring-sky-200 ring-inset">{{ $t('IA') }} {{ a.model }} {{ $t('· citações conferidas') }}</span>
                    <span v-else-if="a.mode === 'reference'" class="badge bg-violet-50 text-violet-800">{{ $t('Base de conhecimento') }}</span>
                    <span v-else class="badge bg-stone-100 text-stone-700">{{ $t('Somente evidências') }}</span>
                </header>

                <p v-if="a.notice" class="notice-warn mb-3 text-sm"><Icon name="info" />{{ a.notice }}</p>

                <ol class="space-y-4">
                    <li v-for="(c, j) in a.claims" :key="j" class="flex gap-3">
                        <span class="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-safra-100 text-xs font-bold text-safra-800 tabular-nums">{{ j + 1 }}</span>
                        <div class="min-w-0 flex-1">
                            <p class="text-stone-800">{{ c.text }}</p>
                            <ul class="mt-2 flex flex-wrap gap-1.5" :aria-label="$t('Evidências citadas')">
                                <li v-for="id in c.fact_ids" :key="id" class="inline-flex max-w-full flex-wrap items-center gap-1.5 rounded-lg border border-stone-200 bg-stone-50 px-2 py-1 text-xs text-stone-700">
                                    <template v-if="a.facts[id]">
                                        <DatasetBadge :code="a.facts[id].dataset" />
                                        <span class="font-semibold">{{ a.facts[id].label }}</span>
                                        <span class="tabular-nums">{{ fmtValue(a.facts[id]) }}</span>
                                        <span v-if="a.facts[id].period" class="text-stone-500">· {{ a.facts[id].period }}</span>
                                        <span class="text-stone-500">· {{ a.facts[id].source }}</span>
                                    </template>
                                </li>
                                <li v-for="id in c.ref_ids" :key="id">
                                    <button type="button" class="inline-flex items-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 px-2 py-1 text-xs text-violet-800 hover:bg-violet-100" :aria-expanded="openRef === `${i}:${id}`" @click="openRef = openRef === `${i}:${id}` ? null : `${i}:${id}`">
                                        <Icon name="book" class="h-3.5 w-3.5" /> {{ a.refs.find((r) => r.id === id)?.title ?? id }}
                                    </button>
                                </li>
                            </ul>
                            <template v-for="id in c.ref_ids" :key="`t-${id}`">
                                <blockquote v-if="openRef === `${i}:${id}`" :lang="a.refs.find((r) => r.id === id)?.locale" class="mt-2 rounded-lg border-l-4 border-violet-300 bg-violet-50/60 px-3 py-2 text-sm text-stone-700">
                                    <template v-if="a.mode !== 'reference'">{{ a.refs.find((r) => r.id === id)?.text }}</template>
                                    <footer class="text-xs text-stone-600">
                                        <a v-if="a.refs.find((r) => r.id === id)?.url" :href="a.refs.find((r) => r.id === id)?.url ?? undefined" target="_blank" rel="noopener noreferrer" class="font-medium underline">{{ a.refs.find((r) => r.id === id)?.source }}</a>
                                        <template v-else>{{ a.refs.find((r) => r.id === id)?.source }}</template>
                                    </footer>
                                </blockquote>
                            </template>
                        </div>
                    </li>
                </ol>
                <p v-if="!a.claims.length" class="text-sm text-stone-600">{{ $t('Não há evidência nos dados deste talhão para responder a essa pergunta com segurança.') }}</p>

                <details v-if="a.rejected.length" class="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    <summary class="cursor-pointer font-semibold">{{ tf('{count} afirmação(ões) descartada(s) por falta de respaldo', { count: a.rejected.length }) }}</summary>
                    <ul class="mt-2 list-disc space-y-1 pl-5">
                        <li v-for="(r, k) in a.rejected" :key="k"><span class="line-through opacity-70">{{ r.text }}</span> <em>({{ r.reason }})</em></li>
                    </ul>
                </details>

                <ul v-if="a.limitations.length" class="mt-4 space-y-1 border-t border-stone-100 pt-3 text-xs text-stone-500">
                    <li v-for="l in a.limitations" :key="l" class="flex gap-1.5"><Icon name="alert" class="mt-0.5 h-3.5 w-3.5 shrink-0" /> {{ l }}</li>
                </ul>
                <div v-if="a.follow_up_questions.length" class="mt-3 flex flex-wrap gap-2">
                    <button v-for="q in a.follow_up_questions" :key="q" type="button" class="rounded-full border border-safra-200 px-3 py-1 text-xs text-safra-800 hover:bg-safra-50" :disabled="loading" @click="ask(q)">{{ q }}</button>
                </div>
                <p v-if="a.mode !== 'reference'" class="mt-3 text-[11px] text-stone-400">{{ tf('Baseado em {count} evidências do talhão. Apoia, mas não substitui, o seu conhecimento e o do técnico local.', { count: a.evidence_count }) }}</p>
            </article>
        </div>
    </div>
</template>
