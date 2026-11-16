import { t } from './i18n';
import { url } from './url';

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public body: unknown = null,
    ) {
        super(message);
    }
}

/** Token CSRF que o Laravel grava no cookie XSRF-TOKEN (a API interna usa a sessão do usuário). */
function xsrfToken(): string | null {
    const match = document.cookie.match(/(?:^|;\s*)XSRF-TOKEN=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : null;
}

/** fetch JSON para a API interna (/api/v1). Erros problem+json viram ApiError com a mensagem em português. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = xsrfToken();
    let res: Response;
    try {
        res = await fetch(url(path), {
            credentials: 'same-origin',
            ...init,
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...(token ? { 'X-XSRF-TOKEN': token } : {}),
                ...(init.headers ?? {}),
            },
        });
    } catch {
        throw new ApiError(t('Sem conexão. Verifique a internet e tente de novo.'), 0);
    }
    const text = await res.text();
    const body = text ? safeJson(text) : null;
    if (!res.ok) {
        const b = (body ?? {}) as { detail?: string; message?: string; title?: string };
        throw new ApiError(b.detail || b.message || b.title || `Erro ${res.status}`, res.status, body);
    }
    return body as T;
}

function safeJson(text: string): unknown {
    try {
        return JSON.parse(text);
    } catch {
        return { detail: text.slice(0, 200) };
    }
}
