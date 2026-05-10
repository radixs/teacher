<?php

namespace App\Support;

use DateTimeImmutable;
use DateTimeZone;

class FlowLogger
{
    public function __construct(
        private readonly ?string $path,
        private readonly ?FlowEventStream $stream = null,
    )
    {
    }

    public function log(string $service, string $step, string $message, array $context = []): void
    {
        $timestamp = (new DateTimeImmutable('now', new DateTimeZone('UTC')))->format(DATE_ATOM);
        $sanitizedContext = $this->sanitize($context);

        if ($this->path) {
            $directory = dirname($this->path);
            if (!is_dir($directory)) {
                @mkdir($directory, 0777, true);
            }
            if (!file_exists($this->path)) {
                @touch($this->path);
            }
            @chmod($this->path, 0666);

            $line = sprintf('%s | %s | %s | %s', $timestamp, $service, $step, $message);

            if ($sanitizedContext !== []) {
                $line .= ' | ' . json_encode($sanitizedContext, JSON_UNESCAPED_SLASHES);
            }

            @file_put_contents($this->path, $line . PHP_EOL, FILE_APPEND | LOCK_EX);
        }

        if ($this->stream !== null) {
            $this->stream->publish([
                'timestamp' => $timestamp,
                'service' => $service,
                'step' => $step,
                'message' => $message,
                'context' => $sanitizedContext,
            ]);
        }
    }

    private function sanitize(mixed $value): mixed
    {
        if (is_string($value)) {
            return mb_strlen($value) > 240 ? mb_substr($value, 0, 237) . '...' : $value;
        }

        if (is_array($value)) {
            $sanitized = [];
            foreach ($value as $key => $item) {
                $sanitized[$key] = $this->sanitize($item);
            }

            return $sanitized;
        }

        if (is_object($value)) {
            return $this->sanitize((array) $value);
        }

        return $value;
    }
}
