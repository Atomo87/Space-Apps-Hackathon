import '../css/app.css';

import { createInertiaApp } from '@inertiajs/vue3';
import { resolvePageComponent } from 'laravel-vite-plugin/inertia-helpers';
import { createApp, h, type DefineComponent } from 'vue';
import { url } from './lib/url';
import { t } from './lib/i18n';

declare module 'vue' {
    interface ComponentCustomProperties {
        /** Prefixa caminhos internos com a subpasta do app (ver lib/url.ts). */
        $url: typeof url;
        $t: typeof t;
    }
}

const appName = import.meta.env.VITE_APP_NAME || 'GeoSafra';

createInertiaApp({
    title: (title) => (title ? `${title} · ${appName}` : appName),
    resolve: (name) =>
        resolvePageComponent(`./pages/${name}.vue`, import.meta.glob<DefineComponent>('./pages/**/*.vue')),
    setup({ el, App, props, plugin }) {
        const app = createApp({ render: () => h(App, props) }).use(plugin);
        app.config.globalProperties.$url = url;
        app.config.globalProperties.$t = t;
        app.mount(el);
    },
    progress: {
        color: '#16a34a',
    },
});
