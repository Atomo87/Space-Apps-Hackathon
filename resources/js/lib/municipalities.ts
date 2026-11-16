export interface Municipality {
    id: number;
    name: string;
    state: string;
    latitude: number;
    longitude: number;
    searchName: string;
}

export interface MunicipalityCatalog {
    municipalities: [number, string, string, number, number][];
}

const states = new Set('ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to'.split(' '));
const names = new Intl.Collator('pt-BR');

export function normalizeMunicipality(value: string): string {
    return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

export function indexMunicipalities(catalog: MunicipalityCatalog): Municipality[] {
    return catalog.municipalities.map(([id, name, state, latitude, longitude]) => ({
        id, name, state, latitude, longitude, searchName: normalizeMunicipality(name),
    }));
}

export function searchMunicipalities(municipalities: Municipality[], query: string, preferredState: string | null): Municipality[] {
    const words = normalizeMunicipality(query).split(' ');
    const last = words.at(-1);
    const state = words.length > 1 && last && states.has(last) ? words.pop()?.toUpperCase() : undefined;
    const name = words.join(' ');
    if (name.length < 2) return [];

    const matches: { city: Municipality; rank: number }[] = [];
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
