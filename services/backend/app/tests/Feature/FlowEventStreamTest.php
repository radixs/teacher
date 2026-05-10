<?php

namespace Tests\Feature;

use App\Support\FlowEventStream;
use Tests\TestCase;

class FlowEventStreamTest extends TestCase
{
    public function test_flow_event_ingest_endpoint_accepts_signed_events(): void
    {
        config()->set('flow_events.token', 'test-flow-token');

        $response = $this
            ->withHeader('X-Flow-Event-Token', 'test-flow-token')
            ->postJson('/api/v1/flow-events', [
                'timestamp' => '2026-05-03T13:00:00Z',
                'service' => 'search-agent',
                'step' => 'search.completed',
                'message' => 'Search agent returned a result set.',
                'context' => ['query' => 'rag'],
            ]);

        $response->assertAccepted()->assertJson(['accepted' => true]);
    }

    public function test_flow_event_stream_service_replays_recent_events(): void
    {
        $published = app(FlowEventStream::class)->publish([
            'timestamp' => '2026-05-03T13:01:00Z',
            'service' => 'backend',
            'step' => 'http.sessions.start.received',
            'message' => 'Backend received a start request.',
            'context' => ['goal_preview' => 'Learn RAG'],
        ]);

        $events = app(FlowEventStream::class)->recentAfter($published['id'] - 1);

        $this->assertCount(1, $events);
        $this->assertSame('backend', $events[0]['service']);
        $this->assertSame('http.sessions.start.received', $events[0]['step']);
        $this->assertSame('Backend received a start request.', $events[0]['message']);
    }
}
