<?php

return [
    'cache_store' => env('FLOW_EVENT_CACHE_STORE', 'flow_events'),
    'namespace' => env('FLOW_EVENT_NAMESPACE', 'default'),
    'buffer_size' => (int) env('FLOW_EVENT_BUFFER_SIZE', 40),
    'retention_seconds' => (int) env('FLOW_EVENT_RETENTION_SECONDS', 900),
    'stream_poll_interval_ms' => (int) env('FLOW_EVENT_STREAM_POLL_INTERVAL_MS', 500),
    'stream_timeout_seconds' => (int) env('FLOW_EVENT_STREAM_TIMEOUT_SECONDS', 25),
    'token' => env('FLOW_EVENT_TOKEN'),
];
