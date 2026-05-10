<?php

namespace App\Services\Rag;

use App\Support\FlowLogger;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;

class RagClient
{
    public function __construct(
        private PendingRequest $http,
        private array $elasticsearchConfig,
        private FlowLogger $flowLogger,
    ) {
    }

    public function startSession(array $payload): array
    {
        $this->flowLogger->log(
            'backend',
            'rag.start_session.dispatch',
            'Backend is sending a session-start request to rag-orchestrator.',
            [
                'endpoint' => '/v1/sessions',
                'goal' => $payload['goal'] ?? null,
                'has_profile' => !empty($payload['profile']),
            ],
        );

        $response = $this->http->post('/v1/sessions', $payload);
        $data = $response->json();

        $this->flowLogger->log(
            'backend',
            'rag.start_session.response',
            'Backend received the session-start response from rag-orchestrator.',
            [
                'status' => $response->status(),
                'session_id' => $data['id'] ?? null,
                'phase' => $data['phase'] ?? null,
            ],
        );

        return $data;
    }

    public function sendMessage(string $sessionId, array $payload): array
    {
        $this->flowLogger->log(
            'backend',
            'rag.send_message.dispatch',
            'Backend is forwarding a learner message to rag-orchestrator.',
            [
                'endpoint' => "/v1/sessions/{$sessionId}",
                'session_id' => $sessionId,
                'message_preview' => $payload['message'] ?? null,
                'has_metadata' => !empty($payload['metadata']),
            ],
        );

        $response = $this->http->post("/v1/sessions/{$sessionId}", $payload);
        $data = $response->json();

        $this->flowLogger->log(
            'backend',
            'rag.send_message.response',
            'Backend received the learner-message response from rag-orchestrator.',
            [
                'status' => $response->status(),
                'session_id' => $sessionId,
                'phase' => $data['session']['phase'] ?? null,
            ],
        );

        return $data;
    }

    public function fetchSession(string $sessionId): array
    {
        $this->flowLogger->log(
            'backend',
            'rag.fetch_session.dispatch',
            'Backend is requesting a stored session from rag-orchestrator.',
            [
                'endpoint' => "/v1/sessions/{$sessionId}",
                'session_id' => $sessionId,
            ],
        );

        $response = $this->http->get("/v1/sessions/{$sessionId}");
        $data = $response->json();

        $this->flowLogger->log(
            'backend',
            'rag.fetch_session.response',
            'Backend received the stored session payload from rag-orchestrator.',
            [
                'status' => $response->status(),
                'session_id' => $data['id'] ?? $sessionId,
                'phase' => $data['phase'] ?? null,
            ],
        );

        return $data;
    }

    public function getElasticsearchConfig(): array
    {
        return $this->elasticsearchConfig;
    }
}
