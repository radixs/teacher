<?php

namespace App\Support;

use Illuminate\Contracts\Cache\Repository as CacheRepository;
use Illuminate\Support\Facades\Cache;

class FlowEventStream
{
    private const EVENTS_CACHE_KEY = 'flow_events.items';
    private const SEQUENCE_CACHE_KEY = 'flow_events.sequence';
    private const LOCK_KEY = 'flow_events.lock';

    public function __construct(
        private readonly string $cacheStore,
        private readonly string $namespace,
        private readonly int $bufferSize,
        private readonly int $retentionSeconds,
    ) {
    }

    public function publish(array $event): array
    {
        $cache = $this->cache();

        return $cache->lock($this->key(self::LOCK_KEY), 3)->block(1, function () use ($cache, $event) {
            $sequence = (int) $cache->get($this->key(self::SEQUENCE_CACHE_KEY), 0) + 1;
            $prepared = $this->prepare($event, $sequence);
            $events = $cache->get($this->key(self::EVENTS_CACHE_KEY), []);

            if (!is_array($events)) {
                $events = [];
            }

            $events[] = $prepared;

            if (count($events) > $this->bufferSize) {
                $events = array_slice($events, -1 * $this->bufferSize);
            }

            $ttl = now()->addSeconds($this->retentionSeconds);
            $cache->put($this->key(self::SEQUENCE_CACHE_KEY), $sequence, $ttl);
            $cache->put($this->key(self::EVENTS_CACHE_KEY), $events, $ttl);

            return $prepared;
        });
    }

    public function snapshot(): array
    {
        $events = $this->cache()->get($this->key(self::EVENTS_CACHE_KEY), []);

        return is_array($events) ? array_values($events) : [];
    }

    public function recentAfter(int $lastSeenId): array
    {
        return array_values(
            array_filter(
                $this->snapshot(),
                static fn (mixed $event): bool => is_array($event) && (int) ($event['id'] ?? 0) > $lastSeenId,
            ),
        );
    }

    private function prepare(array $event, int $sequence): array
    {
        return [
            'id' => $sequence,
            'timestamp' => (string) ($event['timestamp'] ?? now()->toIso8601String()),
            'service' => (string) ($event['service'] ?? 'unknown'),
            'step' => (string) ($event['step'] ?? 'unknown'),
            'message' => (string) ($event['message'] ?? ''),
            'context' => is_array($event['context'] ?? null) ? $event['context'] : [],
        ];
    }

    private function cache(): CacheRepository
    {
        return Cache::store($this->cacheStore);
    }

    private function key(string $suffix): string
    {
        return $this->namespace . '.' . $suffix;
    }
}
