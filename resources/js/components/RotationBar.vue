<script setup lang="ts">
import { MONTHS, PURPOSE_COLOR, PURPOSE_LABEL } from '@/lib/labels';
import type { Strategy } from '@/types/contract';

/** Linha do tempo de 12 meses (out → set, o ano-safra) com culturas e cobertura. */
const props = defineProps<{ strategy: Pick<Strategy, 'steps' | 'cover_by_month'> }>();
const order = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9];

function at(m: number) {
    return props.strategy.steps.filter((s) => s.months.includes(m));
}
function cover(m: number) {
    return props.strategy.cover_by_month.find((c) => c.month === m);
}
</script>

<template>
    <div>
        <div class="grid grid-cols-12 gap-px overflow-hidden rounded-lg text-[10px]">
            <div v-for="m in order" :key="m" class="flex h-9 flex-col justify-end" :title="`${MONTHS[m - 1]}: ${at(m).map((s) => s.crop_names.map((crop) => $t(crop)).join(' + ')).join(' / ') || cover(m)?.kind}`">
                <div
                    v-if="at(m).length"
                    :class="['flex-1', PURPOSE_COLOR[at(m)[at(m).length - 1].purpose]]"
                    class="flex items-center justify-center overflow-hidden px-0.5 font-semibold text-white"
                >
                    {{ $t(at(m)[at(m).length - 1].crop_names[0]).slice(0, 4) }}
                </div>
                <div v-else-if="(cover(m)?.factor ?? 0) > 0" class="flex-1 bg-[repeating-linear-gradient(45deg,#d6d3d1,#d6d3d1_3px,#f5f5f4_3px,#f5f5f4_6px)]" />
                <div v-else class="flex-1 bg-orange-100" />
            </div>
        </div>
        <div class="grid grid-cols-12 text-center text-[10px] text-stone-500 uppercase">
            <span v-for="m in order" :key="m">{{ MONTHS[m - 1] }}</span>
        </div>
        <ul class="mt-1 space-y-0.5 text-xs text-stone-700">
            <li v-for="(s, i) in strategy.steps" :key="i">
                <span :class="['mr-1 inline-block h-2 w-2 rounded-full', PURPOSE_COLOR[s.purpose]]" />
                <strong>{{ s.crop_names.map((crop) => $t(crop)).join(' + ') }}</strong> · {{ $t(s.label) }} · {{ PURPOSE_LABEL[s.purpose] }}
            </li>
        </ul>
    </div>
</template>
