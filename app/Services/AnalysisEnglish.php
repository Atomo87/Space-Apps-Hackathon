<?php

namespace App\Services;

/** Localizes analysis text returned by older geo-service instances. */
class AnalysisEnglish
{
    private const TEXT_FIELDS = [
        'text', 'title', 'name', 'label', 'focus', 'note', 'notes', 'source_note', 'grid_note',
        'dataset', 'datasets', 'period', 'resolution', 'citation', 'relief_class',
        'driest', 'wettest', 'disclaimer', 'rationale', 'explanation', 'benefits',
        'information_gaps', 'local_review_risks', 'conflicts', 'warnings', 'human_judgment',
        'reasons', 'risks', 'crops', 'crop_names', 'current_crops',
    ];

    private array $messages;

    private array $templates = [];

    public function __construct()
    {
        $catalog = json_decode(file_get_contents(database_path('data/analysis-en-US.json')), true, 512, JSON_THROW_ON_ERROR);
        $this->messages = $catalog;

        foreach ($catalog as $original => $english) {
            $source = preg_replace('/^; /', '', trim($original));
            $translation = preg_replace('/^; /', '', trim($english));
            if (! preg_match('/\{\d+\}/', $source)) {
                $this->messages[$source] ??= $translation;
                $this->messages[mb_strtolower($source)] ??= mb_strtolower(mb_substr($translation, 0, 1)).mb_substr($translation, 1);
                continue;
            }
            $this->addTemplate($original, $english);
            if ($source !== $original) {
                $this->addTemplate($source, $translation);
            }
        }

        usort($this->templates, fn ($a, $b) => strlen($b[0]) <=> strlen($a[0]));
    }

    private function addTemplate(string $original, string $english): void
    {
        $parts = preg_split('/\{(\d+)\}/', $original, -1, PREG_SPLIT_DELIM_CAPTURE);
        $pattern = preg_quote($parts[0], '~');
        for ($i = 1; $i < count($parts); $i += 2) {
            $next = $parts[$i + 1];
            $capture = $next === '' && isset($parts[$i + 2]) ? '[+−-]?' : '.*?';
            $pattern .= '(?<arg'.$parts[$i].'>'.$capture.')'.preg_quote($next, '~');
        }
        $this->templates[] = [$parts[0], '~\A'.$pattern.'\z~u', $english];
    }

    public function response(array $data): array
    {
        return $this->walk($data, null);
    }

    private function walk(array $data, ?string $parent): array
    {
        foreach ($data as $key => $value) {
            $field = is_string($key) ? $key : $parent;
            if (is_array($value)) {
                $data[$key] = $this->walk($value, $field);
            } elseif (is_string($value) && in_array($field, self::TEXT_FIELDS, true)) {
                $data[$key] = $this->translate($value);
            }
        }

        return $data;
    }

    private function translate(string $text, int $depth = 0): string
    {
        if (isset($this->messages[$text])) {
            return $this->messages[$text];
        }
        if ($depth >= 6 || $text === '') {
            return $text;
        }

        $sentences = preg_split('/(?<=[.!?]) (?=[\p{Lu}\d(])/u', $text);
        if (count($sentences) > 1) {
            $english = implode(' ', array_map(fn ($sentence) => $this->translate($sentence, $depth + 1), $sentences));
            if ($english !== $text) {
                return $english;
            }
        }

        foreach ($this->templates as [$prefix, $pattern, $english]) {
            if (str_starts_with($text, $prefix) && preg_match($pattern, $text, $matches)) {
                return preg_replace_callback('/\{(\d+)\}/', function (array $placeholder) use ($matches, $depth) {
                    $arg = trim($matches['arg'.$placeholder[1]]);

                    return preg_match('/\A[+−-]?\d+,\d+\z/u', $arg)
                        ? str_replace(',', '.', $arg)
                        : $this->translate($arg, $depth + 1);
                }, $english);
            }
        }

        // Older responses join separately formatted sentences, crop names and months.
        foreach (['/(; )/u', '/(, )/u', '/( e | → | \+ )/u'] as $separator) {
            $parts = preg_split($separator, $text, -1, PREG_SPLIT_DELIM_CAPTURE);
            if (count($parts) > 1) {
                $english = implode('', array_map(fn ($part) => $this->translate($part, $depth + 1), $parts));
                if ($english !== str_replace(' e ', ' and ', $text)) {
                    return $english;
                }
            }
        }

        return str_ends_with($text, '.') ? $this->translate(substr($text, 0, -1), $depth + 1).'.' : $text;
    }
}
