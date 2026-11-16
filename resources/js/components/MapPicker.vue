<script setup lang="ts">
import { t, locale } from '@/lib/i18n';
import turfArea from '@turf/area';
import turfCentroid from '@turf/centroid';
import type { Feature, Polygon } from 'geojson';
import { LngLatBounds, Map as MlMap, NavigationControl, setWorkerUrl, type GeoJSONSource, type MapMouseEvent, type StyleSpecification } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import Icon from './Icon.vue';

// Worker do MapLibre servido como arquivo próprio (funciona no Vite dev e no build).
setWorkerUrl(workerUrl);

/**
 * Seleção do talhão: toque no mapa para marcar os cantos (3 toques já formam o talhão).
 * Um único toque também serve: o POWER responde por ponto.
 */
export interface PickedField {
    latitude: number | null;
    longitude: number | null;
    boundary: Polygon | null;
    area_ha: number | null;
}

export interface MapLocation {
    latitude: number;
    longitude: number;
}

const props = defineProps<{ modelValue: PickedField; cityCenter?: MapLocation | null }>();
const emit = defineEmits<{ 'update:modelValue': [PickedField] }>();

const el = ref<HTMLDivElement | null>(null);
const map = shallowRef<MlMap | null>(null);
const points = ref<[number, number][]>(initialPoints());
const cityMarker = ref(Boolean(props.cityCenter && !props.modelValue.boundary
    && props.cityCenter.latitude === props.modelValue.latitude && props.cityCenter.longitude === props.modelValue.longitude));
const basemap = ref<'sat' | 'map'>('sat');
const locating = ref(false);
const geoError = ref<string | null>(null);

function initialPoints(): [number, number][] {
    const ring = props.modelValue.boundary?.coordinates?.[0];
    if (ring && ring.length >= 4) return ring.slice(0, -1).map((c) => [c[0], c[1]] as [number, number]);
    if (props.modelValue.latitude !== null && props.modelValue.longitude !== null) return [[props.modelValue.longitude, props.modelValue.latitude]];
    return [];
}

const style: StyleSpecification = {
    version: 8,
    sources: {
        sat: {
            type: 'raster',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
            tileSize: 256,
            maxzoom: 18,
            attribution: t('Imagens © Esri, Maxar, Earthstar Geographics'),
        },
        osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            maxzoom: 19,
            attribution: '© OpenStreetMap',
        },
    },
    layers: [
        { id: 'sat', type: 'raster', source: 'sat' },
        { id: 'osm', type: 'raster', source: 'osm', layout: { visibility: 'none' } },
    ],
};

function polygon(): Feature<Polygon> | null {
    if (points.value.length < 3) return null;
    const ring = [...points.value, points.value[0]];
    return { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [ring] } };
}

function sync() {
    const poly = polygon();
    let value: PickedField;
    if (poly) {
        const c = turfCentroid(poly).geometry.coordinates;
        value = { latitude: round(c[1]), longitude: round(c[0]), boundary: poly.geometry, area_ha: Math.round((turfArea(poly) / 10000) * 100) / 100 };
    } else if (points.value.length >= 1) {
        const [lon, lat] = points.value[points.value.length - 1];
        value = { latitude: round(lat), longitude: round(lon), boundary: null, area_ha: props.modelValue.area_ha };
    } else {
        value = { latitude: null, longitude: null, boundary: null, area_ha: null };
    }
    emit('update:modelValue', value);
    draw();
}

function round(x: number) {
    return Math.round(x * 1e6) / 1e6;
}

function draw() {
    const m = map.value;
    if (!m) return;
    const poly = polygon();
    (m.getSource('field') as GeoJSONSource | undefined)?.setData({ type: 'FeatureCollection', features: poly ? [poly] : [] });
    (m.getSource('pts') as GeoJSONSource | undefined)?.setData({
        type: 'FeatureCollection',
        features: points.value.map((p) => ({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: p } })),
    });
}

function undo() {
    cityMarker.value = false;
    points.value = points.value.slice(0, -1);
    sync();
}

function clear() {
    cityMarker.value = false;
    points.value = [];
    sync();
}

function locate() {
    if (!navigator.geolocation) {
        geoError.value = t('Seu navegador não informa a localização.');
        return;
    }
    locating.value = true;
    geoError.value = null;
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            locating.value = false;
            map.value?.flyTo({ center: [pos.coords.longitude, pos.coords.latitude], zoom: 16 });
        },
        () => {
            locating.value = false;
            geoError.value = t('Não foi possível obter o GPS. Toque no mapa para marcar.');
        },
        { enableHighAccuracy: true, timeout: 10000 },
    );
}

watch(basemap, (b) => {
    map.value?.setLayoutProperty('sat', 'visibility', b === 'sat' ? 'visible' : 'none');
    map.value?.setLayoutProperty('osm', 'visibility', b === 'map' ? 'visible' : 'none');
});

watch(() => props.cityCenter, (city) => {
    if (!city) return;
    const center: [number, number] = [city.longitude, city.latitude];
    cityMarker.value = true;
    points.value = [center];
    draw();
    map.value?.flyTo({ center, zoom: 12 });
});

onMounted(() => {
    const start = points.value[0] ?? [-48.2772, -18.9186];
    const zoom = cityMarker.value ? 12 : points.value.length ? 15 : 11;
    const m = new MlMap({ container: el.value!, style, center: start, zoom, attributionControl: { compact: true } });
    m.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    m.once('style.load', () => {
        m.addSource('field', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        m.addSource('pts', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        m.addLayer({ id: 'field-fill', type: 'fill', source: 'field', paint: { 'fill-color': '#facc15', 'fill-opacity': 0.25 } });
        m.addLayer({ id: 'field-line', type: 'line', source: 'field', paint: { 'line-color': '#facc15', 'line-width': 3 } });
        m.addLayer({ id: 'pts', type: 'circle', source: 'pts', paint: { 'circle-radius': 7, 'circle-color': '#fff', 'circle-stroke-color': '#15803d', 'circle-stroke-width': 3 } });
        draw();
        if (points.value.length >= 3) {
            const b = new LngLatBounds();
            points.value.forEach((p) => b.extend(p));
            m.fitBounds(b, { padding: 40, maxZoom: 17, duration: 0 });
        }
    });
    m.on('click', (e: MapMouseEvent) => {
        const point: [number, number] = [e.lngLat.lng, e.lngLat.lat];
        points.value = cityMarker.value ? [point] : [...points.value, point];
        cityMarker.value = false;
        sync();
    });
    map.value = m;
});

onBeforeUnmount(() => map.value?.remove());
</script>

<template>
    <div class="space-y-2">
        <div class="relative overflow-hidden rounded-2xl border border-stone-200 shadow-[var(--shadow-soft)]">
            <div ref="el" class="h-64 w-full sm:h-80 lg:h-[25rem]" />
            <div class="absolute top-3 left-3 flex gap-1.5">
                <button type="button" class="inline-flex items-center gap-1.5 rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-stone-800 shadow-[var(--shadow-lift)] backdrop-blur transition hover:bg-white" @click="basemap = basemap === 'sat' ? 'map' : 'sat'">
                    <Icon :name="basemap === 'sat' ? 'map' : 'satellite'" class="h-3.5 w-3.5" /> {{ basemap === 'sat' ? $t('Mapa') : $t('Satélite') }}
                </button>
                <button type="button" class="inline-flex items-center gap-1.5 rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-stone-800 shadow-[var(--shadow-lift)] backdrop-blur transition hover:bg-white" :disabled="locating" @click="locate">
                    <Icon name="pin" class="h-3.5 w-3.5" /> {{ locating ? 'Localizando…' : $t('Meu GPS') }}
                </button>
            </div>
            <span v-if="modelValue.area_ha && modelValue.boundary" class="absolute top-14 left-3 inline-flex items-center gap-1.5 rounded-lg bg-safra-950/85 px-3 py-1.5 text-sm font-bold text-lime-300 shadow-[var(--shadow-lift)] backdrop-blur tabular-nums">
                <Icon name="grid" class="h-3.5 w-3.5" /> {{ modelValue.area_ha.toLocaleString(locale) }} ha
            </span>
        </div>
        <p class="flex items-start gap-2 text-sm text-stone-600">
            <Icon name="info" class="mt-0.5 h-4 w-4 shrink-0 text-safra-700" />
            <span v-if="cityMarker">{{ $t('O ponto inicial é o centro do município. Clique no mapa para marcar a localização do talhão.') }}</span>
            <span v-else>{{ $t('Toque nos') }} <strong>{{ $t('cantos do talhão') }}</strong> {{ $t('(3 toques já formam a área). Se preferir, um toque só marca o ponto.') }}</span>
        </p>
        <p v-if="geoError" class="field-error">{{ geoError }}</p>
        <div class="flex flex-wrap items-center gap-2 text-sm">
            <button type="button" class="btn-secondary btn-sm" :disabled="!points.length" @click="undo"><Icon name="arrowLeft" /> {{ $t('Desfazer') }}</button>
            <button type="button" class="btn-secondary btn-sm" :disabled="!points.length" @click="clear"><Icon name="trash" /> {{ $t('Limpar') }}</button>
            <span v-if="modelValue.latitude !== null" class="badge ml-auto bg-stone-100 text-stone-600 tabular-nums">
                <Icon name="target" class="h-3.5 w-3.5" /> {{ modelValue.latitude?.toFixed(4) }}, {{ modelValue.longitude?.toFixed(4) }}
            </span>
        </div>
    </div>
</template>
