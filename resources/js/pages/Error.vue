<script setup lang="ts">
import { t } from '@/lib/i18n';
import { Head, Link } from '@inertiajs/vue3';
import { computed } from 'vue';
import Icon, { type IconName } from '@/components/Icon.vue';
import AppLayout from '@/layouts/AppLayout.vue';

const props = defineProps<{ status: number }>();

const content = computed(
    () =>
        ({
            403: { title: t('Ação não permitida'), text: t('O exemplo público de referência não pode ser editado nem excluído. Cadastre um talhão próprio para isso.'), icon: 'lock' as IconName },
            404: { title: t('Página não encontrada'), text: t('O endereço não existe ou o talhão foi excluído.'), icon: 'map' as IconName },
            429: { title: t('Muitas tentativas'), text: t('Você fez muitas requisições seguidas. Aguarde um minuto e tente de novo.'), icon: 'clock' as IconName },
            500: { title: t('Algo deu errado'), text: t('Tivemos um problema do nosso lado. Já registramos o erro; tente de novo em instantes.'), icon: 'alert' as IconName },
            503: { title: t('Em manutenção'), text: t('O GeoSafra está passando por uma atualização rápida. Volte em alguns minutos.'), icon: 'refresh' as IconName },
        })[props.status] ?? { title: 'Erro', text: t('Não foi possível concluir a ação.'), icon: 'alert' as IconName },
);
</script>

<template>
    <Head :title="content.title" />
    <AppLayout>
        <div class="mx-auto max-w-lg py-10 text-center sm:py-16">
            <span class="icon-tile-good mx-auto h-16 w-16 rounded-2xl"><Icon :name="content.icon" class="!h-8 !w-8" /></span>
            <p class="mt-6 bg-gradient-to-br from-safra-700 to-safra-950 bg-clip-text text-7xl font-black tracking-tighter text-transparent tabular-nums">{{ status }}</p>
            <h1 class="mt-2 text-2xl font-extrabold tracking-tight">{{ content.title }}</h1>
            <p class="mt-2 text-stone-600">{{ content.text }}</p>
            <div class="mt-8 flex flex-col justify-center gap-2.5 sm:flex-row">
                <Link :href="$url('/')" class="btn-primary"><Icon name="arrowLeft" /> {{ $t('Voltar ao início') }}</Link>
                <Link v-if="status === 403" :href="$url('/talhoes/novo')" class="btn-secondary"><Icon name="plus" /> {{ $t('Cadastrar talhão') }}</Link>
            </div>
        </div>
    </AppLayout>
</template>
