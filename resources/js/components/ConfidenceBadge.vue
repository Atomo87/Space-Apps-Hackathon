<script setup lang="ts">
import { t } from '@/lib/i18n';
import { computed } from 'vue';
import type { ConfidenceLevel } from '@/types/contract';
import Term from './Term.vue';

const props = defineProps<{ level: ConfidenceLevel; value?: number }>();
const style = computed(
    () =>
        ({
            alta: 'bg-safra-100 text-safra-900',
            media: 'bg-amber-100 text-amber-900',
            baixa: 'bg-red-100 text-red-900',
        })[props.level],
);
const text = computed(() => ({ alta: t('Alta'), media: t('Média', 'ConfidenceBadge'), baixa: t('Baixa') })[props.level]);
</script>

<template>
    <span :class="['inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold', style]">
        <Term k="confianca" :label="`Confiança ${text}`" />
        <span v-if="value !== undefined" class="font-normal opacity-70">({{ Math.round(value * 100) }}%)</span>
    </span>
</template>
