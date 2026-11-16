<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Services\PublicDemo;
use Illuminate\Http\RedirectResponse;

class DemoController extends Controller
{
    public function __invoke(PublicDemo $demo): RedirectResponse
    {
        return redirect()->route('fields.show', $demo->open())
            ->with('success', __('Exemplo de Uberlândia (MG). Para analisar o seu, use "Cadastrar talhão".'));
    }
}
