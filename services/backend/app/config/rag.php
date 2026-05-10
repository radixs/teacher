<?php

return [
    'orchestrator_url' => env('RAG_ORCHESTRATOR_URL', 'http://rag-orchestrator:9000'),
    'request_timeout' => (int) env('RAG_HTTP_TIMEOUT', 180),
    'connect_timeout' => (int) env('RAG_HTTP_CONNECT_TIMEOUT', 5),
    'llm_engine_url' => env('LLM_ENGINE_URL', 'http://llm-engine:8000'),
    'embedding_service_url' => env('EMBEDDING_SERVICE_URL', 'http://embedding-worker:9100'),
    'search_agent_url' => env('SEARCH_AGENT_URL', 'http://search-agent:9205'),

    'elasticsearch' => [
        'host' => env('ELASTICSEARCH_URL', 'http://elasticsearch:9200'),
        'indices' => [
            'user_profiles' => env('ELASTICSEARCH_INDEX_USER_PROFILES', 'user_profiles'),
            'knowledge_snapshots' => env('ELASTICSEARCH_INDEX_KNOWLEDGE_SNAPSHOTS', 'knowledge_snapshots'),
            'learning_resources' => env('ELASTICSEARCH_INDEX_LEARNING_RESOURCES', 'learning_resources'),
            'dependency_graph' => env('ELASTICSEARCH_INDEX_DEPENDENCY_GRAPH', 'dependency_graph'),
            'session_interactions' => env('ELASTICSEARCH_INDEX_SESSION_INTERACTIONS', 'session_interactions'),
        ],
    ],

    'feature_flags' => [
        'calibration' => (bool) env('ENABLE_PHASE_CALIBRATION', true),
        'tuning' => (bool) env('ENABLE_PHASE_TUNING', true),
        'learning' => (bool) env('ENABLE_PHASE_LEARNING', true),
    ],
];
