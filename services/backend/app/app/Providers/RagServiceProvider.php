<?php

namespace App\Providers;

use App\Services\Rag\RagClient;
use App\Support\FlowEventStream;
use App\Support\FlowLogger;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Http;

class RagServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(
            FlowEventStream::class,
            fn () => new FlowEventStream(
                config('flow_events.cache_store', 'file'),
                config('flow_events.namespace', 'default'),
                (int) config('flow_events.buffer_size', 40),
                (int) config('flow_events.retention_seconds', 900),
            ),
        );

        $this->app->singleton(
            FlowLogger::class,
            fn () => new FlowLogger(
                env('FLOW_LOG_PATH'),
                $this->app->make(FlowEventStream::class),
            ),
        );

        $this->app->singleton(RagClient::class, function () {
            return new RagClient(
                Http::baseUrl(config('rag.orchestrator_url'))
                    ->acceptJson()
                    ->asJson()
                    ->connectTimeout((int) config('rag.connect_timeout', 5))
                    ->timeout((int) config('rag.request_timeout', 180)),
                config('rag.elasticsearch'),
                $this->app->make(FlowLogger::class),
            );
        });
    }

    public function boot(): void
    {
        // Future bootstrapping hooks (events, observers, etc.) will live here.
    }
}
