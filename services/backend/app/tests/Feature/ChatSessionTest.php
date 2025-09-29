<?php

namespace Tests\Feature;

use App\Providers\RagServiceProvider;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class ChatSessionTest extends TestCase
{
    public function test_start_session_delegates_to_orchestrator(): void
    {
        Http::fake([
            'rag-orchestrator*/sessions' => Http::response(['id' => 'session-123'], 200),
        ]);

        $response = $this->postJson('/api/v1/sessions', [
            'goal' => 'Learn ESRE',
            'profile' => ['experience' => 'PHP developer'],
        ]);

        $response->assertOk()->assertJson(['id' => 'session-123']);
    }
}
