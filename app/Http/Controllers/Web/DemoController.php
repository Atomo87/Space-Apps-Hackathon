<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Services\PublicDemo;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

class DemoController extends Controller
{
    public function __invoke(Request $request, PublicDemo $demo): RedirectResponse
    {
        $data = $request->validate(['region' => ['sometimes', 'required', 'string', Rule::in(array_column($demo->options(), 'key'))]]);
        $key = $data['region'] ?? PublicDemo::DEFAULT_REGION;

        return redirect()->route('fields.show', $demo->open($key), 303);
    }
}
