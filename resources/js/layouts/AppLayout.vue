<script setup lang="ts">
import { Link, usePage } from '@inertiajs/vue3';
import { appPath, url } from '@/lib/url';
import { locale, setLocale, type Locale } from '@/lib/i18n';
import { computed, ref, watch } from 'vue';
import Icon from '@/components/Icon.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import type { SharedProps } from '@/types/global';

const props = withDefaults(defineProps<{ title?: string; back?: string; showWarning?: boolean; wide?: boolean; landing?: boolean }>(), { wide: false });
// Telas de análise usam largura maior (conteúdo + coluna lateral); o resto fica em leitura confortável.
const container = computed(() => (props.wide ? 'max-w-[88rem]' : props.landing ? 'max-w-[84rem]' : 'max-w-6xl'));

const page = usePage<SharedProps>();
// Tolerante a páginas de erro, onde parte dos dados compartilhados pode faltar.
const flash = computed(() => page.props.flash ?? { success: null, error: null });
const path = computed(() => appPath(page.url));
const menuOpen = ref(false);
const menuButton = ref<HTMLButtonElement | null>(null);
const navigation = [
    { href: '/talhoes', label: 'Meus talhões', icon: 'map' },
    { href: '/metodologia', label: 'Metodologia', icon: 'book' },
    { href: '/#dados', label: 'Dados', icon: 'database' },
] as const;

watch(() => page.url, () => { menuOpen.value = false; });

function closeMenu() {
    if (!menuOpen.value) return;
    menuOpen.value = false;
    menuButton.value?.focus();
}

const year = new Date().getFullYear();

function changeLanguage(event: Event) {
    setLocale((event.target as HTMLSelectElement).value as Locale);
}
</script>

<template>
    <div class="flex min-h-screen flex-col">
        <a href="#conteudo" class="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:font-semibold focus:text-safra-900">{{ $t('Pular para o conteúdo') }}</a>

        <!-- ================= HEADER ================= -->
        <header class="sticky top-0 z-50 border-b border-white/10 bg-[#102b22] text-white print:hidden" @keydown.esc="closeMenu">
            <div class="mx-auto flex h-16 w-full items-center gap-1.5 px-3 sm:gap-3 sm:px-6" :class="container">
                <Link v-if="back" :href="url(back)" class="grid size-9 shrink-0 place-items-center rounded-lg text-white/80 transition hover:bg-white/10 hover:text-white" :aria-label="$t('Voltar')">
                    <Icon name="arrowLeft" class="h-5 w-5" />
                </Link>
                <Link :href="$url('/')" class="flex shrink-0 items-center gap-1.5 text-[15px] font-extrabold tracking-tight transition hover:opacity-90 sm:gap-2.5 sm:text-[17px]">
                    <span class="grid size-8 place-items-center rounded-[9px] bg-gradient-to-br from-safra-500 to-safra-800 sm:size-[34px]">
                        <Icon name="logo" :stroke-width="2.2" class="h-[18px] w-[18px]" />
                    </span>
                    <span>GeoSafra</span>
                </Link>
                <span v-if="title" class="hidden min-w-0 items-center gap-2 text-sm text-white/60 xl:flex">
                    <span aria-hidden="true">/</span><span class="truncate">{{ title }}</span>
                </span>

                <nav class="ml-auto hidden items-center gap-1 lg:flex" :aria-label="$t('Navegação principal')">
                    <component
                        :is="item.href.includes('#') ? 'a' : Link"
                        v-for="item in navigation" :key="item.href" :href="$url(item.href)"
                        class="inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-sm font-medium whitespace-nowrap text-white/80 transition hover:bg-white/10 hover:text-white"
                        :class="path === item.href || item.href === '/talhoes' && /^\/talhoes\/\d+$/.test(path) ? 'bg-white/10 text-white' : ''"
                        :aria-current="path === item.href ? 'page' : undefined"
                    >
                        <Icon :name="item.icon" class="size-[15px] opacity-70" /> {{ $t(item.label) }}
                    </component>
                </nav>
                <div class="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2 lg:ml-0">
                    <select :value="locale" :aria-label="$t('Idioma')" class="h-10 rounded-lg border border-white/25 bg-[#102b22] px-1.5 text-xs text-white sm:px-2" @change="changeLanguage">
                        <option value="en-US" lang="en-US">EN-US</option>
                        <option value="pt-BR" lang="pt-BR">PT-BR</option>
                    </select>
                    <Link :href="$url('/talhoes/novo')" :aria-label="$t('Novo talhão')" class="inline-flex h-10 min-w-10 items-center justify-center gap-2 rounded-lg bg-lime-300 text-sm font-bold whitespace-nowrap text-safra-950 transition hover:bg-lime-400 sm:px-3.5">
                        <Icon name="plus" :stroke-width="2.5" class="size-4" /><span class="hidden sm:inline">{{ $t('Novo talhão') }}</span>
                    </Link>
                    <button ref="menuButton" type="button" class="grid size-10 place-items-center rounded-lg border border-white/20 hover:bg-white/10 lg:hidden" aria-controls="mobile-navigation" :aria-expanded="menuOpen" :aria-label="$t(menuOpen ? 'Fechar menu' : 'Abrir menu')" @click="menuOpen = !menuOpen">
                        <Icon :name="menuOpen ? 'x' : 'menu'" class="size-5" />
                    </button>
                </div>
            </div>
            <nav v-show="menuOpen" id="mobile-navigation" class="absolute inset-x-0 top-full border-t border-white/10 bg-[#102b22] shadow-[var(--shadow-lift)] lg:hidden" :aria-label="$t('Navegação principal')">
                <div class="mx-auto grid gap-1 px-3 py-3 sm:px-6" :class="container">
                    <component :is="item.href.includes('#') ? 'a' : Link" v-for="item in navigation" :key="item.href" :href="$url(item.href)" :aria-current="path === item.href ? 'page' : undefined" class="flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium text-white/90 hover:bg-white/10" @click="menuOpen = false">
                        <Icon :name="item.icon" class="size-4 opacity-75" /> {{ $t(item.label) }}
                    </component>
                </div>
            </nav>
        </header>

        <!-- ================= FLASH ================= -->
        <div v-if="flash.success || flash.error" class="mx-auto w-full px-4 pt-4 sm:px-6 print:hidden" :class="container">
            <div v-if="flash.success" class="notice-info animate-fade-up" role="status"><Icon name="check" :stroke-width="2.5" /><p class="font-medium">{{ flash.success }}</p></div>
            <div v-if="flash.error" class="notice-error animate-fade-up" role="alert"><Icon name="alert" /><p class="font-medium">{{ flash.error }}</p></div>
        </div>

        <!-- ================= MAIN ================= -->
        <main id="conteudo" class="mx-auto w-full min-w-0 flex-1 px-3 pb-12 sm:px-6" :class="[container, landing ? 'pt-3 sm:pt-5' : 'pt-5 sm:pt-8']">
            <slot />
        </main>

        <!-- ================= FOOTER ================= -->
        <footer class="relative mt-auto overflow-hidden bg-safra-950 text-white/75 before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-lime-300/50 before:to-transparent print:hidden">
            <div class="mx-auto w-full px-4 pt-10 pb-7 sm:px-6" :class="container">
                <div v-if="showWarning" class="mb-8 flex items-start gap-3 rounded-2xl border border-amber-300/25 bg-amber-300/10 p-4 text-sm text-amber-100">
                    <Icon name="alert" class="mt-0.5 h-5 w-5 shrink-0 text-amber-300" />
                    <p>{{ page.props.app?.footerWarning }}</p>
                </div>

                <div class="mb-8 grid gap-8 md:grid-cols-[1.4fr_1fr_1fr]">
                    <div>
                        <Link :href="$url('/')" class="mb-3 inline-flex items-center gap-2.5 text-[17px] font-extrabold tracking-tight text-white">
                            <span class="grid h-[34px] w-[34px] place-items-center rounded-[10px] bg-gradient-to-br from-safra-500 to-safra-800"><Icon name="logo" :stroke-width="2.2" class="h-[18px] w-[18px]" /></span>
                            GeoSafra
                        </Link>
                        <p class="mb-3 max-w-[38ch] text-[13px] leading-relaxed text-white/60">{{ $t('Apoio à decisão para rotação de culturas, com observações da Terra da NASA e as prioridades de quem planta.') }}</p>
                        <span class="inline-flex items-center gap-2 rounded-full border border-lime-300/25 bg-lime-300/10 px-3 py-1.5 text-[11px] font-bold tracking-wide text-lime-300">
                            <Icon name="star" :stroke-width="2.5" class="h-[13px] w-[13px]" /> NASA Space Apps {{ year }}
                        </span>
                    </div>
                    <div>
                        <h4 class="mb-3.5 text-xs font-bold tracking-[0.12em] text-lime-300 uppercase">{{ $t('Produto') }}</h4>
                        <ul class="space-y-2.5 text-[13.5px]">
                            <li><Link :href="$url('/talhoes')" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="map" class="h-3.5 w-3.5 opacity-60" /> {{ $t('Meus talhões') }}</Link></li>
                            <li><Link :href="$url('/metodologia')" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="book" class="h-3.5 w-3.5 opacity-60" /> {{ $t('Metodologia') }}</Link></li>
                            <li><a :href="$url('/#dados')" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="database" class="h-3.5 w-3.5 opacity-60" /> {{ $t('Fontes de dados') }}</a></li>
                            <li><Link :href="$url('/talhoes/novo')" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="plus" class="h-3.5 w-3.5 opacity-60" /> {{ $t('Cadastrar talhão') }}</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 class="mb-3.5 text-xs font-bold tracking-[0.12em] text-lime-300 uppercase">{{ $t('Recursos') }}</h4>
                        <ul class="space-y-2.5 text-[13.5px]">
                            <li><a href="https://power.larc.nasa.gov" target="_blank" rel="noopener" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="external" class="h-3.5 w-3.5 opacity-60" /> NASA POWER</a></li>
                            <li><a href="https://www.earthdata.nasa.gov" target="_blank" rel="noopener" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="external" class="h-3.5 w-3.5 opacity-60" /> NASA Earthdata</a></li>
                            <li><a href="https://www.spaceappschallenge.org" target="_blank" rel="noopener" class="inline-flex items-center gap-2 text-white/70 transition hover:translate-x-0.5 hover:text-lime-300"><Icon name="external" class="h-3.5 w-3.5 opacity-60" /> Space Apps Challenge</a></li>
                        </ul>
                    </div>
                </div>

                <div class="grid gap-3 border-t border-white/10 pt-6 text-xs leading-relaxed text-white/50 md:grid-cols-2 md:gap-8">
                    <p>{{ page.props.app?.powerCitation }}</p>
                    <p class="md:text-right">GeoSafra · Uberlândia (MG) · {{ page.props.app?.disclaimer }}</p>
                </div>
            </div>
        </footer>
        <ConfirmDialog />
    </div>
</template>
