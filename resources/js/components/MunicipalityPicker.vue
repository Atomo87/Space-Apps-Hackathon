<script setup lang="ts">
import { computed, ref, shallowRef, useId } from 'vue';
import catalogUrl from '@/data/municipalities-br.json?url';
import { indexMunicipalities, normalizeMunicipality, searchMunicipalities, type Municipality, type MunicipalityCatalog } from '@/lib/municipalities';

const model = defineModel<string>({ required: true });
const props = defineProps<{ state: string | null }>();
const emit = defineEmits<{ select: [Municipality] }>();

const inputId = useId();
const listId = `${inputId}-options`;
const catalog = shallowRef<Municipality[] | null>(null);
const open = ref(false);
const loading = ref(false);
const failed = ref(false);
const active = ref(-1);
const panelVisible = computed(() => open.value && normalizeMunicipality(model.value).length >= 2);
const suggestions = computed(() => panelVisible.value && catalog.value ? searchMunicipalities(catalog.value, model.value, props.state) : []);

async function loadSuggestions() {
    if (!panelVisible.value || loading.value || catalog.value) return;
    failed.value = false;
    loading.value = true;
    try {
        const response = await fetch(catalogUrl);
        if (!response.ok) throw new Error('Municipality catalog unavailable.');
        catalog.value = indexMunicipalities(await response.json() as MunicipalityCatalog);
    } catch {
        failed.value = true;
    } finally {
        loading.value = false;
    }
}

function show() {
    active.value = -1;
    open.value = true;
    void loadSuggestions();
}

function close() {
    open.value = false;
    active.value = -1;
}

function input(event: Event) {
    model.value = (event.target as HTMLInputElement).value;
    show();
}

function select(city: Municipality) {
    close();
    emit('select', city);
}

function optionId(index: number) {
    return `${listId}-${index}`;
}

function navigate(event: KeyboardEvent) {
    if (event.key === 'Escape' && panelVisible.value) {
        event.preventDefault();
        close();
        return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        if (!open.value) show();
        const count = suggestions.value.length;
        if (!count) return;
        event.preventDefault();
        active.value = active.value < 0
            ? (event.key === 'ArrowDown' ? 0 : count - 1)
            : (active.value + (event.key === 'ArrowDown' ? 1 : -1) + count) % count;
        return;
    }
    const city = suggestions.value[active.value];
    if (event.key === 'Enter' && city) {
        event.preventDefault();
        select(city);
    }
}
</script>

<template>
    <div class="relative">
        <label :for="inputId" class="label">{{ $t('Município') }}</label>
        <input
            :id="inputId"
            :value="model"
            role="combobox"
            aria-autocomplete="list"
            :aria-expanded="suggestions.length > 0"
            :aria-controls="suggestions.length ? listId : undefined"
            :aria-activedescendant="suggestions[active] ? optionId(active) : undefined"
            autocomplete="off"
            class="input"
            :placeholder="$t('Ex.: Uberlândia')"
            @focus="show"
            @blur="close"
            @input="input"
            @keydown="navigate"
        />
        <div v-if="panelVisible" class="absolute inset-x-0 top-full z-20 mt-1 rounded-xl border border-stone-200 bg-white shadow-[var(--shadow-lift)]">
            <ul v-if="suggestions.length" :id="listId" role="listbox" :aria-label="$t('Municípios sugeridos')" class="py-1">
                <li
                    v-for="(city, index) in suggestions"
                    :id="optionId(index)"
                    :key="city.id"
                    role="option"
                    :aria-selected="active === index"
                    class="flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-safra-50"
                    :class="active === index ? 'bg-safra-100 text-safra-900' : 'text-stone-700'"
                    @mousedown.prevent
                    @click="select(city)"
                >
                    <span>{{ city.name }}</span>
                    <span class="shrink-0 text-xs font-semibold text-stone-500">{{ city.state }}</span>
                </li>
            </ul>
            <p v-else class="px-3 py-2 text-sm text-stone-600" role="status">
                {{ loading ? $t('Carregando municípios…') : failed ? $t('Sugestões indisponíveis. Digite o município e marque o mapa.') : $t('Nenhum município encontrado.') }}
            </p>
        </div>
    </div>
</template>
