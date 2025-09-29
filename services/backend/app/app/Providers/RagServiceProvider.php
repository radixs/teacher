<?php

namespace App\Providers;

use App\Services\Rag\RagClient;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Http;

class RagServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(RagClient::class, function () {
            return new RagClient(
                Http::baseUrl(config('rag.orchestrator_url')),
                config('rag.elasticsearch'),
            );
        });
    }

    public function boot(): void
    {
        // Future bootstrapping hooks (events, observers, etc.) will live here.
    }
}
