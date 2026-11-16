<script setup lang="ts">
import { t } from '@/lib/i18n';
import { computed } from 'vue';
import { VChart } from '@/lib/echarts';
import type { Strategy } from '@/types/contract';

const props = defineProps<{ strategies: Strategy[] }>();
const colors = ['#78716c', '#15803d', '#2563eb', '#d97706'];
const option = computed(() => {
    const first = props.strategies[0];
    return {
        tooltip: {},
        legend: { bottom: 0, data: props.strategies.map((s) => s.label), textStyle: { fontSize: 11 } },
        radar: {
            radius: '62%',
            indicator: first.criteria.map((c) => ({ name: c.label.replace(' (palhada)', '').replace(t(' e doenças'), ''), max: 100 })),
            axisName: { fontSize: 10, color: '#57534e' },
        },
        series: [
            {
                type: 'radar',
                data: props.strategies.map((s, i) => ({
                    name: s.label,
                    value: s.criteria.map((c) => c.score),
                    lineStyle: { color: colors[i % colors.length], width: s.is_current ? 1 : 2, type: s.is_current ? 'dashed' : 'solid' },
                    itemStyle: { color: colors[i % colors.length] },
                    areaStyle: { opacity: s.is_current ? 0 : 0.06 },
                })),
            },
        ],
    };
});
</script>

<template>
    <VChart :option="option" autoresize class="h-80" />
</template>
