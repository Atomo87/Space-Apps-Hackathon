import english from '../locales/en-US.json';

export type Locale = 'en-US' | 'pt-BR';
export const locale: Locale = document.documentElement.lang === 'pt-BR' ? 'pt-BR' : 'en-US';
const regions = new Intl.DisplayNames(locale, { type: 'region' });

export function countryName(code: string): string {
    return regions.of(code) ?? code;
}

const messages: Readonly<Record<string, string>> = english;

export function t(message: string, context?: string): string {
    if (locale === 'pt-BR') return message;
    const key = context ? `${context}:${message}` : message;
    return Object.prototype.hasOwnProperty.call(messages, key) ? messages[key] : message;
}

export function tf(message: string, values: Record<string, string | number>): string {
    return t(message).replace(/\{(\w+)\}/g, (token, key: string) => String(values[key] ?? token));
}

export function setLocale(value: Locale): void {
    if ((value !== 'pt-BR' && value !== 'en-US') || value === locale) return;
    const path = document.querySelector<HTMLMetaElement>('meta[name="base-path"]')?.content || '/';
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `geosafra_locale=${value}; Path=${path}; Max-Age=31536000; SameSite=Lax${secure}`;
    window.location.reload();
}
