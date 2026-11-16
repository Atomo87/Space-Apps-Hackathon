<script setup lang="ts">
import { locale, t } from '@/lib/i18n';
import type { Polygon } from 'geojson';
import { LngLatBounds, Map as MlMap, NavigationControl, setWorkerUrl, type GeoJSONSource, type StyleSpecification } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import type { Fires, Vegetation } from '@/types/contract';
import DatasetBadge from './DatasetBadge.vue';
import Icon from './Icon.vue';

setWorkerUrl(workerUrl);

/**
 * Imagens de satélite do talhão pela NASA GIBS (pública, sem chave):
 * - cor real a 30 m do HLS (Landsat 8/9 + Sentinel-2) nas datas em que o satélite viu o talhão sem nuvem;
 * - verde (NDVI) do MODIS, composições de 16 dias dos satélites Terra e Aqua;
 * - focos de queimada da NASA FIRMS.
 */
const props = defineProps<{ latitude: number; longitude: number; boundary: Polygon | null; vegetation: Vegetation | null | undefined; fires: Fires | null }>();

const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';
const MODIS_LAYERS = {
    terra: 'MODIS_Terra_L3_NDVI_16Day',
    aqua: 'MODIS_Aqua_L3_NDVI_16Day',
};
const DAY_MS = 86_400_000;
type Layer = 'hls' | 'ndvi' | 'none';
type ModisPlatform = keyof typeof MODIS_LAYERS;
const layer = ref<Layer>(props.vegetation?.hls?.series.length ? 'hls' : props.vegetation?.series.length ? 'ndvi' : 'none');
const opacity = ref(100);
const showFires = ref(true);

/** Datas com imagem HLS sem nuvem sobre o talhão (vêm da própria análise), mais recentes primeiro. */
const hlsDates = computed(() => {
    const s = props.vegetation?.hls?.series ?? [];
    return [...new Set(s.map((p) => p.date))].reverse().slice(0, 40);
});

// Análises antigas só guardam o dia central da composição, calculado pelo catálogo STAC.
function legacyModisImage(date: string) {
    const midpoint = Date.parse(`${date}T00:00:00Z`);
    for (let offset = 8; offset >= 2; offset--) {
        const start = new Date(midpoint - offset * DAY_MS);
        const year = start.getUTCFullYear();
        const cycle = ((+start - Date.UTC(year, 0, 1)) / DAY_MS) % 16;
        if (cycle !== 0 && cycle !== 8) continue;
        const lastDay = Math.min(15, (Date.UTC(year, 11, 31) - +start) / DAY_MS);
        if (offset !== 8 && offset !== 7 && offset !== Math.floor(lastDay / 2)) continue;
        return { date: start.toISOString().slice(0, 10), platform: cycle === 0 ? 'terra' as const : 'aqua' as const };
    }
    return null;
}

const ndviImages = computed(() => {
    const images = new Map<string, ModisPlatform>();
    for (const point of props.vegetation?.series ?? []) {
        const image = point.image_date && point.platform
            ? { date: point.image_date, platform: point.platform }
            : legacyModisImage(point.date);
        if (image) images.set(image.date, image.platform);
    }
    return images;
});
const dates = computed(() => {
    if (layer.value === 'hls') return hlsDates.value;
    if (layer.value === 'ndvi') return [...ndviImages.value.keys()].sort().reverse().slice(0, 40);
    return [];
});
const date = ref<string>('');
watch(dates, (list) => {
    if (!list.includes(date.value)) date.value = list[0] ?? '';
}, { immediate: true });
const ndviPlatform = computed(() => layer.value === 'ndvi' ? ndviImages.value.get(date.value) : undefined);
const dateBr = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' });

const el = ref<HTMLDivElement | null>(null);
const map = shallowRef<MlMap | null>(null);

const style: StyleSpecification = {
    version: 8,
    sources: {
        base: {
            type: 'raster',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
            tileSize: 256,
            maxzoom: 18,
            attribution: t('Base © Esri, Maxar · Imagens NASA GIBS (HLS, MODIS) · Queimadas NASA FIRMS'),
        },
    },
    layers: [{ id: 'base', type: 'raster', source: 'base' }],
};

function gibsTiles(id: string, level: number, ext: string, d: string) {
    return [`${GIBS}/${id}/default/${d}/GoogleMapsCompatible_Level${level}/{z}/{y}/{x}.${ext}`];
}

function applyLayers() {
    const m = map.value;
    if (!m?.getLayer('field-line')) return;
    for (const id of ['hls-l30', 'hls-s30', 'ndvi']) {
        if (m.getLayer(id)) m.removeLayer(id);
        if (m.getSource(id)) m.removeSource(id);
    }
    const before = 'field-line';
    const op = opacity.value / 100;
    if (layer.value === 'hls' && date.value) {
        // Landsat (L30) e Sentinel-2 (S30): onde um não passou naquele dia, o PNG vem transparente.
        m.addSource('hls-l30', { type: 'raster', tiles: gibsTiles('HLS_L30_Nadir_BRDF_Adjusted_Reflectance', 12, 'png', date.value), tileSize: 256, maxzoom: 12 });
        m.addLayer({ id: 'hls-l30', type: 'raster', source: 'hls-l30', paint: { 'raster-opacity': op } }, before);
        m.addSource('hls-s30', { type: 'raster', tiles: gibsTiles('HLS_S30_Nadir_BRDF_Adjusted_Reflectance', 12, 'png', date.value), tileSize: 256, maxzoom: 12 });
        m.addLayer({ id: 'hls-s30', type: 'raster', source: 'hls-s30', paint: { 'raster-opacity': op } }, before);
    } else if (ndviPlatform.value) {
        m.addSource('ndvi', { type: 'raster', tiles: gibsTiles(MODIS_LAYERS[ndviPlatform.value], 9, 'png', date.value), tileSize: 256, maxzoom: 9 });
        m.addLayer({ id: 'ndvi', type: 'raster', source: 'ndvi', paint: { 'raster-opacity': op } }, before);
    }
}

function syncFires() {
    const m = map.value;
    if (!m) return;
    const pts = showFires.value ? props.fires?.points ?? [] : [];
    (m.getSource('fires') as GeoJSONSource | undefined)?.setData({
        type: 'FeatureCollection',
        features: pts.map((p) => ({ type: 'Feature', properties: { frp: p.frp ?? 1, label: `${p.satellite} · ${p.date ?? ''} · ${p.distance_km} km` }, geometry: { type: 'Point', coordinates: [p.lon, p.lat] } })),
    });
}

onMounted(() => {
    const m = new MlMap({ container: el.value!, style, center: [props.longitude, props.latitude], zoom: 13, attributionControl: { compact: true }, maxZoom: 17 });
    m.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    m.once('style.load', () => {
        m.addSource('fires', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        m.addLayer({
            id: 'fires', type: 'circle', source: 'fires',
            paint: {
                'circle-radius': ['interpolate', ['linear'], ['get', 'frp'], 0, 5, 50, 11],
                'circle-color': '#ef4444', 'circle-stroke-color': '#fff7ed', 'circle-stroke-width': 2, 'circle-opacity': 0.9,
            },
        });
        const ring = props.boundary ?? {
            type: 'Polygon',
            coordinates: [[[props.longitude - 0.002, props.latitude - 0.002], [props.longitude + 0.002, props.latitude - 0.002], [props.longitude + 0.002, props.latitude + 0.002], [props.longitude - 0.002, props.latitude + 0.002], [props.longitude - 0.002, props.latitude - 0.002]]],
        };
        m.addSource('field', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: ring as Polygon } });
        m.addLayer({ id: 'field-line', type: 'line', source: 'field', paint: { 'line-color': '#facc15', 'line-width': 3 } });
        if (props.boundary) {
            const b = new LngLatBounds();
            props.boundary.coordinates[0].forEach((c) => b.extend(c as [number, number]));
            m.fitBounds(b, { padding: 60, maxZoom: 15, duration: 0 });
        }
        applyLayers();
        syncFires();
    });
    map.value = m;
});
onBeforeUnmount(() => map.value?.remove());

watch([layer, date, ndviPlatform], applyLayers);
watch(opacity, () => {
    for (const id of ['hls-l30', 'hls-s30', 'ndvi']) if (map.value?.getLayer(id)) map.value.setPaintProperty(id, 'raster-opacity', opacity.value / 100);
});
watch([showFires, () => props.fires], syncFires);

function zoomOut() {
    map.value?.flyTo({ center: [props.longitude, props.latitude], zoom: 9 });
}
</script>

<template>
    <div class="card">
        <div class="card-head">
            <div>
                <h2><span class="h-icon"><Icon name="map" /></span> {{ $t('Imagens do talhão') }}</h2>
                <p>{{ $t('Veja o talhão pelos satélites da NASA nas datas em que passaram sem nuvem e compare a lavoura ao longo da safra.') }}</p>
            </div>
            <div class="flex flex-wrap gap-1"><DatasetBadge code="GIBS" /><DatasetBadge code="HLS" /><DatasetBadge code="FIRMS" /></div>
        </div>

        <div class="mb-3 flex flex-wrap items-end gap-3">
            <div class="tabs !mb-0" role="tablist" :aria-label="$t('Camada de satélite')">
                <button type="button" role="tab" class="tab" :aria-selected="layer === 'hls'" @click="layer = 'hls'">{{ $t('Cor real 30 m') }}</button>
                <button type="button" role="tab" class="tab" :aria-selected="layer === 'ndvi'" @click="layer = 'ndvi'">{{ $t('Verde (NDVI)') }}</button>
                <button type="button" role="tab" class="tab" :aria-selected="layer === 'none'" @click="layer = 'none'">{{ $t('Só o mapa') }}</button>
            </div>
            <label v-if="layer !== 'none'" class="block">
                <span class="mb-1 block text-xs font-semibold text-stone-600">{{ layer === 'ndvi' ? $t('Início da composição') : $t('Data da imagem') }}</span>
                <select v-model="date" class="input w-48" :disabled="!dates.length">
                    <option v-if="!dates.length" value="">{{ $t('Sem datas disponíveis') }}</option>
                    <option v-for="d in dates" :key="d" :value="d">{{ dateBr(d) }}</option>
                </select>
            </label>
            <label v-if="layer !== 'none'" class="block">
                <span class="mb-1 block text-xs font-semibold text-stone-600">{{ $t('Transparência') }}</span>
                <input v-model.number="opacity" type="range" min="20" max="100" step="5" class="w-32 accent-safra-700" :aria-label="$t('Opacidade da imagem')" />
            </label>
            <label class="inline-flex items-center gap-2 pb-2 text-sm text-stone-700">
                <input v-model="showFires" type="checkbox" class="h-4 w-4 accent-red-600" /> {{ $t('Focos de queimada') }}
            </label>
        </div>

        <div class="relative overflow-hidden rounded-2xl border border-stone-200">
            <div ref="el" class="h-80 w-full sm:h-[26rem]" />
            <button type="button" class="absolute bottom-10 left-3 inline-flex items-center gap-1.5 rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-stone-800 shadow-[var(--shadow-lift)]" @click="zoomOut">
                <Icon name="target" class="h-3.5 w-3.5" /> {{ $t('Ver a região') }}
            </button>
        </div>
        <p class="mt-2 text-xs text-stone-500">
            <template v-if="layer === 'hls'">{{ $t('HLS: Landsat 8/9 e Sentinel-2 harmonizados pela NASA, 30 m. Áreas sem cor naquela data: o satélite não passou ou havia nuvem.') }}</template>
            <template v-else-if="layer === 'ndvi'">{{ $t('NDVI do MODIS (Terra e Aqua), composição de 16 dias, 250 m: verde escuro = muita planta, amarelo ou marrom = pouca planta ou solo exposto.') }}</template>
            {{ $t('Pontos vermelhos: focos de queimada dos últimos') }} {{ fires?.days ?? 7 }} {{ $t('dias (NASA FIRMS); quanto maior, mais intenso.') }}
        </p>
    </div>
</template>
