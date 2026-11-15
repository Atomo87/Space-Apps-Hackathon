"""Confere a identidade do aplicativo antes de abrir a porta; nao imprime segredos."""
from pathlib import Path
import importlib


def main():
    root = Path(__file__).resolve().parent
    module = importlib.import_module('app.main')
    if Path(module.__file__).resolve() != root / 'app' / 'main.py':
        raise SystemExit('ERRO: outro modulo app.main foi importado.')
    routes = {getattr(r, 'path', '') for r in module.app.routes}
    required = {'/test', '/health', '/v1/cultivation-assessment', '/v1/insights'}
    if not required <= routes:
        raise SystemExit('ERRO: versao incompleta; rotas ausentes: ' + ', '.join(sorted(required - routes)))
    if not (root / 'app/static/test.html').is_file():
        raise SystemExit('ERRO: tela de testes ausente.')
    import importlib.util
    for dependency in ('h5py', 'rasterio'):
        if importlib.util.find_spec(dependency) is None:
            print('AVISO: ' + dependency + ' ausente; fontes complementares podem estar indisponiveis. Execute -Install.')
    print('Aplicativo conferido: ' + str(Path(module.__file__).resolve()))
    print('Rotas /test, cultivo e insights presentes. Isso nao confirma que a porta esta disponivel.')


if __name__ == '__main__':
    main()
