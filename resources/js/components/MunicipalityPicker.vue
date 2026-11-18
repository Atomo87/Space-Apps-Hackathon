<script setup lang="ts">
import { computed, nextTick, ref, shallowRef, useId, watch } from 'vue';
import catalogUrl from '@/data/municipalities-br.json?url';
import { countryName, locale } from '@/lib/i18n';
import { indexMunicipalities, normalizeMunicipality, parseCityQuery, searchInternationalCities, searchMunicipalities, type Municipality, type MunicipalityCatalog } from '@/lib/municipalities';

const model = defineModel<string>({ required: true });
const props = defineProps<{ state: string | null }>();
const emit = defineEmits<{ select: [Municipality] }>();

const inputId = useId();
const listId = `${inputId}-options`;
const catalog = shallowRef<ReturnType<typeof indexMunicipalities> | null>(null);
const international = shallowRef<Municipality[]>([]);
const open = ref(false);
const loading = ref(false);
const failed = ref(false);
const internationalLoading = ref(false);
const internationalFailed = ref(false);
const active = ref(-1);
const panelVisible = computed(() => open.value && normalizeMunicipality(model.value).length >= 2);
const query = computed(() => parseCityQuery(model.value));
const suggestions = computed(() => {
    if (!panelVisible.value) return [];
    const { name, countryCode } = query.value;
    const local = catalog.value && (!countryCode || countryCode === 'BR')
        ? searchMunicipalities(catalog.value, name, props.state) : [];
    const normalizedName = normalizeMunicipality(name);
    return [...local, ...international.value].sort((a, b) =>
        Number(normalizeMunicipality(b.name) === normalizedName) - Number(normalizeMunicipality(a.name) === normalizedName));
});

watch([open, model], ([isOpen, value], _, onCleanup) => {
    international.value = [];
    internationalLoading.value = false;
    internationalFailed.value = false;
    const { name, countryCode } = parseCityQuery(value);
    if (!isOpen || countryCode === 'BR' || normalizeMunicipality(name.split(',')[0]).length < 2) return;

    internationalLoading.value = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
        try {
            const results = await searchInternationalCities(value, locale.slice(0, 2), controller.signal);
            if (!controller.signal.aborted) international.value = results;
        } catch {
            if (!controller.signal.aborted) internationalFailed.value = true;
        } finally {
            if (!controller.signal.aborted) internationalLoading.value = false;
        }
    }, 350);

    onCleanup(() => {
        window.clearTimeout(timeout);
        controller.abort();
    });
}, { flush: 'sync' });

watch(suggestions, () => { active.value = -1; }, { flush: 'sync' });

async function loadSuggestions() {
    if (!panelVisible.value || (query.value.countryCode && query.value.countryCode !== 'BR') || loading.value || catalog.value) return;
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

watch([panelVisible, model], () => { void loadSuggestions(); });

function show() {
    active.value = -1;
    open.value = true;
}

function close() {
    open.value = false;
    active.value = -1;
}

function closeWhenLeaving(event: FocusEvent) {
    if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) close();
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
        void nextTick(() => document.getElementById(optionId(active.value))?.scrollIntoView({ block: 'nearest' }));
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
    <div class="relative" @focusout="closeWhenLeaving">
        <label :for="inputId" class="label">{{ $t('Município ou cidade') }}</label>
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
            placeholder="Lubbock TX - US"
            @focus="show"
            @input="input"
            @keydown="navigate"
        />
        <div v-if="panelVisible" class="absolute inset-x-0 top-full z-20 mt-1 rounded-xl border border-stone-200 bg-white shadow-[var(--shadow-lift)]">
            <ul v-if="suggestions.length" :id="listId" role="listbox" :aria-label="$t('Cidades sugeridas')" class="max-h-60 overflow-y-auto py-1">
                <li
                    v-for="(city, index) in suggestions"
                    :id="optionId(index)"
                    :key="`${city.countryCode}-${city.id}`"
                    role="option"
                    :aria-selected="active === index"
                    class="cursor-pointer px-3 py-2 text-sm hover:bg-safra-50"
                    :class="active === index ? 'bg-safra-100 text-safra-900' : 'text-stone-700'"
                    :title="[city.state, countryName(city.countryCode)].filter(Boolean).join(' · ')"
                    @mousedown.prevent
                    @click="select(city)"
                >
                    {{ [city.name, city.stateCode ?? city.state].filter(Boolean).join(' ') }} - {{ city.countryCode }}
                </li>
            </ul>
            <p v-if="loading || internationalLoading" class="px-3 py-2 text-sm text-stone-600" role="status">{{ $t('Buscando cidades…') }}</p>
            <p v-else-if="!suggestions.length" class="px-3 py-2 text-sm text-stone-600" role="status">
                {{ failed || internationalFailed ? $t('Sugestões indisponíveis. Digite a cidade e marque o mapa.') : $t('Nenhuma cidade encontrada.') }}
            </p>
            <p v-else-if="internationalFailed" class="px-3 py-2 text-xs text-stone-600" role="status">{{ $t('A busca internacional está indisponível.') }}</p>
            <p v-if="international.length" class="border-t border-stone-100 px-3 py-2 text-xs text-stone-600">
                <a href="https://open-meteo.com/en/docs/geocoding-api" target="_blank" rel="noopener noreferrer" class="underline">Open-Meteo</a> /
                <a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer" class="underline">GeoNames</a>
            </p>
        </div>
    </div>
</template>
