"""Launches the app the way a person actually launches it.

This exists because of a bug the rest of the suite could not see. `AppTest` puts `src` on
the path itself (pytest's `pythonpath` setting), so every flow test passed while
`streamlit run src/prove_it/ui/app.py` — the command the README and setup docs both give —
died instantly with ModuleNotFoundError. The server still answered HTTP 200 and its health
endpoint still said "ok", because Streamlit only executes the script when a browser
connects. Server-is-up is not app-works.

So this test runs the real command in a subprocess, with the environment scrubbed of the
things that would paper over the failure, and reads the server's own log for the traceback
Streamlit prints when a script dies.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "prove_it" / "ui" / "app.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():  # POSIX layout
    PYTHON = ROOT / ".venv" / "bin" / "python"

BOOT_TIMEOUT = 90


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_for(url: str, deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


@pytest.mark.slow
@pytest.mark.skipif(not PYTHON.exists(), reason="no project virtualenv to launch")
def test_the_documented_launch_command_actually_renders_the_app(tmp_path: Path) -> None:
    port = free_port()
    log = tmp_path / "server.log"

    # Scrubbed on purpose. PYTHONPATH would hide exactly the bug this test exists for,
    # and a stray PROVE_IT_* var from the developer's shell would change what renders.
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "PYTHONPATH" and not k.startswith("PROVE_IT_") and not k.startswith("GENIE_")
    }

    with log.open("w", encoding="utf-8") as sink:
        server = subprocess.Popen(
            [
                str(PYTHON),
                "-m",
                "streamlit",
                "run",
                str(APP),
                "--server.port",
                str(port),
                "--server.headless",
                "true",
            ],
            cwd=str(ROOT),
            stdout=sink,
            stderr=subprocess.STDOUT,
            env=env,
        )
    try:
        deadline = time.monotonic() + BOOT_TIMEOUT
        assert wait_for(f"http://127.0.0.1:{port}/_stcore/health", deadline), (
            f"server never became healthy\n{log.read_text(encoding='utf-8')}"
        )

        # Fetching the page is what makes Streamlit execute the script. Without this the
        # script never runs and the log stays clean no matter how broken the app is.
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=15) as response:
            assert response.status == 200
        time.sleep(3)  # let the script run and any traceback reach the log

        output = log.read_text(encoding="utf-8")
        assert "Uncaught app execution" not in output, f"the app raised while rendering:\n{output}"
        assert "ModuleNotFoundError" not in output, (
            f"the app could not import its own package:\n{output}"
        )
        assert "Traceback" not in output, f"the app logged a traceback:\n{output}"
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover
            server.kill()


@pytest.mark.skipif(sys.platform not in {"win32", "linux", "darwin"}, reason="unsupported")
def test_the_package_imports_without_help_from_pytest() -> None:
    """A clean interpreter must be able to import the package.

    pytest sets `pythonpath = ["src"]`, so the rest of the suite proves nothing about
    whether the editable install is actually wired up. An `-e` install can write its
    dist-info and skip the .pth that does the path wiring, and nothing notices until the
    app is launched for real.
    """
    result = subprocess.run(
        [str(PYTHON), "-c", "import prove_it, prove_it.session; print('ok')"],
        cwd=str(ROOT),
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        "prove_it is not importable from a clean interpreter — the editable install is "
        f"incomplete. Re-run `uv pip install -e .`\nstderr:\n{result.stderr}"
    )
