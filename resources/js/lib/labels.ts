import { t, locale } from './i18n';
import type { IconName } from '@/components/Icon.vue';
import type { CriterionKey, PriorityKey } from '@/types/contract';

const monthFormatter = new Intl.DateTimeFormat(locale, { month: 'short', timeZone: 'UTC' });

export const MONTHS = Array.from({ length: 12 }, (_, index) => monthFormatter.format(Date.UTC(2000, index, 1)).toLowerCase().replace(/\.$/, ''));

export function monthName(month: number): string {
    return MONTHS[month - 1] ?? '';
}

/** Ícone (componente Icon) de cada critério do motor. */
export const CRITERIA_ICONS: Record<CriterionKey, IconName> = {
    save_water: 'droplet',
    soil_structure: 'layers',
    n_fixation: 'leaf',
    erosion_control: 'mountain',
    organic_matter: 'sprout',
    pest_break: 'shield',
    forage: 'tractor',
    extra_income: 'chart',
    market_fit: 'target',
    climate_risk: 'sun',
};

export const PRIORITIES: { key: PriorityKey; label: string; icon: IconName; help: string; glossary?: string }[] = [
    { key: 'save_water', label: t('Economizar água'), icon: CRITERIA_ICONS.save_water, help: t('Culturas que passam melhor por veranicos e secas'), glossary: 'balanco' },
    { key: 'soil_structure', label: t('Melhorar a estrutura do solo'), icon: CRITERIA_ICONS.soil_structure, help: t('Raízes que soltam o solo e ajudam a água a infiltrar'), glossary: 'raiz' },
    { key: 'n_fixation', label: t('Deixar nitrogênio no solo'), icon: CRITERIA_ICONS.n_fixation, help: t('Leguminosas que economizam adubo na próxima safra'), glossary: 'fixacao' },
    { key: 'erosion_control', label: t('Segurar a erosão'), icon: CRITERIA_ICONS.erosion_control, help: t('Solo coberto quando vêm as chuvas fortes'), glossary: 'erosao' },
    { key: 'organic_matter', label: t('Aumentar a matéria orgânica'), icon: CRITERIA_ICONS.organic_matter, help: t('Mais palhada voltando para o solo'), glossary: 'cn' },
    { key: 'pest_break', label: t('Quebrar pragas e doenças'), icon: CRITERIA_ICONS.pest_break, help: t('Culturas que a praga não consegue usar'), glossary: 'quebra_pragas' },
    { key: 'forage', label: t('Ter forragem para o gado'), icon: CRITERIA_ICONS.forage, help: t('Pasto ou palhada para a entressafra seca') },
    { key: 'extra_income', label: t('Ter uma renda a mais'), icon: CRITERIA_ICONS.extra_income, help: t('Uma segunda safra que dá para vender') },
    { key: 'market_fit', label: t('Plantar o que tem comprador'), icon: CRITERIA_ICONS.market_fit, help: t('Culturas com mercado na sua região') },
];

export const PURPOSE_LABEL: Record<string, string> = {
    cash: t('venda'),
    cover: t('cobertura'),
    forage: t('forragem'),
    green_manure: t('adubo verde'),
};

export const PURPOSE_COLOR: Record<string, string> = {
    cash: 'bg-amber-400',
    cover: 'bg-lime-500',
    forage: 'bg-emerald-600',
    green_manure: 'bg-teal-500',
};

export function scoreColor(score: number): string {
    if (score >= 70) return 'text-safra-700';
    if (score >= 50) return 'text-amber-600';
    return 'text-red-600';
}

export function fmt(n: number | null | undefined, digits = 0, unit = ''): string {
    if (n === null || n === undefined || Number.isNaN(n)) return '—';
    return n.toLocaleString(locale, { maximumFractionDigits: digits, minimumFractionDigits: digits }) + unit;
}
