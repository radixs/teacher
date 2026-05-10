<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Support\FlowEventStream;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\StreamedResponse;

class FlowEventController extends Controller
{
    public function __construct(private readonly FlowEventStream $flowEventStream)
    {
    }

    public function store(Request $request): JsonResponse
    {
        $expectedToken = (string) config('flow_events.token', '');
        $providedToken = (string) $request->header('X-Flow-Event-Token', '');

        abort_if($expectedToken !== '' && !hash_equals($expectedToken, $providedToken), 403);

        $validated = $request->validate([
            'timestamp' => ['nullable', 'string'],
            'service' => ['required', 'string'],
            'step' => ['required', 'string'],
            'message' => ['required', 'string'],
            'context' => ['sometimes', 'array'],
        ]);

        $event = $this->flowEventStream->publish($validated);

        return response()->json(
            [
                'accepted' => true,
                'event_id' => $event['id'],
            ],
            202,
        );
    }

    public function stream(Request $request): StreamedResponse
    {
        $lastSeenId = max(
            0,
            (int) ($request->header('Last-Event-ID') ?: $request->query('after', 0)),
        );
        $singlePass = $request->boolean('once');

        $pollIntervalMs = max(100, (int) config('flow_events.stream_poll_interval_ms', 500));
        $timeoutSeconds = max(5, (int) config('flow_events.stream_timeout_seconds', 25));

        return response()->stream(function () use ($lastSeenId, $pollIntervalMs, $timeoutSeconds, $singlePass): void {
            $cursor = $lastSeenId;
            $deadline = microtime(true) + $timeoutSeconds;
            $lastHeartbeat = microtime(true);

            if ($cursor === 0) {
                foreach ($this->flowEventStream->snapshot() as $event) {
                    $this->emit('flow', $event);
                    $cursor = (int) ($event['id'] ?? $cursor);
                    $lastHeartbeat = microtime(true);
                }
            }

            while (connection_aborted() === 0 && microtime(true) < $deadline) {
                $sentEvent = false;

                foreach ($this->flowEventStream->recentAfter($cursor) as $event) {
                    $this->emit('flow', $event);
                    $cursor = (int) ($event['id'] ?? $cursor);
                    $sentEvent = true;
                    $lastHeartbeat = microtime(true);
                }

                if ($sentEvent) {
                    if ($singlePass) {
                        return;
                    }
                    continue;
                }

                if ($singlePass) {
                    return;
                }

                if ((microtime(true) - $lastHeartbeat) >= 5) {
                    $this->emit('heartbeat', ['timestamp' => now()->toIso8601String()]);
                    $lastHeartbeat = microtime(true);
                }

                usleep($pollIntervalMs * 1000);
            }
        }, 200, [
            'Cache-Control' => 'no-cache, no-transform',
            'Connection' => 'keep-alive',
            'Content-Type' => 'text/event-stream',
            'X-Accel-Buffering' => 'no',
        ]);
    }

    private function emit(string $eventName, array $payload): void
    {
        if (array_key_exists('id', $payload)) {
            echo 'id: ' . $payload['id'] . "\n";
        }

        echo 'event: ' . $eventName . "\n";
        echo 'data: ' . json_encode($payload, JSON_UNESCAPED_SLASHES) . "\n\n";

        @ob_flush();
        flush();
    }
}
