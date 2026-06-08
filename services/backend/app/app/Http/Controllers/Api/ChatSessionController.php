<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\Rag\RagClient;
use App\Support\FlowLogger;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ChatSessionController extends Controller
{
    public function __construct(
        private RagClient $ragClient,
        private FlowLogger $flowLogger,
    )
    {
    }

    public function start(Request $request): JsonResponse
    {
        $this->flowLogger->log(
            'backend',
            'http.sessions.start.received',
            'Backend received a request from the frontend to start a new learning session.',
            [
                'goal_preview' => $request->input('goal'),
                'has_profile' => $request->filled('profile'),
            ],
        );

        $validated = $request->validate([
            'goal' => ['required', 'string'],
            'profile' => ['array'],
        ]);

        $this->flowLogger->log(
            'backend',
            'http.sessions.start.validated',
            'Backend validated the new-session payload and will delegate to RagClient.',
            [
                'goal_preview' => $validated['goal'],
                'has_profile' => !empty($validated['profile']),
            ],
        );

        try {
            $response = $this->ragClient->startSession($validated);
        } catch (ConnectionException $exc) {
            return $this->ragUnavailableResponse(
                step: 'http.sessions.start.failed',
                message: 'Backend could not start the session because rag-orchestrator did not respond in time.',
                sessionId: null,
                error: $exc->getMessage(),
            );
        }
        $session = $response->json();

        $this->flowLogger->log(
            'backend',
            'http.sessions.start.completed',
            'Backend is returning the initialized session back to the frontend.',
            [
                'session_id' => $session['id'] ?? null,
                'phase' => $session['phase'] ?? null,
            ],
        );

        return response()->json($session, $response->status());
    }

    public function message(string $sessionId, Request $request): JsonResponse
    {
        $this->flowLogger->log(
            'backend',
            'http.sessions.message.received',
            'Backend received a learner message from the frontend.',
            [
                'session_id' => $sessionId,
                'message_preview' => $request->input('message'),
                'has_metadata' => $request->filled('metadata'),
            ],
        );

        $validated = $request->validate([
            'message' => ['required', 'string'],
            'metadata' => ['array'],
        ]);

        $this->flowLogger->log(
            'backend',
            'http.sessions.message.validated',
            'Backend validated the learner message and will delegate to RagClient.',
            [
                'session_id' => $sessionId,
                'message_preview' => $validated['message'],
            ],
        );

        try {
            $response = $this->ragClient->sendMessage($sessionId, $validated);
        } catch (ConnectionException $exc) {
            return $this->ragUnavailableResponse(
                step: 'http.sessions.message.failed',
                message: 'Backend could not complete the learner message because rag-orchestrator did not respond in time.',
                sessionId: $sessionId,
                error: $exc->getMessage(),
            );
        }
        $responseBody = $response->json();

        $this->flowLogger->log(
            'backend',
            'http.sessions.message.completed',
            'Backend is returning the assistant response back to the frontend.',
            [
                'session_id' => $sessionId,
                'phase' => $responseBody['session']['phase'] ?? null,
                'assistant_stage' => $responseBody['last_message']['metadata']['stage'] ?? null,
            ],
        );

        return response()->json($responseBody, $response->status());
    }

    public function show(string $sessionId): JsonResponse
    {
        $this->flowLogger->log(
            'backend',
            'http.sessions.show.received',
            'Backend received a request to load an existing session for resume.',
            [
                'session_id' => $sessionId,
            ],
        );

        try {
            $response = $this->ragClient->fetchSession($sessionId);
        } catch (ConnectionException $exc) {
            return $this->ragUnavailableResponse(
                step: 'http.sessions.show.failed',
                message: 'Backend could not load the stored session because rag-orchestrator did not respond in time.',
                sessionId: $sessionId,
                error: $exc->getMessage(),
            );
        }
        $session = $response->json();

        $this->flowLogger->log(
            'backend',
            'http.sessions.show.completed',
            'Backend is returning the stored session payload to the frontend.',
            [
                'session_id' => $session['id'] ?? $sessionId,
                'phase' => $session['phase'] ?? null,
            ],
        );

        return response()->json($session, $response->status());
    }

    private function ragUnavailableResponse(string $step, string $message, ?string $sessionId, string $error): JsonResponse
    {
        $this->flowLogger->log(
            'backend',
            $step,
            $message,
            [
                'session_id' => $sessionId,
                'error' => $error,
            ],
        );

        return response()->json(
            [
                'message' => $message,
                'upstream' => 'rag-orchestrator',
            ],
            504,
        );
    }
}
