<?php

namespace App\Services\Rag;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

class RagClient
{
    public function __construct(
        private PendingRequest $http,
        private array $elasticsearchConfig,
    ) {
    }

    public function startSession(array $payload): array
    {
        // TODO: wire to orchestrator once implemented.
        return $this->http->post('/sessions', $payload)->json();
    }

    public function sendMessage(string $sessionId, array $payload): array
    {
        return $this->http->post("/sessions/{$sessionId}/messages", $payload)->json();
    }

    public function fetchSession(string $sessionId): array
    {
        return $this->http->get("/sessions/{$sessionId}")->json();
    }

    public function getElasticsearchConfig(): array
    {
        return $this->elasticsearchConfig;
    }
}
