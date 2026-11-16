import type { PageProps as InertiaPageProps } from '@inertiajs/core';

export interface GlossaryEntry {
    term: string;
    text: string;
}

export interface AuthUser {
    id: number;
    name: string;
    email: string;
}

export interface SharedProps {
    app: { name: string; disclaimer: string; footerWarning: string; powerCitation: string };
    auth: { user: AuthUser | null };
    flash: { success: string | null; error: string | null };
    glossary: Record<string, GlossaryEntry>;
    errors: Record<string, string>;
    [key: string]: unknown;
}

declare module '@inertiajs/core' {
    interface PageProps extends InertiaPageProps, SharedProps {}
}

declare module 'vue' {
    interface ComponentCustomProperties {
        $page: import('@inertiajs/core').Page<SharedProps>;
    }
}
