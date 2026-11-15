"""Testes ASGI sem TCP: python run-tests.py --windows-pipe-loop.

Modo opt-in exclusivo de testes. Nao modifica o servidor ou permite rede.
Usa APIs internas do asyncio do Windows: verificar ao atualizar Python.
"""
from __future__ import annotations
import argparse
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import uuid


def pipe_loop_policy():
    if sys.platform != "win32":
        raise RuntimeError("O modo pipe requer Windows.")
    import _winapi
    from asyncio import windows_utils

    class PipeProactorLoop(asyncio.ProactorEventLoop):
        def _make_self_pipe(self):
            read_handle, write_handle = windows_utils.pipe(overlapped=(True, False), bufsize=65536)
            self._ssock = windows_utils.PipeHandle(read_handle)
            self._csock = windows_utils.PipeHandle(write_handle)
            self._internal_fds += 1

        def _write_to_self(self):
            handle = self._csock
            if handle is not None:
                try:
                    _winapi.WriteFile(handle.fileno(), b"\0", False)
                except (OSError, ValueError):
                    pass  # Outra thread pode estar fechando o loop.

    class PipePolicy(asyncio.WindowsProactorEventLoopPolicy):
        _loop_factory = PipeProactorLoop

    return PipePolicy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows-pipe-loop", action="store_true")
    args, pytest_args = parser.parse_known_args()
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    # Test process isolated from local service credentials.
    os.environ["REQUIRE_VERIFIED_PROFILES"] = "false"  # Fixtures sinteticas exclusivas dos testes.
    os.environ["GEOSAFRA_TOKEN"] = ""
    os.environ["EARTHDATA_TOKEN"] = ""
    os.chdir(Path(__file__).resolve().parent)
    if not pytest_args:
        pytest_args = ["-q"]
    pytest_args += ["-p", "no:cacheprovider", "--basetemp", str(Path(tempfile.gettempdir()) / ("geosafra-tests-" + uuid.uuid4().hex))]
    old_policy = asyncio.get_event_loop_policy()
    try:
        if args.windows_pipe_loop:
            asyncio.set_event_loop_policy(pipe_loop_policy())
            print("ASGI em memoria; despertar asyncio via pipe local, sem TCP.", flush=True)
        import pytest
        if args.windows_pipe_loop:
            # Pipes nao sao sockets de sinal no Windows. Executa os testes
            # em uma thread, como o proprio TestClient faz para o loop ASGI.
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(pytest.main, pytest_args).result()
        return pytest.main(pytest_args)
    finally:
        asyncio.set_event_loop_policy(old_policy)


if __name__ == "__main__":
    raise SystemExit(main())
