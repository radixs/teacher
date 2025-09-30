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
        return $this->http->post('/v1/sessions', $payload)->json();
    }

    public function sendMessage(string $sessionId, array $payload): array
    {
        return $this->http->post("/v1/sessions/{$sessionId}", $payload)->json();
    }

    public function fetchSession(string $sessionId): array
    {
        return $this->http->get("/v1/sessions/{$sessionId}")->json();
    }

    public function getElasticsearchConfig(): array
    {
        return $this->elasticsearchConfig;
    }
}
