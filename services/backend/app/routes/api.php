<?php

use App\Http\Controllers\Api\ChatSessionController;
use App\Http\Controllers\Api\FlowEventController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    Route::post('/sessions', [ChatSessionController::class, 'start']);
    Route::post('/sessions/{session}', [ChatSessionController::class, 'message']);
    Route::get('/sessions/{session}', [ChatSessionController::class, 'show']);
    Route::post('/flow-events', [FlowEventController::class, 'store']);
    Route::get('/flow-events/stream', [FlowEventController::class, 'stream']);
});
