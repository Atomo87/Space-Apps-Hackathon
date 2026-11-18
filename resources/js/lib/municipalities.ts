import subdivisionData from '@/data/subdivisions.json';

export interface Municipality {
    id: number;
    name: string;
    state: string | null;
    stateCode: string | null;
    countryCode: string;
    latitude: number;
    longitude: number;
}

type BrazilianMunicipality = Municipality & { state: string; searchName: string };

export interface MunicipalityCatalog {
    municipalities: [number, string, string, number, number][];
}

const states = new Set('ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to'.split(' '));
const names = new Intl.Collator('pt-BR');
const subdivisionCodes: Record<string, string> = subdivisionData.codes;
const knownSubdivisions = new Set(Object.values(subdivisionCodes));

export function parseCityQuery(query: string): { name: string; countryCode?: string } {
    const qualified = query.trim().match(/^(.+?)\s+-\s+([a-z]{2})$/i);
    return qualified ? { name: qualified[1], countryCode: qualified[2].toUpperCase() } : { name: query.trim() };
}

export function normalizeMunicipality(value: string): string {
    return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

export function indexMunicipalities(catalog: MunicipalityCatalog): BrazilianMunicipality[] {
    return catalog.municipalities.map(([id, name, state, latitude, longitude]) => ({
        id, name, state, stateCode: state, countryCode: 'BR', latitude, longitude, searchName: normalizeMunicipality(name),
    }));
}

export function searchMunicipalities(municipalities: BrazilianMunicipality[], query: string, preferredState: string | null): Municipality[] {
    const words = normalizeMunicipality(query).split(' ');
    const last = words.at(-1);
    const state = words.length > 1 && last && states.has(last) ? words.pop()?.toUpperCase() : undefined;
    const name = words.join(' ');
    if (name.length < 2) return [];

    const matches: { city: BrazilianMunicipality; rank: number }[] = [];
    for (const city of municipalities) {
        if (state && city.state !== state) continue;
        const start = city.searchName.indexOf(name);
        if (start < 0) continue;
        const rank = city.searchName === name ? 0 : start === 0 ? 1 : city.searchName[start - 1] === ' ' ? 2 : 3;
        matches.push({ city, rank });
    }

    const preferred = preferredState?.trim().toUpperCase();
    matches.sort((a, b) => a.rank - b.rank
        || Number(b.city.state === preferred) - Number(a.city.state === preferred)
        || names.compare(a.city.name, b.city.name)
        || a.city.state.localeCompare(b.city.state));

    return matches.slice(0, 8).map(({ city }) => city);
}

interface GeocodingResult {
    id: number;
    name: string;
    admin1?: string;
    admin1_id?: number;
    country_code?: string;
    feature_code?: string;
    latitude: number;
    longitude: number;
}

export async function searchInternationalCities(query: string, language: string, signal: AbortSignal): Promise<Municipality[]> {
    const { name, countryCode } = parseCityQuery(query);
    if (countryCode === 'BR') return [];

    const params = new URLSearchParams({ name, language, count: '25' });
    if (countryCode) {
        params.set('countryCode', countryCode);
        const stateSuffix = name.match(/^(.+?)\s+([a-z0-9]{1,3})$/i);
        if (stateSuffix && knownSubdivisions.has(`${countryCode}-${stateSuffix[2].toUpperCase()}`)) {
            params.set('name', `${stateSuffix[1]}, ${stateSuffix[2].toUpperCase()}`);
        }
    }
    const response = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`, {
        signal: AbortSignal.any([signal, AbortSignal.timeout(6000)]),
    });
    if (!response.ok) throw new Error('International city search unavailable.');

    const { results = [] } = await response.json() as { results?: GeocodingResult[] };
    return results.filter((place): place is GeocodingResult & { country_code: string } =>
        !!place.country_code && place.country_code !== 'BR' && !!place.feature_code?.startsWith('PPL'))
        .slice(0, 8)
        .map((place) => {
            const subdivision = subdivisionCodes[String(place.admin1_id)];
            return {
                id: place.id,
                name: place.name,
                state: place.admin1 || null,
                stateCode: subdivision?.startsWith(`${place.country_code}-`) ? subdivision.slice(3) : null,
                countryCode: place.country_code,
                latitude: place.latitude,
                longitude: place.longitude,
            };
        });
}
