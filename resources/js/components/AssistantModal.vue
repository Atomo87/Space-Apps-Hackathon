<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import AssistantPanel from './AssistantPanel.vue';
import Icon from './Icon.vue';

/** "Pergunte à IA" em uma janela (modal). O histórico de perguntas é mantido entre aberturas. */
const props = defineProps<{ fieldId: number; open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const dialog = ref<HTMLElement | null>(null);
const closeBtn = ref<HTMLButtonElement | null>(null);
let lastFocus: HTMLElement | null = null;

function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
        e.preventDefault();
        emit('close');
    } else if (e.key === 'Tab' && dialog.value) {
        // Mantém o foco dentro da janela.
        const items = [...dialog.value.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), [href], summary')];
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }
}

watch(
    () => props.open,
    async (open) => {
        if (open) {
            lastFocus = document.activeElement as HTMLElement | null;
            document.addEventListener('keydown', onKey);
            document.body.style.overflow = 'hidden';
            await nextTick();
            (dialog.value?.querySelector<HTMLInputElement>('#ask-input') ?? closeBtn.value)?.focus();
        } else {
            document.removeEventListener('keydown', onKey);
            document.body.style.overflow = '';
            lastFocus?.focus?.();
        }
    },
);

onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKey);
    document.body.style.overflow = '';
});
</script>

<template>
    <Teleport to="body">
        <Transition enter-active-class="transition duration-150 ease-out" enter-from-class="opacity-0" leave-active-class="transition duration-100 ease-in" leave-to-class="opacity-0">
            <div v-show="open" class="fixed inset-0 z-[65] flex items-end justify-center bg-safra-950/50 backdrop-blur-sm sm:items-center sm:p-6 print:hidden" @mousedown.self="emit('close')">
                <div
                    ref="dialog"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="assistant-title"
                    class="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-t-3xl bg-stone-50 shadow-[var(--shadow-lift)] sm:rounded-3xl"
                >
                    <div class="flex items-center justify-between gap-3 border-b border-stone-200 bg-white px-5 py-3.5">
                        <h2 id="assistant-title" class="flex items-center gap-2 font-bold text-stone-900">
                            <span class="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-safra-600 to-safra-900 text-lime-300"><Icon name="message" class="h-4 w-4" /></span>
                            {{ $t('Pergunte à IA') }}
                        </h2>
                        <button ref="closeBtn" type="button" class="grid h-9 w-9 place-items-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-900" :aria-label="$t('Fechar')" @click="emit('close')">
                            <Icon name="x" class="h-5 w-5" />
                        </button>
                    </div>
                    <div class="overflow-y-auto overscroll-contain p-4 sm:p-5">
                        <AssistantPanel :field-id="fieldId" />
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>
