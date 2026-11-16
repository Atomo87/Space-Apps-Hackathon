<script setup lang="ts">
import { t } from '@/lib/i18n';
import { Head, Link, router } from '@inertiajs/vue3';
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import FieldGrid, { type FieldRow } from '@/components/FieldGrid.vue';
import Icon from '@/components/Icon.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { fmt } from '@/lib/labels';

/** Tela "Meus talhões": todos os talhões cadastrados, com busca e filtro por situação. */
const props = defineProps<{ fields: FieldRow[]; stats: { fields: number; area_ha: number; ready: number } }>();

const query = ref('');
const status = ref<'all' | 'ready' | 'processing' | 'error'>('all');
const FILTERS = [
    { k: 'all', l: t('Todos') },
    { k: 'ready', l: t('Análise pronta') },
    { k: 'processing', l: t('Processando') },
    { k: 'error', l: t('Com erro') },
] as const;

const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const shown = computed(() =>
    props.fields.filter((f) => {
        const okStatus = status.value === 'all' || (status.value === 'processing' ? ['processing', 'pending'].includes(f.status) : f.status === status.value);
        const q = norm(query.value.trim());
        return okStatus && (!q || norm(`${f.name} ${f.farm} ${f.municipality ?? ''} ${f.state ?? ''}`).includes(q));
    }),
);

// Enquanto algum talhão processa em segundo plano, a lista se atualiza sozinha.
const anyProcessing = computed(() => props.fields.some((f) => f.status === 'processing'));
let refresh: ReturnType<typeof setInterval> | undefined;
watch(
    anyProcessing,
    (on) => {
        clearInterval(refresh);
        if (on) refresh = setInterval(() => router.reload({ only: ['fields', 'stats'] }), 8000);
    },
    { immediate: true },
);
onBeforeUnmount(() => clearInterval(refresh));
</script>

<template>
    <Head :title="$t('Meus talhões')" />
    <AppLayout :title="$t('Meus talhões')">
        <header class="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
                <h1 class="flex items-center gap-2.5 text-2xl font-extrabold tracking-tight text-stone-900 sm:text-[1.75rem]">
                    <span class="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-safra-700 to-safra-950 text-lime-300"><Icon name="map" class="h-5 w-5" /></span>
                    {{ $t('Meus talhões') }}
                </h1>
                <p class="mt-1.5 text-sm text-stone-600 tabular-nums">{{ stats.fields }} {{ $t('talhões ·') }} {{ fmt(stats.area_ha, 1) }} ha · {{ stats.ready }} {{ $t('análises prontas') }}</p>
            </div>
            <Link :href="$url('/talhoes/novo')" class="btn-primary"><Icon name="plus" /> {{ $t('Novo talhão') }}</Link>
        </header>

        <div v-if="fields.length" class="mb-5 flex flex-wrap items-center gap-3">
            <label class="relative min-w-[16rem] flex-1">
                <span class="sr-only">{{ $t('Buscar talhão') }}</span>
                <Icon name="target" class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-stone-400" />
                <input v-model="query" type="search" class="input w-full pl-9" :placeholder="$t('Buscar por talhão, fazenda ou município')" />
            </label>
            <div class="tabs !mb-0" role="tablist" :aria-label="$t('Filtrar por situação')">
                <button v-for="f in FILTERS" :key="f.k" type="button" role="tab" class="tab" :aria-selected="status === f.k" @click="status = f.k">{{ f.l }}</button>
            </div>
        </div>

        <FieldGrid v-if="shown.length" :fields="shown" :show-add="!query && status === 'all'" />

        <div v-else-if="fields.length" class="card py-10 text-center text-sm text-stone-600">
            {{ $t('Nenhum talhão encontrado com esse filtro.') }}
            <button type="button" class="ml-1 font-semibold text-safra-700 underline" @click="(query = ''), (status = 'all')">{{ $t('Limpar filtros') }}</button>
        </div>

        <section v-else class="card flex flex-col items-center gap-4 px-6 py-14 text-center">
            <span class="icon-tile-good h-14 w-14 rounded-2xl"><Icon name="sprout" class="!h-7 !w-7" /></span>
            <div>
                <h2 class="text-xl font-extrabold tracking-tight">{{ $t('Nenhum talhão ainda') }}</h2>
                <p class="mx-auto mt-1.5 max-w-md text-sm text-stone-600">{{ $t('Desenhe o talhão no mapa, informe o que plantou e suas prioridades. Buscamos os dados da NASA e comparamos rotações.') }}</p>
            </div>
            <Link :href="$url('/talhoes/novo')" class="btn-primary"><Icon name="plus" /> {{ $t('Cadastrar meu primeiro talhão') }}</Link>
        </section>
    </AppLayout>
</template>
