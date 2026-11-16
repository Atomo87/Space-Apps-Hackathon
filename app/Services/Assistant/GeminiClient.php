<?php

namespace App\Services\Assistant;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use RuntimeException;

/**
 * Cliente mínimo do Google Gemini (generateContent) com saída JSON validada por esquema.
 * Configuração: GEMINI_API_KEY, GEMINI_MODEL e, opcional, GEMINI_ENDPOINT.
 */
class GeminiClient
{
    public function configured(): bool
    {
        return (bool) config('geosafra.ai.enabled') && config('geosafra.ai.key') !== '' && config('geosafra.ai.model') !== '';
    }

    public function model(): string
    {
        return (string) config('geosafra.ai.model');
    }

    /**
     * @param  array<string,mixed>  $schema  esquema (subconjunto OpenAPI) da resposta JSON
     * @return array<string,mixed>
     */
    public function json(string $system, string $user, array $schema): array
    {
        $url = rtrim((string) config('geosafra.ai.endpoint'), '/').'/models/'.$this->model().':generateContent';
        try {
            $res = Http::timeout(60)->connectTimeout(10)
                ->withHeaders(['x-goog-api-key' => (string) config('geosafra.ai.key')])
                ->post($url, [
                    'systemInstruction' => ['parts' => [['text' => $system]]],
                    'contents' => [['role' => 'user', 'parts' => [['text' => $user]]]],
                    'generationConfig' => [
                        'temperature' => 0.2,
                        'responseMimeType' => 'application/json',
                        'responseSchema' => $schema,
                        'maxOutputTokens' => 4096,
                    ],
                ]);
        } catch (ConnectionException $e) {
            throw new RuntimeException('Gemini fora do ar ou sem conexão.', 0, $e);
        }

        if (! $res->successful()) {
            // Nunca repassa a chave; só o motivo devolvido pelo Google.
            throw new RuntimeException('Gemini respondeu HTTP '.$res->status().': '.mb_substr((string) $res->json('error.message', ''), 0, 200));
        }
        $cand = $res->json('candidates.0');
        $finish = $cand['finishReason'] ?? null;
        if ($finish && ! in_array($finish, ['STOP', 'MAX_TOKENS'], true)) {
            throw new RuntimeException("Gemini interrompeu a resposta ({$finish}).");
        }
        $text = collect($cand['content']['parts'] ?? [])->pluck('text')->filter()->implode('');
        $data = json_decode($text, true);
        if (! is_array($data)) {
            throw new RuntimeException('Gemini devolveu um JSON inválido.');
        }

        return $data;
    }
}
