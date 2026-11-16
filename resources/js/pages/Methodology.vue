<script setup lang="ts">
import { Head } from '@inertiajs/vue3';
import Icon from '@/components/Icon.vue';
import Term from '@/components/Term.vue';
import AppLayout from '@/layouts/AppLayout.vue';
</script>

<template>
    <Head :title="$t('Metodologia')" />
    <AppLayout :title="$t('Metodologia')" back="/">
        <header class="hero-surface relative mb-8 overflow-hidden rounded-3xl p-6 text-white shadow-[var(--shadow-hero)] sm:p-10">
            <div class="hero-grid-overlay pointer-events-none absolute inset-0" />
            <div class="relative">
                <p class="eyebrow"><Icon name="book" class="h-3.5 w-3.5" /> {{ $t('Metodologia') }}</p>
                <h1 class="mt-4 max-w-[24ch] text-3xl leading-tight font-black tracking-tight sm:text-4xl">{{ $t('Como o GeoSafra chega às sugestões') }}</h1>
                <p class="mt-3 max-w-[60ch] text-white/80">{{ $t('Dados abertos da NASA, regras agronômicas explícitas e as suas prioridades. Toda nota pode ser rastreada até um dado e uma regra.') }}</p>
            </div>
        </header>

        <div class="grid gap-5 lg:grid-cols-[220px_1fr]">
            <nav class="hidden lg:block" :aria-label="$t('Seções')">
                <ol class="sticky top-24 space-y-1 text-sm">
                    <li v-for="(s, i) in [$t('Dados da NASA'), $t('Satélite × campo'), $t('Motor de rotação'), $t('Incerteza e limites'), $t('Atribuição')]" :key="s">
                        <a :href="`#sec-${i + 1}`" class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-stone-600 transition hover:bg-white hover:text-safra-800">
                            <span class="grid h-6 w-6 place-items-center rounded-md bg-stone-200/70 text-xs font-bold tabular-nums">{{ i + 1 }}</span>{{ s }}
                        </a>
                    </li>
                </ol>
            </nav>

            <article class="space-y-5">
                <section id="sec-1" class="card scroll-mt-24 space-y-3 text-[15px] leading-relaxed text-stone-700">
                    <h2 class="section-title !text-lg"><span class="h-icon"><Icon name="satellite" /></span> {{ $t('1. Dados da NASA') }}</h2>
                    <p>
                        {{ $t('Para o ponto do seu talhão, o serviço de dados consulta a') }} <Term k="power" /> {{ $t('dia a dia, ano a ano (2005–2025, ~7.600 dias): temperatura máxima, mínima e média, chuva corrigida, umidade do ar, ponto de orvalho, vento a 2 m, radiação solar, pressão e — quando disponível — umidade do solo na zona das raízes.') }}
                    </p>
                    <p>
                        {{ $t('Com isso calculamos a') }} <Term k="eto" /> {{ $t('pelo método FAO-56 Penman-Monteith (conferido contra os exemplos do próprio boletim da FAO), o') }} <Term k="balanco" />{{ $t(', os') }} <Term k="veranico" :label="$t('veranicos')" />{{ $t(', o') }} <Term k="geada" />{{ $t(', os dias de') }} <Term k="estresse_termico" />{{ $t(', as') }} <Term k="chuva_extrema" :label="$t('chuvas extremas')" /> {{ $t('e as') }}
                        <Term k="tendencia" :label="$t('tendências')" /> {{ $t('de longo prazo.') }}
                    </p>
                    <p>
                        {{ $t('Para o relevo, amostramos uma grade de 5 × 5 pontos de elevação do') }} <Term k="srtm" /> {{ $t('sobre o contorno do talhão e calculamos a') }} <Term k="declividade" />
                        {{ $t('e o fator topográfico (LS) da') }} <Term k="erosao" label="RUSLE" /> {{ $t('— McCool et al. (1987) para a inclinação, Wischmeier & Smith (1978) para o comprimento de rampa.') }}
                    </p>
                    <p class="rounded-xl bg-stone-50 p-3 text-sm text-stone-600">{{ $t('Dados ausentes viram “sem dado” (nunca zero) e meses com menos de 90% dos dias não entram nas médias. Se a elevação não puder ser obtida, a análise segue sem relevo e avisa.') }}</p>
                </section>

                <section id="sec-2" class="card scroll-mt-24 space-y-3 text-[15px] leading-relaxed text-stone-700">
                    <h2 class="section-title !text-lg"><span class="h-icon"><Icon name="target" /></span> 2. <Term k="satelite_campo" /></h2>
                    <div class="overflow-x-auto rounded-xl border border-stone-200">
                        <table class="w-full text-sm">
                            <thead class="bg-stone-50 text-left text-xs tracking-wide text-stone-500 uppercase">
                                <tr><th class="px-3 py-2.5" /><th class="px-3 py-2.5">{{ $t('Satélite / modelo (NASA)') }}</th><th class="px-3 py-2.5">{{ $t('Medição no campo') }}</th></tr>
                            </thead>
                            <tbody class="[&_td]:border-t [&_td]:border-stone-100 [&_td]:px-3 [&_td]:py-2.5">
                                <tr><td class="font-semibold text-stone-900">{{ $t('Cobertura') }}</td><td>{{ $t('Contínua, qualquer lugar') }}</td><td>{{ $t('Só no ponto medido') }}</td></tr>
                                <tr><td class="font-semibold text-stone-900">{{ $t('Detalhe') }}</td><td>{{ $t('~300 km (GRACE-FO) · ~50 km (POWER) · ~11 km (GPM) · 9 km (SMAP) · 1 km (temperatura da superfície) · 500 m (evapotranspiração) · 250 m (NDVI MODIS) · 70 m (ECOSTRESS) · 30 m (NDVI HLS, relevo SRTM)') }}</td><td>{{ $t('Exato no ponto') }}</td></tr>
                                <tr><td class="font-semibold text-stone-900">{{ $t('Histórico') }}</td><td>{{ $t('Décadas, padronizado') }}</td><td>{{ $t('Curto ou inexistente') }}</td></tr>
                                <tr><td class="font-semibold text-stone-900">{{ $t('Erros típicos') }}</td><td>{{ $t('Mistura o talhão com a região') }}</td><td>{{ $t('Calibração, falhas de registro') }}</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <p>{{ $t('Por isso o satélite dá a') }} <strong>{{ $t('tendência e o contexto') }}</strong>{{ $t(', e o dado local') }} <strong>{{ $t('calibra') }}</strong>{{ $t('. Quando você informa análise de solo e mercado, a') }} <Term k="confianca" /> {{ $t('sobe.') }}</p>
                </section>

                <section id="sec-3" class="card scroll-mt-24 space-y-3 text-[15px] leading-relaxed text-stone-700">
                    <h2 class="section-title !text-lg"><span class="h-icon"><Icon name="sliders" /></span> {{ $t('3. O motor de rotação') }}</h2>
                    <ol class="space-y-3">
                        <li v-for="(s, i) in [
                            [$t('Filtros duros'), $t('eliminam opções impossíveis: cultura excluída, equipamento que falta, frio abaixo da base, geada frequente, falta de mais da metade da água em metade dos anos, pH sem correção viável, mesma família seguida com doença compartilhada (ex.: soja → feijão e mofo-branco).')],
                            [$t('Notas de 0 a 100'), $t('em 10 critérios: água (balanço mensal ano a ano com água no solo), estrutura, nitrogênio, erosão (cobertura × chuva erosiva × fator LS do relevo), matéria orgânica, quebra de pragas, forragem, renda, mercado e segurança climática.')],
                            [$t('Pesos'), $t('= suas estrelas (0–5). A segurança climática sempre entra com peso 3.')],
                            [$t('Seleção diversa:'), $t('a atual (A) + as melhores alternativas que não sejam variações da mesma coisa.')],
                            [$t('Explicação'), $t('montada a partir dos números: porquê, evidências com fonte e período, benefícios em relação à atual, lacunas e riscos para conferir.')],
                        ]" :key="s[0]" class="flex gap-3">
                            <span class="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-safra-950 to-safra-800 text-xs font-extrabold text-lime-300">{{ i + 1 }}</span>
                            <p class="pt-0.5"><strong class="text-stone-900">{{ s[0] }}</strong> {{ s[1] }}</p>
                        </li>
                    </ol>
                    <p class="notice-info !text-sm"><Icon name="info" /><span>{{ $t('Não usamos IA “caixa-preta” para escolher a rotação: toda nota pode ser rastreada até um dado e uma regra. A estatística (percentis, Mann-Kendall, Sen) aparece no diagnóstico e na faixa de variação entre anos secos e chuvosos.') }}</span></p>
                </section>

                <section id="sec-4" class="card scroll-mt-24 space-y-3 text-[15px] leading-relaxed text-stone-700">
                    <h2 class="section-title !text-lg"><span class="h-icon"><Icon name="alert" /></span> {{ $t('4. Incerteza e limites') }}</h2>
                    <ul class="space-y-2.5">
                        <li v-for="t in [
                            $t('O clima vem de uma grade regional: baixadas de geada e encharcamento não aparecem.'),
                            $t('O catálogo de culturas é simplificado; atributos sem fonte direta estão marcados como hipótese a validar com agrônomos.'),
                            $t('A declividade vem do SRTM (pixel de 30 m, ano 2000), com comprimento de rampa assumido de 100 m: terraços e curvas de nível não aparecem.'),
                            $t('O NDVI é lido no centro do talhão: o HLS (30 m, 2 anos) vira a referência quando cobre ao menos 10 meses; senão vale o MODIS (250 m, 5 anos), que em áreas pequenas mistura a vizinhança. Palhada seca aparece com NDVI baixo, como solo exposto.'),
                            $t('Temperatura da superfície (1 km) e evapotranspiração (500 m, anual) do MODIS incluem a vizinhança do talhão. Esses indicadores de satélite entram no diagnóstico e nas evidências, não na nota.'),
                            $t('Cenários ajustam o clima histórico; não são previsão do tempo.'),
                            $t('Estratégias com confiança abaixo de 50% recebem o selo “Baixa confiança — validar com técnico”.'),
                        ]" :key="t" class="flex gap-3"><span class="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />{{ t }}</li>
                    </ul>
                </section>

                <section id="sec-5" class="card scroll-mt-24 space-y-1.5 text-sm text-stone-600">
                    <h2 class="section-title mb-2 !text-lg"><span class="h-icon"><Icon name="bookOpen" /></span> {{ $t('5. Atribuição') }}</h2>
                    <p>{{ $page.props.app.powerCitation }}</p>
                    <p>{{ $t('Elevação: NASA Shuttle Radar Topography Mission (SRTM) GL1, NASA JPL / USGS EROS, via OpenTopoData.') }}</p>
                    <p>{{ $t('Vegetação: Didan, K. (2021). MODIS/Terra e Aqua Vegetation Indices 16-Day L3 Global 250m V061 (MOD13Q1/MYD13Q1), NASA LP DAAC — doi:10.5067/MODIS/MOD13Q1.061, via Microsoft Planetary Computer.') }}</p>
                    <p>{{ $t('NDVI de 30 m: NASA Harmonized Landsat and Sentinel-2 (HLS) v2.0, HLSL30 e HLSS30, NASA LP DAAC — doi:10.5067/HLS/HLSL30.002 e 10.5067/HLS/HLSS30.002.') }}</p>
                    <p>{{ $t('Temperatura da superfície: Wan, Z., Hook, S., Hulley, G. (2021). MOD11A2 v061, NASA LP DAAC — doi:10.5067/MODIS/MOD11A2.061.') }}</p>
                    <p>{{ $t('Evapotranspiração: Running, S. et al. (2021). MOD16A3GF v061, NASA LP DAAC — doi:10.5067/MODIS/MOD16A3GF.061.') }}</p>
                    <p>{{ $t('Umidade do solo: O\'Neill, P. E. et al. (2023). SMAP Enhanced L3 9 km (SPL3SMP_E) v6, NASA NSIDC DAAC — doi:10.5067/M20OXIZHY3RJ.') }}</p>
                    <p>{{ $t('Chuva por satélite: Huffman, G. J. et al. (2023). GPM IMERG Final mensal V07, NASA GES DISC — doi:10.5067/GPM/IMERG/3B-MONTH/07.') }}</p>
                    <p>{{ $t('Estresse da planta: ECOSTRESS ECO_L4T_ESI v002 (70 m), NASA LP DAAC — doi:10.5067/ECOSTRESS/ECO_L4T_ESI.002.') }}</p>
                    <p>{{ $t('Água armazenada: Wiese, D. N. et al. (2023). JPL GRACE/GRACE-FO Mascon RL06.3 v04 CRI, NASA PO.DAAC — doi:10.5067/TEMSC-3JC63.') }}</p>
                    <p>{{ $t('Cálculo da ETo: Allen, R. G. et al. (1998). FAO Irrigation and Drainage Paper 56.') }}</p>
                    <p>{{ $t('Erosão: Renard, K. G. et al. (1997). RUSLE — USDA Agriculture Handbook 703.') }}</p>
                    <p>{{ $t('Mapas: imagens © Esri, Maxar, Earthstar Geographics; © colaboradores do OpenStreetMap.') }}</p>
                </section>
            </article>
        </div>
    </AppLayout>
</template>
