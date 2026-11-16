<?php

use App\Jobs\AnalyzeFieldJob;
use App\Models\AssistantKnowledgeEntry;
use App\Models\Farm;
use App\Models\Field;
use App\Models\User;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Schedule;
use Illuminate\Support\Facades\Validator;

Artisan::command('geosafra:knowledge:publish {file}', function (string $file) {
    $contents = is_file($file) ? @file_get_contents($file) : false;
    $entries = $contents === false ? null : json_decode($contents, true);
    if (! is_array($entries) || ! array_is_list($entries)) {
        $this->error('Informe um arquivo JSON legível com uma lista de entradas.');

        return 1;
    }

    $validator = Validator::make(['entries' => $entries], [
        'entries' => ['required', 'array', 'min:1'],
        'entries.*' => ['required', 'array:locale,slug,question,aliases,answer,source,source_url'],
        'entries.*.locale' => ['required', 'in:en-US,pt-BR'],
        'entries.*.slug' => ['required', 'string', 'max:120', 'regex:/^[a-z0-9]+(-[a-z0-9]+)*$/'],
        'entries.*.question' => ['required', 'string', 'min:3', 'max:500'],
        'entries.*.aliases' => ['nullable', 'array', 'list', 'max:20'],
        'entries.*.aliases.*' => ['required', 'string', 'min:3', 'max:500'],
        'entries.*.answer' => ['required', 'string', 'max:5000'],
        'entries.*.source' => ['required', 'string', 'max:255'],
        'entries.*.source_url' => ['nullable', 'url:http,https', 'max:2048'],
    ]);
    if ($validator->fails()) {
        foreach ($validator->errors()->all() as $message) {
            $this->error($message);
        }

        return 1;
    }

    DB::transaction(function () use ($validator): void {
        foreach ($validator->validated()['entries'] as $entry) {
            AssistantKnowledgeEntry::updateOrCreate(
                ['locale' => $entry['locale'], 'slug' => $entry['slug']],
                $entry + ['aliases' => null, 'source_url' => null, 'published_at' => now()],
            );
        }
    });
    $this->info(count($entries).' entrada(s) publicada(s).');

    return 0;
})->purpose('Publica perguntas e respostas revisadas na base de conhecimento do GeoSafra.');

Artisan::command('geosafra:analyze {field}', function (int $field) {
    $model = Field::findOrFail($field);
    $this->info("Analisando o talhão {$model->id} ({$model->name}) — o geo-service vai consultar a NASA POWER…");
    try {
        AnalyzeFieldJob::dispatchSync($model->id);
    } catch (Throwable $e) {
        $this->error($e->getMessage());
    }
    $model->refresh();
    $this->info("Status: {$model->status} {$model->status_message}");
})->purpose('Processa um talhão de forma síncrona (teste da integração Laravel → geo-service → NASA POWER).');

Artisan::command('geosafra:ping', function () {
    $url = config('geosafra.geo_service.url');
    $this->info("GET $url/health");
    $this->line(Http::timeout(70)->get("$url/health")->body());
})->purpose('Verifica se o geo-service responde.');

Artisan::command('geosafra:claim {email}', function (string $email) {
    $user = User::where('email', mb_strtolower($email))->first();
    if (! $user) {
        $this->error("Nenhuma conta com o e-mail {$email}. Crie a conta em /cadastro primeiro.");

        return 1;
    }
    $count = Farm::whereNull('user_id')->where('is_demo', false)->update(['user_id' => $user->id]);
    $this->info("{$count} propriedade(s) sem dono foram atribuídas a {$user->name} <{$user->email}>.");

    return 0;
})->purpose('Atribui a uma conta as propriedades criadas antes do login existir (dados sem dono).');

// Mantém o geo-service do Render (plano gratuito) acordado.
// Na Hostinger: hPanel > Avançado > Cron Jobs, a cada minuto: php /home/USUARIO/geosafra/artisan schedule:run
Schedule::call(function () {
    try {
        Http::timeout(70)->get(config('geosafra.geo_service.url').'/health');
    } catch (Throwable) {
        // só um ping
    }
})->everyTenMinutes()->name('geo-service-ping')->withoutOverlapping();
