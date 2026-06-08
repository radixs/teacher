<?php

namespace App\Services\Rag;

use App\Support\FlowLogger;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\Response;

class RagClient
{
    public function __construct(
        private PendingRequest $http,
        private array $elasticsearchConfig,
        private FlowLogger $flowLogger,
    ) {
    }

    public function startSession(array $payload): Response
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
        $this->flowLogger->log(
            'backend',
            'rag.start_session.response',
            'Backend received the session-start response from rag-orchestrator.',
            [
                'status' => $response->status(),
                'session_id' => $response->json('id'),
                'phase' => $response->json('phase'),
            ],
        );

        return $response;
    }

    public function sendMessage(string $sessionId, array $payload): Response
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
        $this->flowLogger->log(
            'backend',
            'rag.send_message.response',
            'Backend received the learner-message response from rag-orchestrator.',
            [
                'status' => $response->status(),
                'session_id' => $sessionId,
                'phase' => $response->json('session.phase'),
            ],
        );

        return $response;
    }

    public function fetchSession(string $sessionId): Response
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
        $this->flowLogger->log(
            'backend',
            'rag.fetch_session.response',
            'Backend received the stored session payload from rag-orchestrator.',
            [
                'status' => $response->status(),
                'session_id' => $response->json('id') ?? $sessionId,
                'phase' => $response->json('phase'),
            ],
        );

        return $response;
    }

    public function getElasticsearchConfig(): array
    {
        return $this->elasticsearchConfig;
    }
}
