<script setup lang="ts">
import { tf } from '@/lib/i18n';
import { usePage } from '@inertiajs/vue3';
import { computed, ref } from 'vue';
import type { SharedProps } from '@/types/global';

/** Termo técnico com "?" que abre a explicação do glossário (RNF02). */
const props = defineProps<{ k: string; label?: string }>();
const page = usePage<SharedProps>();
const entry = computed(() => page.props.glossary?.[props.k]);
const open = ref(false);
</script>

<template>
    <span class="relative inline-flex items-baseline gap-1">
        <span>{{ label ?? entry?.term ?? k }}</span>
        <button
            v-if="entry"
            type="button"
            class="inline-flex h-5 w-5 items-center justify-center rounded-full bg-stone-200 text-xs font-bold text-stone-700 hover:bg-stone-300"
            :aria-label="tf('O que é {term}?', { term: entry.term })"
            :aria-expanded="open"
            @click.stop="open = !open"
        >?</button>
        <span
            v-if="open && entry"
            class="absolute top-6 left-0 z-40 w-72 rounded-xl border border-stone-200 bg-white p-3 text-left text-sm font-normal text-stone-700 shadow-lg"
            role="tooltip"
            @click.stop="open = false"
        >
            <strong class="block text-stone-900">{{ entry.term }}</strong>
            {{ entry.text }}
        </span>
    </span>
</template>
