<!-- Ilustração decorativa do hero: globo, satélite em órbita varrendo a lavoura e ícones dos dados monitorados. -->
<template>
    <div class="hero-visual relative mx-auto aspect-square w-full max-w-[340px] lg:max-w-[440px]" aria-hidden="true">
        <svg viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg" class="h-full w-full overflow-visible drop-shadow-[0_20px_40px_rgba(0,0,0,0.35)]">
            <defs>
                <radialGradient id="hv-globe" cx="40%" cy="35%" r="70%">
                    <stop offset="0%" stop-color="#34d399" /><stop offset="55%" stop-color="#16a34a" /><stop offset="100%" stop-color="#065f46" />
                </radialGradient>
                <radialGradient id="hv-shine" cx="35%" cy="30%" r="60%">
                    <stop offset="0%" stop-color="#fff" stop-opacity=".35" /><stop offset="60%" stop-color="#fff" stop-opacity="0" />
                </radialGradient>
                <radialGradient id="hv-atmo" cx="50%" cy="50%" r="50%">
                    <stop offset="60%" stop-color="#22c55e" stop-opacity="0" /><stop offset="100%" stop-color="#22c55e" stop-opacity=".35" />
                </radialGradient>
                <linearGradient id="hv-sat" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#f8fafc" /><stop offset="100%" stop-color="#94a3b8" /></linearGradient>
                <linearGradient id="hv-panel" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1e40af" /><stop offset="100%" stop-color="#1e3a8a" /></linearGradient>
                <linearGradient id="hv-beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#a3e635" stop-opacity=".9" /><stop offset="100%" stop-color="#a3e635" stop-opacity="0" /></linearGradient>
                <linearGradient id="hv-soil" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#78350f" /><stop offset="100%" stop-color="#451a03" /></linearGradient>
                <linearGradient id="hv-crop" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#a3e635" /><stop offset="100%" stop-color="#4d7c0f" /></linearGradient>
                <filter id="hv-glow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            <circle cx="250" cy="250" r="180" fill="none" stroke="#22c55e" stroke-opacity=".15" stroke-width="1.5" />
            <circle cx="250" cy="250" r="160" fill="url(#hv-atmo)" />
            <ellipse cx="250" cy="250" rx="215" ry="80" fill="none" stroke="#a3e635" stroke-opacity=".35" stroke-width="1.5" stroke-dasharray="4 8" transform="rotate(-25 250 250)" />
            <ellipse cx="250" cy="250" rx="215" ry="80" fill="none" stroke="#a3e635" stroke-opacity=".2" stroke-width="1" stroke-dasharray="2 10" transform="rotate(25 250 250)" />

            <circle class="ring" cx="250" cy="250" r="160" fill="none" stroke="#a3e635" stroke-width="2" />
            <circle class="ring d1" cx="250" cy="250" r="160" fill="none" stroke="#a3e635" stroke-width="2" />
            <circle class="ring d2" cx="250" cy="250" r="160" fill="none" stroke="#a3e635" stroke-width="2" />

            <!-- globo -->
            <circle cx="250" cy="250" r="150" fill="url(#hv-globe)" />
            <g class="globe">
                <path d="M210 200Q230 185 255 195Q280 205 290 230Q295 250 285 275Q275 300 260 315Q245 325 235 310Q225 290 220 265Q210 240 210 200Z" fill="#166534" fill-opacity=".85" stroke="#14532d" stroke-width=".5" />
                <path d="M300 180Q320 175 330 190Q335 205 325 215Q315 220 305 210Q298 200 300 180Z" fill="#166534" fill-opacity=".7" />
                <g stroke="#84cc16" stroke-width=".8" stroke-opacity=".6" fill="none">
                    <path d="M220 220Q240 225 260 230" /><path d="M225 245Q245 250 270 255" /><path d="M230 270Q250 275 275 278" /><path d="M240 290Q255 293 270 295" />
                </g>
            </g>
            <g stroke="#fff" stroke-opacity=".18" stroke-width="1" fill="none">
                <ellipse cx="250" cy="250" rx="150" ry="150" /><ellipse cx="250" cy="250" rx="110" ry="150" /><ellipse cx="250" cy="250" rx="60" ry="150" />
                <ellipse cx="250" cy="250" rx="150" ry="110" /><ellipse cx="250" cy="250" rx="150" ry="60" /><line x1="100" y1="250" x2="400" y2="250" />
            </g>
            <circle cx="250" cy="250" r="150" fill="url(#hv-shine)" />
            <circle cx="250" cy="250" r="150" fill="none" stroke="#4ade80" stroke-opacity=".5" stroke-width="1.5" />

            <!-- feixe de varredura -->
            <g class="beam">
                <path d="M355 145L310 245L290 245Z" fill="url(#hv-beam)" filter="url(#hv-glow)" />
                <path d="M355 145L330 250L320 250Z" fill="url(#hv-beam)" />
            </g>

            <!-- satélite -->
            <g class="orbit">
                <g transform="translate(355 145)">
                    <g class="bob">
                        <rect x="-38" y="-8" width="22" height="16" rx="2" fill="url(#hv-panel)" stroke="#1e3a8a" stroke-width=".5" />
                        <rect x="16" y="-8" width="22" height="16" rx="2" fill="url(#hv-panel)" stroke="#1e3a8a" stroke-width=".5" />
                        <g stroke="#3b82f6" stroke-width=".4" stroke-opacity=".7">
                            <line x1="-32" y1="-8" x2="-32" y2="8" /><line x1="-27" y1="-8" x2="-27" y2="8" /><line x1="-22" y1="-8" x2="-22" y2="8" />
                            <line x1="21" y1="-8" x2="21" y2="8" /><line x1="26" y1="-8" x2="26" y2="8" /><line x1="31" y1="-8" x2="31" y2="8" />
                            <line x1="-38" y1="0" x2="-16" y2="0" /><line x1="16" y1="0" x2="38" y2="0" />
                        </g>
                        <line x1="-16" y1="0" x2="-10" y2="0" stroke="#cbd5e1" stroke-width="1.5" /><line x1="10" y1="0" x2="16" y2="0" stroke="#cbd5e1" stroke-width="1.5" />
                        <rect x="-10" y="-10" width="20" height="20" rx="3" fill="url(#hv-sat)" stroke="#64748b" stroke-width=".8" />
                        <circle r="3" fill="#0f172a" /><circle r="1.2" fill="#a3e635" />
                        <path d="M0 10L-4 18L4 18Z" fill="#cbd5e1" stroke="#64748b" stroke-width=".5" />
                        <circle cy="18" r="1.5" fill="#a3e635" filter="url(#hv-glow)" />
                    </g>
                </g>
            </g>

            <!-- lavoura -->
            <path d="M140 400Q250 380 360 400L360 410Q250 390 140 410Z" fill="url(#hv-soil)" stroke="#292524" stroke-width=".5" />
            <g v-for="(row, i) in crops" :key="i" class="crop" :style="{ animationDelay: `${i * 0.4}s` }">
                <path v-for="x in row" :key="x" :d="`M${x} 398Q${x + 10} 378 ${x + 20} 398`" fill="none" stroke="url(#hv-crop)" stroke-width="3" stroke-linecap="round" />
            </g>
            <path d="M150 400Q250 385 350 400" fill="none" stroke="#a3e635" stroke-width="1" stroke-opacity=".6" />

            <!-- dados monitorados -->
            <g transform="translate(95 175)"><g class="float" filter="url(#hv-glow)">
                <circle r="16" fill="#065f46" fill-opacity=".8" stroke="#4ade80" stroke-width="1" />
                <path d="M-6 4Q-6-4 4-6Q6 4-2 6Z" fill="#a3e635" /><line x1="-4" y1="4" x2="2" y2="-2" stroke="#065f46" stroke-width="1" />
            </g></g>
            <g transform="translate(410 210)"><g class="float d1" filter="url(#hv-glow)">
                <circle r="16" fill="#0c4a6e" fill-opacity=".8" stroke="#38bdf8" stroke-width="1" />
                <path d="M0-7Q-6 0 0 6Q6 0 0-7Z" fill="#38bdf8" />
            </g></g>
            <g transform="translate(400 355)"><g class="float d2" filter="url(#hv-glow)">
                <circle r="16" fill="#7c2d12" fill-opacity=".8" stroke="#fb923c" stroke-width="1" />
                <rect x="-1.5" y="-8" width="3" height="11" rx="1.5" fill="#fb923c" /><circle cy="5" r="3.5" fill="#fb923c" />
            </g></g>
            <g transform="translate(95 330)"><g class="float d1" filter="url(#hv-glow)">
                <circle r="16" fill="#44403c" fill-opacity=".85" stroke="#d6d3d1" stroke-width="1" />
                <path d="M-8 6L-2-5L2 1L4-2L8 6Z" fill="#d6d3d1" />
            </g></g>
        </svg>
    </div>
</template>

<script setup lang="ts">
const crops = [
    [165, 185, 205],
    [225, 245, 265],
    [285, 305, 325],
];
</script>

<style scoped>
.globe { transform-origin: 250px 250px; animation: spin 40s linear infinite; }
.orbit { transform-origin: 250px 250px; animation: spin 22s linear infinite; }
.bob { animation: bob 5s ease-in-out infinite; }
.beam { animation: beam 3s ease-in-out infinite; }
.ring { transform-origin: 250px 250px; animation: ring 3s ease-out infinite; }
.ring.d1 { animation-delay: 1s; }
.ring.d2 { animation-delay: 2s; }
.crop { transform-box: fill-box; transform-origin: bottom center; animation: sway 4s ease-in-out infinite; }
.float { animation: bob 6s ease-in-out infinite; }
.float.d1 { animation-delay: 1s; }
.float.d2 { animation-delay: 2s; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes beam { 0%, 100% { opacity: .15; } 50% { opacity: .5; } }
@keyframes ring { 0% { transform: scale(.6); opacity: .6; } 100% { transform: scale(1.8); opacity: 0; } }
@keyframes sway { 0%, 100% { transform: skewX(0); } 50% { transform: skewX(2deg); } }
</style>
