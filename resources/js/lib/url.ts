/**
 * O app pode rodar na raiz do domínio (artisan serve, Hostinger) ou numa subpasta
 * (http://localhost/geosafra/public no XAMPP). O Blade informa o prefixo na meta "base-path".
 */
export const BASE_PATH = (document.querySelector<HTMLMetaElement>('meta[name="base-path"]')?.content ?? '').replace(/\/$/, '');

/** "/talhoes/3" → "/geosafra/public/talhoes/3" (ou igual, na raiz). Links externos e âncoras passam direto. */
export function url(path: string): string {
    return path.startsWith('/') && !path.startsWith('//') ? `${BASE_PATH}${path}` : path;
}

/** Caminho da página sem o prefixo, para comparar com rotas ("/metodologia"). */
export function appPath(pageUrl: string): string {
    const p = pageUrl.split('?')[0];
    return BASE_PATH && p.startsWith(BASE_PATH) ? p.slice(BASE_PATH.length) || '/' : p;
}
