<script setup lang="ts">
import { computed } from 'vue';

/** Selo de fonte de dados com cor fixa por conjunto — o mesmo dataset tem a mesma cor em toda a interface. */
const props = defineProps<{ code: string }>();

const TONES: [RegExp, string][] = [
    [/^POWER/, 'bg-sky-50 text-sky-800 ring-sky-200'],
    [/^SRTM/, 'bg-stone-100 text-stone-700 ring-stone-300'],
    [/^HLS/, 'bg-emerald-50 text-emerald-800 ring-emerald-200'],
    [/LST/, 'bg-orange-50 text-orange-800 ring-orange-200'],
    [/ET$/, 'bg-teal-50 text-teal-800 ring-teal-200'],
    [/^MODIS/, 'bg-lime-50 text-lime-800 ring-lime-200'],
    [/Histórico/, 'bg-violet-50 text-violet-800 ring-violet-200'],
    [/^SMAP/, 'bg-amber-50 text-amber-800 ring-amber-200'],
    [/^GPM/, 'bg-blue-50 text-blue-800 ring-blue-200'],
    [/^ECOSTRESS/, 'bg-rose-50 text-rose-800 ring-rose-200'],
    [/^GRACE/, 'bg-indigo-50 text-indigo-800 ring-indigo-200'],
    [/^FIRMS/, 'bg-red-50 text-red-800 ring-red-200'],
    [/^GIBS/, 'bg-cyan-50 text-cyan-800 ring-cyan-200'],
];
const tone = computed(() => TONES.find(([re]) => re.test(props.code))?.[1] ?? 'bg-stone-50 text-stone-600 ring-stone-200');
</script>

<template>
    <span class="inline-flex items-center rounded-md px-1.5 py-0.5 text-[10.5px] font-semibold tracking-wide whitespace-nowrap ring-1 ring-inset" :class="tone">{{ code }}</span>
</template>
