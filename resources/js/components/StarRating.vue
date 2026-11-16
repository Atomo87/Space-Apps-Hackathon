<script setup lang="ts">
import { tf } from '@/lib/i18n';
const props = defineProps<{ modelValue: number; label: string }>();
const emit = defineEmits<{ 'update:modelValue': [number] }>();

function set(n: number) {
    emit('update:modelValue', props.modelValue === n ? 0 : n);
}
</script>

<template>
    <div class="flex items-center gap-0.5" role="radiogroup" :aria-label="label">
        <button
            v-for="n in 5"
            :key="n"
            type="button"
            role="radio"
            :aria-checked="modelValue === n"
            :aria-label="tf('{n} de 5', { n })"
            class="p-1 text-2xl leading-none transition"
            :class="n <= modelValue ? 'text-amber-500' : 'text-stone-300 hover:text-amber-300'"
            @click="set(n)"
        >★</button>
        <span class="ml-1 w-14 text-xs text-stone-500">{{ [$t('não importa'), $t('pouco'), $t('algo'), $t('médio', 'StarRating'), $t('muito'), $t('essencial')][modelValue] }}</span>
    </div>
</template>
