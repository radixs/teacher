<?php

use App\Http\Controllers\Api\ChatSessionController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    Route::post('/sessions', [ChatSessionController::class, 'start']);
    Route::post('/sessions/{session}', [ChatSessionController::class, 'message']);
    Route::get('/sessions/{session}', [ChatSessionController::class, 'show']);
});
