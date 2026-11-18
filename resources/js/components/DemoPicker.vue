<script setup lang="ts">
import { router } from '@inertiajs/vue3';
import { ref } from 'vue';
import { url } from '@/lib/url';
import Icon from './Icon.vue';

export interface DemoRegion {
    key: string;
    label: string;
}

defineProps<{ regions: DemoRegion[]; current?: string | null; dark?: boolean }>();
const opening = ref<string | null>(null);

function open(region: string) {
    if (opening.value) return;
    opening.value = region;
    router.post(url('/demo'), { region }, {
        preserveState: false,
        onFinish: () => (opening.value = null),
    });
}
</script>

<template>
    <div class="flex flex-wrap gap-2" role="group" :aria-label="$t('Regiões de demonstração')">
        <button
            v-for="region in regions" :key="region.key" type="button"
            class="btn-sm" :class="dark ? 'btn-ghost' : 'btn-secondary'"
            :disabled="!!opening || current === region.key"
            :aria-current="current === region.key ? 'true' : undefined"
            :aria-busy="opening === region.key"
            @click="open(region.key)"
        >
            <Icon v-if="current === region.key" name="check" />
            {{ opening === region.key ? $t('Abrindo…') : region.label }}
        </button>
    </div>
</template>
