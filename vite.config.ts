import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import laravel from 'laravel-vite-plugin';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [
        laravel({
            input: ['resources/js/app.ts'],
            refresh: true,
        }),
        tailwindcss(),
        vue({
            template: {
                transformAssetUrls: {
                    base: null,
                    includeAbsolute: false,
                },
            },
        }),
    ],
    // URLs dos chunks relativas ao próprio arquivo JS: o site funciona na raiz do domínio
    // (artisan serve, Hostinger) e também em subpasta (http://localhost/geosafra/public no XAMPP).
    experimental: {
        renderBuiltUrl: () => ({ relative: true }),
    },
    resolve: {
        alias: {
            '@': '/resources/js',
        },
    },
});
