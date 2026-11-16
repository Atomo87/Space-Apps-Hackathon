<script setup lang="ts">
import { confirmState, settleConfirm } from '@/lib/confirm';
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import Icon from './Icon.vue';

const panel = ref<HTMLElement | null>(null);
const cancelBtn = ref<HTMLButtonElement | null>(null);
const danger = computed(() => (confirmState.opts.tone ?? 'primary') === 'danger');
let lastFocus: HTMLElement | null = null;

function onKey(e: KeyboardEvent) {
    if (!confirmState.open) return;
    if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        settleConfirm(false);
    } else if (e.key === 'Tab' && panel.value) {
        // Mantém o foco dentro do modal.
        const items = [...panel.value.querySelectorAll<HTMLElement>('button')];
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first?.focus();
        }
    }
}

watch(
    () => confirmState.open,
    async (open) => {
        if (open) {
            lastFocus = document.activeElement as HTMLElement | null;
            document.addEventListener('keydown', onKey, true);
            document.body.style.overflow = 'hidden';
            await nextTick();
            cancelBtn.value?.focus(); // o padrão seguro é cancelar
        } else {
            document.removeEventListener('keydown', onKey, true);
            document.body.style.overflow = '';
            lastFocus?.focus?.();
        }
    },
);

onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKey, true);
    document.body.style.overflow = '';
});
</script>

<template>
    <Teleport to="body">
        <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0" leave-active-class="transition duration-100 ease-in" leave-to-class="opacity-0">
            <div v-if="confirmState.open" class="fixed inset-0 z-[70] flex items-end justify-center bg-safra-950/50 p-4 backdrop-blur-sm sm:items-center print:hidden" @mousedown.self="settleConfirm(false)">
                <div
                    ref="panel"
                    role="alertdialog"
                    aria-modal="true"
                    aria-labelledby="confirm-title"
                    :aria-describedby="confirmState.opts.message ? 'confirm-message' : undefined"
                    class="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-6 shadow-[var(--shadow-lift)]"
                >
                    <div class="flex items-start gap-4">
                        <span class="grid h-11 w-11 shrink-0 place-items-center rounded-full" :class="danger ? 'bg-red-50 text-red-700' : 'bg-safra-50 text-safra-800'">
                            <Icon :name="confirmState.opts.icon ?? (danger ? 'alert' : 'info')" class="h-5 w-5" />
                        </span>
                        <div class="min-w-0 space-y-1.5">
                            <h2 id="confirm-title" class="text-lg font-bold text-stone-900">{{ confirmState.opts.title }}</h2>
                            <p v-if="confirmState.opts.message" id="confirm-message" class="text-sm leading-relaxed text-stone-600">{{ confirmState.opts.message }}</p>
                        </div>
                    </div>
                    <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                        <button ref="cancelBtn" type="button" class="btn-secondary" @click="settleConfirm(false)">{{ confirmState.opts.cancelText ?? $t('Cancelar') }}</button>
                        <button type="button" :class="danger ? 'btn-danger' : 'btn-primary'" @click="settleConfirm(true)">{{ confirmState.opts.confirmText ?? $t('Confirmar') }}</button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>
