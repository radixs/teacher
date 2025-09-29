<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\Rag\RagClient;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ChatSessionController extends Controller
{
    public function __construct(private RagClient $ragClient)
    {
    }

    public function start(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'goal' => ['required', 'string'],
            'profile' => ['array'],
        ]);

        $session = $this->ragClient->startSession($validated);

        return response()->json($session);
    }

    public function message(string $sessionId, Request $request): JsonResponse
    {
        $validated = $request->validate([
            'message' => ['required', 'string'],
            'metadata' => ['array'],
        ]);

        $response = $this->ragClient->sendMessage($sessionId, $validated);

        return response()->json($response);
    }

    public function show(string $sessionId): JsonResponse
    {
        $session = $this->ragClient->fetchSession($sessionId);

        return response()->json($session);
    }
}
