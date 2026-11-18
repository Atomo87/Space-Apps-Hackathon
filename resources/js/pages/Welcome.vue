<script setup lang="ts">
import { t } from '@/lib/i18n';
import { Head, Link, usePage } from '@inertiajs/vue3';
import { computed } from 'vue';
import heroImage from '@/assets/geosafra-fields.webp';
import heroImageMobile from '@/assets/geosafra-fields-mobile.webp';
import Icon, { type IconName } from '@/components/Icon.vue';
import DemoPicker, { type DemoRegion } from '@/components/DemoPicker.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import type { SharedProps } from '@/types/global';

const page = usePage<SharedProps>();
const glossary = computed(() => page.props.glossary);
defineProps<{ demoRegions: DemoRegion[] }>();

const steps: { title: string; text: string; icon: IconName }[] = [
    { title: t('Localize o talhão'), text: t('Busque o município, ajuste o ponto no mapa e informe o histórico da área.'), icon: 'map' },
    { title: t('Entenda os riscos'), text: t('Veja janelas de plantio, períodos de seca e meses de maior risco para a lavoura.'), icon: 'calendar' },
    { title: t('Compare rotações'), text: t('Compare a rotação atual com alternativas e confira os fatores que pesam em cada opção.'), icon: 'chart' },
];

const highlights: { name: string; label: string; icon: IconName }[] = [
    { name: 'NASA POWER', label: t('Clima histórico'), icon: 'sun' },
    { name: 'HLS', label: t('Vegetação por satélite'), icon: 'satellite' },
    { name: 'SRTM', label: t('Elevação e relevo'), icon: 'mountain' },
];

const dataInUse: { name: string; text: string; icon: IconName }[] = [
    { name: 'NASA POWER', text: t('Clima diário desde 1981: chuva, temperatura, umidade, vento, radiação e umidade do solo'), icon: 'sun' },
    { name: 'SRTM', text: t('Elevação de ~30 m: declividade e fator de relevo da erosão'), icon: 'mountain' },
    { name: 'MODIS NDVI', text: t('5 anos de verde a cada 16 dias (250 m): ciclo da lavoura e meses de solo exposto'), icon: 'leaf' },
    { name: 'HLS', text: t('Landsat + Sentinel-2 a 30 m: o verde do próprio talhão, imagem a imagem'), icon: 'grid' },
    { name: 'MODIS LST', text: t('Temperatura da superfície: calor do chão e da lavoura comparado com o ar'), icon: 'thermometer' },
    { name: 'MODIS ET', text: t('Evapotranspiração real × potencial: estresse hídrico observado a cada ano'), icon: 'droplet' },
    { name: 'SMAP', text: t('Umidade do solo medida por micro-ondas: meses de solo seco e o último mês contra o normal'), icon: 'droplet' },
    { name: 'ECOSTRESS', text: t('Estresse da planta a 70 m, passagem a passagem, a partir da Estação Espacial'), icon: 'thermometer' },
    { name: 'GRACE-FO', text: t('Água total armazenada na região (solo, aquífero e rios) e sua tendência desde 2002'), icon: 'waves' },
    { name: 'GPM IMERG', text: t('Chuva medida por satélite (~11 km) desde 2016, comparada com a chuva do modelo POWER'), icon: 'rain' },
    { name: t('POWER diário'), text: t('Chuva e temperatura dia a dia para achar a janela de plantio de cada safra'), icon: 'calendar' },
    { name: 'NASA GIBS', text: t('Imagens do talhão em cor real (HLS 30 m) e verde (MODIS NDVI) por data'), icon: 'map' },
    { name: 'NASA FIRMS', text: t('Focos de queimada dos satélites VIIRS e MODIS perto do talhão, quase em tempo real'), icon: 'flame' },
];

const priorities = [t('Economizar água'), t('Gerar renda complementar'), t('Fixar nitrogênio'), t('Reduzir erosão'), t('Aumentar matéria orgânica'), t('Produzir forragem'), t('Atender ao mercado'), t('Quebrar ciclo de pragas')];
const terms = [{ key: 'et' }, { key: 'balanco' }, { key: 'declividade' }];
</script>

<template>
    <Head :title="$t('Início')" />
    <AppLayout landing>
        <div class="landing-page">
            <section class="landing-hero" aria-labelledby="hero-title">
                <div class="landing-hero-copy">
                    <p class="flex items-center gap-2 text-xs font-bold tracking-[0.13em] text-[#d0e8a7] uppercase">
                        <Icon name="satellite" class="h-4 w-4 shrink-0" />
                        {{ $t('Rotação de culturas com dados da NASA') }}
                    </p>
                    <h1 id="hero-title" class="landing-title mt-5">
                        {{ $t('Planeje a próxima safra') }}
                        <em>{{ $t('com dados do seu talhão.') }}</em>
                    </h1>
                    <p class="mt-5 max-w-[42ch] text-base leading-relaxed text-white/80 sm:text-lg">
                        {{ $t('Compare rotações de culturas, antecipe riscos climáticos e avalie as melhores janelas de plantio para a sua propriedade.') }}
                    </p>
                    <div class="mt-7 grid gap-2.5 sm:flex sm:flex-wrap">
                        <Link :href="$url('/talhoes/novo')" class="btn-lime min-h-12">
                            {{ $t('Cadastrar meu talhão') }} <Icon name="arrowRight" />
                        </Link>
                        <details>
                            <summary class="btn-ghost min-h-12 cursor-pointer list-none">
                                <Icon name="play" /> {{ $t('Ver demonstração') }}
                            </summary>
                            <DemoPicker :regions="demoRegions" dark class="mt-3" />
                        </details>
                    </div>
                    <p class="mt-4 flex items-center gap-2 text-sm text-white/70">
                        <Icon name="check" class="h-4 w-4 shrink-0 text-[#c8e89b]" />
                        {{ $t('Grátis · acesso livre, sem cadastro') }}
                    </p>
                </div>

                <figure class="landing-hero-image">
                    <img
                        :src="heroImage"
                        :srcset="`${heroImageMobile} 640w, ${heroImage} 1200w`"
                        sizes="(max-width: 767px) calc(100vw - 60px), (max-width: 1344px) 43vw, 560px"
                        alt="" decoding="async" fetchpriority="high" width="1200" height="900"
                    />
                    <div class="landing-field-outline" aria-hidden="true" />
                    <figcaption>
                        <Icon name="layers" class="h-4 w-4 shrink-0" />
                        {{ $t('Vista aérea ilustrativa') }}
                    </figcaption>
                </figure>
            </section>

            <section id="como-funciona" class="landing-section scroll-mt-28" aria-labelledby="como-title">
                <div class="max-w-2xl">
                    <h2 id="como-title" class="landing-heading">{{ $t('Do mapa à decisão de plantio') }}</h2>
                    <p class="mt-3 text-stone-600">{{ $t('Cadastre um talhão e veja quais informações podem orientar a próxima safra.') }}</p>
                </div>
                <div class="mt-6 grid gap-3 md:grid-cols-3">
                    <article v-for="step in steps" :key="step.title" class="landing-step">
                        <span class="landing-step-icon"><Icon :name="step.icon" class="h-5 w-5" /></span>
                        <h3 class="mt-4 text-lg font-bold tracking-tight text-[#142b21]">{{ step.title }}</h3>
                        <p class="mt-2 text-sm leading-relaxed text-stone-600">{{ step.text }}</p>
                    </article>
                </div>
            </section>

            <section id="dados" class="landing-section landing-data scroll-mt-28" aria-labelledby="dados-title">
                <div class="grid gap-5 lg:grid-cols-[1fr_1.1fr] lg:items-center">
                    <div>
                        <h2 id="dados-title" class="landing-heading">{{ $t('As fontes por trás da análise') }}</h2>
                        <p class="mt-3 max-w-[48ch] text-stone-600">{{ $t('Observações da Terra da NASA combinadas com o que você sabe do seu talhão: solo, histórico, água, equipamentos e mercado.') }}</p>
                        <Link :href="$url('/metodologia')" class="link mt-4 inline-flex min-h-11 items-center gap-2 text-sm">
                            {{ $t('Conhecer a metodologia') }} <Icon name="arrowRight" class="h-4 w-4" />
                        </Link>
                    </div>
                    <div class="grid gap-2 sm:grid-cols-3">
                        <div v-for="source in highlights" :key="source.name" class="landing-source">
                            <Icon :name="source.icon" class="h-5 w-5 text-[#315a40]" />
                            <span class="mt-2 block text-sm font-bold text-[#142b21]">{{ source.name }}</span>
                            <span class="text-xs text-stone-600">{{ source.label }}</span>
                        </div>
                    </div>
                </div>

                <details class="landing-disclosure mt-5">
                    <summary>{{ $t('Ver todas as fontes de dados') }}</summary>
                    <ul class="mt-4 grid gap-x-6 gap-y-3 pb-2 text-sm sm:grid-cols-2">
                        <li v-for="source in dataInUse" :key="source.name" class="flex items-start gap-2.5">
                            <Icon :name="source.icon" class="mt-0.5 h-4 w-4 shrink-0 text-[#315a40]" />
                            <div><strong class="text-[#142b21]">{{ source.name }}</strong><p class="text-stone-600">{{ source.text }}</p></div>
                        </li>
                    </ul>
                </details>
            </section>

            <section class="landing-section" aria-labelledby="prio-title">
                <h2 id="prio-title" class="landing-heading">{{ $t('Você decide o que importa') }}</h2>
                <p class="mt-3 text-stone-600">{{ $t('Suas prioridades definem o peso de cada critério na comparação das rotações.') }}</p>
                <ul class="mt-5 flex flex-wrap gap-2">
                    <li v-for="priority in priorities" :key="priority" class="rounded-full border border-[#dce5d9] bg-white px-3 py-1.5 text-sm font-medium text-[#274535]">{{ priority }}</li>
                </ul>
                <details class="landing-disclosure mt-5">
                    <summary>{{ $t('Glossário e limites da análise') }}</summary>
                    <div class="mt-4 grid gap-4 sm:grid-cols-3">
                        <div v-for="term in terms" :key="term.key">
                            <h3 class="text-sm font-bold text-[#142b21]">{{ glossary?.[term.key]?.term }}</h3>
                            <p class="mt-1 text-sm text-stone-600">{{ glossary?.[term.key]?.text }}</p>
                        </div>
                    </div>
                    <p class="mt-4 border-t border-stone-200 pt-4 text-sm text-stone-600">{{ page.props.app?.footerWarning }}</p>
                </details>
            </section>

            <section class="landing-section landing-cta" aria-labelledby="cta-title">
                <div class="min-w-0">
                    <h2 id="cta-title" class="text-2xl font-bold tracking-tight sm:text-3xl">{{ $t('Comece pelo seu talhão') }}</h2>
                    <p class="mt-2 max-w-[48ch] text-sm text-white/75 sm:text-base">{{ $t('Marque sua área no mapa e compare alternativas para a próxima safra.') }}</p>
                </div>
                <Link :href="$url('/talhoes/novo')" class="btn-lime min-h-12">
                    {{ $t('Cadastrar meu talhão') }} <Icon name="arrowRight" />
                </Link>
            </section>
        </div>
    </AppLayout>
</template>

<style scoped>
.landing-page {
    color: #142b21;
}

.landing-hero {
    display: grid;
    min-width: 0;
    gap: clamp(1.5rem, 4vw, 3.5rem);
    align-items: center;
    padding: clamp(1.05rem, 3.5vw, 3.4rem);
    border-radius: clamp(1.25rem, 3vw, 2rem);
    background: radial-gradient(ellipse at 78% 60%, #254736 0%, #102b22 62%);
    color: #fff;
}

.landing-hero-copy {
    min-width: 0;
    padding-block: 0.5rem;
}

.landing-title {
    max-width: 13ch;
    font-size: clamp(2.2rem, 6.5vw, 5.1rem);
    font-weight: 750;
    line-height: 0.99;
    letter-spacing: -0.055em;
    text-wrap: balance;
}

.landing-title em {
    display: block;
    margin-top: 0.1em;
    color: #d3efa6;
    font-family: 'Instrument Serif', Georgia, serif;
    font-size: 1.12em;
    font-weight: 400;
    line-height: 0.98;
    letter-spacing: -0.022em;
}

.landing-hero-image {
    position: relative;
    isolation: isolate;
    display: flex;
    align-items: flex-end;
    aspect-ratio: 5 / 4;
    overflow: hidden;
    border: 1px solid rgb(255 255 255 / 0.18);
    border-radius: clamp(0.9rem, 2vw, 1.45rem);
    background: #304d34;
}

.landing-hero-image img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 51%;
}

.landing-field-outline {
    position: absolute;
    inset: 17% 13% 19% 14%;
    pointer-events: none;
    background: rgb(216 255 148 / 0.8);
    clip-path: polygon(12% 32%, 57% 5%, 93% 21%, 88% 74%, 42% 93%, 13% 74%, 12% 32%, 13% 33%, 14% 73%, 42% 92%, 87% 73%, 92% 22%, 57% 6%, 13% 33%);
    filter: drop-shadow(0 0 9px rgb(188 247 107 / 0.4));
}

.landing-hero-image figcaption {
    position: relative;
    display: flex;
    gap: 0.45rem;
    align-items: center;
    margin: clamp(0.55rem, 2vw, 1rem);
    padding: 0.54rem 0.75rem;
    border: 1px solid rgb(255 255 255 / 0.24);
    border-radius: 0.7rem;
    background-color: rgb(10 29 20 / 0.8);
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
    backdrop-filter: blur(6px);
}

.landing-section {
    margin-top: clamp(2.25rem, 5.5vw, 4.75rem);
}

.landing-heading {
    font-size: clamp(1.65rem, 3.4vw, 2.8rem);
    font-weight: 750;
    line-height: 1.15;
    letter-spacing: -0.045em;
    text-wrap: balance;
}

.landing-step,
.landing-source {
    min-width: 0;
    border: 1px solid #dfe7da;
    border-radius: 1rem;
    background: #fff;
}

.landing-step {
    padding: clamp(1rem, 2vw, 1.5rem);
}

.landing-step-icon {
    display: grid;
    width: 2.5rem;
    height: 2.5rem;
    place-items: center;
    border-radius: 0.75rem;
    background: #e8f1dc;
    color: #2c553a;
}

.landing-source {
    padding: 0.9rem;
}

.landing-data {
    padding: clamp(1rem, 3vw, 2rem);
    border-radius: 1.4rem;
    background: #edf2e7;
}

.landing-disclosure {
    border-block-start: 1px solid #d9e3d3;
}

.landing-disclosure summary {
    min-height: 2.75rem;
    padding-block: 0.65rem;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 650;
    color: #28523b;
}

.landing-disclosure summary::marker {
    color: #386348;
}

.landing-cta {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    justify-content: space-between;
    padding: clamp(1.15rem, 3vw, 2.5rem);
    border-radius: 1.4rem;
    background: #102b22;
    color: #fff;
}

@media (min-width: 48rem) {
    .landing-hero {
        grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
    }

    .landing-hero-image {
        aspect-ratio: 1;
    }

    .landing-cta {
        flex-direction: row;
        align-items: center;
    }
}

@media (min-width: 75rem) {
    .landing-hero-image {
        aspect-ratio: 6 / 5;
    }
}
</style>
