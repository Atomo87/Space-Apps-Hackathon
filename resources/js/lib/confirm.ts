import type { IconName } from '@/components/Icon.vue';
import { reactive } from 'vue';

/** Confirmação antes de operações que gravam, apagam ou encerram algo. Abre o ConfirmDialog (montado no AppLayout). */
export interface ConfirmOptions {
    title: string;
    message?: string;
    confirmText?: string;
    cancelText?: string;
    /** danger = ação que apaga ou não tem volta; primary = ação comum */
    tone?: 'danger' | 'primary';
    icon?: IconName;
}

export const confirmState = reactive<{ open: boolean; opts: ConfirmOptions; resolve: ((ok: boolean) => void) | null }>({
    open: false,
    opts: { title: '' },
    resolve: null,
});

/** Mostra o modal e resolve true se a pessoa confirmar. */
export function confirmAction(opts: ConfirmOptions): Promise<boolean> {
    confirmState.resolve?.(false); // um pedido novo cancela o anterior
    return new Promise((resolve) => {
        confirmState.opts = opts;
        confirmState.resolve = resolve;
        confirmState.open = true;
    });
}

export function settleConfirm(ok: boolean): void {
    const resolve = confirmState.resolve;
    confirmState.open = false;
    confirmState.resolve = null;
    resolve?.(ok);
}
