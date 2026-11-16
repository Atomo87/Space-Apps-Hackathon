<?php

namespace Tests;

use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\Http;

abstract class TestCase extends BaseTestCase
{
    protected function setUp(): void
    {
        parent::setUp();

        // Nenhum teste acessa a internet: toda chamada HTTP precisa de um Http::fake correspondente.
        Http::preventStrayRequests();
    }
}
