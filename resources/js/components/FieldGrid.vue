<script setup lang="ts">
import { countryName, t, locale, tf } from '@/lib/i18n';
import { Link } from '@inertiajs/vue3';
import { fmt } from '@/lib/labels';
import Icon, { type IconName } from './Icon.vue';

/** Grade de cartões de talhão (início e tela "Meus talhões"). */
export interface FieldRow {
    id: number;
    name: string;
    farm: string;
    municipality: string | null;
    state: string | null;
    country_code: string;
    area_ha: number | null;
    status: string;
    analyzed_at: string | null;
    is_demo: boolean;
}

defineProps<{ fields: FieldRow[]; showAdd?: boolean }>();

const statusInfo: Record<string, { label: string; cls: string; icon: IconName }> = {
    pending: { label: t('Aguardando dados'), cls: 'bg-stone-100 text-stone-700', icon: 'clock' },
    processing: { label: t('Processando em segundo plano'), cls: 'bg-sky-100 text-sky-800', icon: 'refresh' },
    ready: { label: t('Análise pronta'), cls: 'bg-safra-100 text-safra-800', icon: 'check' },
    error: { label: t('Erro — tentar de novo'), cls: 'bg-red-100 text-red-800', icon: 'alert' },
};

function since(iso: string | null): string {
    if (!iso) return t('ainda não analisado');
    return tf('analisado em {date}', { date: new Date(iso).toLocaleDateString(locale, { day: '2-digit', month: 'short', year: 'numeric' }) });
}
</script>

<template>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link v-for="f in fields" :key="f.id" :href="$url(`/talhoes/${f.id}`)" class="card card-hover card-accent group flex flex-col gap-4">
            <div class="flex items-start justify-between gap-3">
                <span class="icon-tile-good"><Icon name="sprout" /></span>
                <span class="badge" :class="statusInfo[f.status]?.cls ?? 'bg-stone-100'"><Icon :name="statusInfo[f.status]?.icon ?? 'info'" class="h-3.5 w-3.5" /> {{ statusInfo[f.status]?.label ?? f.status }}</span>
            </div>
            <div class="min-w-0">
                <h3 class="card-title flex items-center gap-2 truncate">
                    {{ f.name }}
                    <span v-if="f.is_demo" class="badge bg-amber-100 text-[10px] text-amber-800 uppercase">{{ $t('exemplo') }}</span>
                </h3>
                <p class="mt-0.5 truncate text-sm text-stone-500">{{ f.farm }}</p>
            </div>
            <div class="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-stone-100 pt-3 text-xs text-stone-500">
                <span v-if="f.municipality" class="inline-flex items-center gap-1">
                    <Icon name="pin" class="h-3.5 w-3.5 shrink-0" />
                    {{ [f.municipality, f.state, f.country_code !== 'BR' ? countryName(f.country_code) : null].filter(Boolean).join(', ') }}
                </span>
                <span v-if="f.area_ha" class="inline-flex items-center gap-1"><Icon name="grid" class="h-3.5 w-3.5" /> {{ fmt(f.area_ha, 1) }} ha</span>
                <span class="inline-flex items-center gap-1"><Icon name="clock" class="h-3.5 w-3.5" /> {{ since(f.analyzed_at) }}</span>
            </div>
        </Link>
        <Link v-if="showAdd" :href="$url('/talhoes/novo')" class="flex min-h-[180px] flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-stone-300 p-5 text-stone-500 transition hover:border-safra-600 hover:bg-safra-50 hover:text-safra-800">
            <span class="grid h-10 w-10 place-items-center rounded-full bg-white shadow-[var(--shadow-soft)]"><Icon name="plus" class="h-5 w-5" /></span>
            <span class="text-sm font-semibold">{{ $t('Cadastrar outro talhão') }}</span>
        </Link>
    </div>
</template>
