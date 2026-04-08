"""Single-command backend launcher for local development on Windows.

Starts parser-service, ml-service, genai-service, api-gateway, and simulator
in parallel and prefixes each log line with the service name.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Service:
    name: str
    cwd: Path
    cmd: list[str]


def _py(venv_dir: Path) -> str:
    exe = venv_dir / "Scripts" / "python.exe"
    return str(exe)


def build_services(include_simulator: bool = True) -> list[Service]:
    services = [
        Service(
            name="parser",
            cwd=ROOT / "parser-service",
            cmd=[
                _py(ROOT / "parser-service" / ".venv"),
                "-m",
                "uvicorn",
                "app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8002",
                "--reload",
            ],
        ),
        Service(
            name="ml",
            cwd=ROOT / "ml-service",
            cmd=[
                _py(ROOT / "ml-service" / ".venv"),
                "-m",
                "uvicorn",
                "app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8001",
                "--reload",
            ],
        ),
        Service(
            name="genai",
            cwd=ROOT / "genai-service",
            cmd=[
                _py(ROOT / "genai-service" / ".venv"),
                "-m",
                "uvicorn",
                "app:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8003",
                "--reload",
            ],
        ),
        Service(
            name="gateway",
            cwd=ROOT / "api-gateway",
            cmd=[
                _py(ROOT / "api-gateway" / ".venv"),
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
            ],
        ),
    ]
    if include_simulator:
        services.append(
            Service(
                name="simulator",
                cwd=ROOT / "simulator",
                cmd=[_py(ROOT / "simulator" / ".venv"), "generator.py"],
            )
        )
    return services


def _validate_services(services: list[Service]) -> None:
    missing: list[str] = []
    for svc in services:
        exe = Path(svc.cmd[0])
        if not exe.exists():
            missing.append(f"{svc.name}: missing interpreter at {exe}")
        if not svc.cwd.exists():
            missing.append(f"{svc.name}: missing directory {svc.cwd}")
    if missing:
        msg = "\n".join(missing)
        raise SystemExit(
            "Cannot start backend because some service paths are missing:\n"
            f"{msg}\n\nRun service setup first (create venv + install requirements)."
        )


def _stream_output(name: str, pipe) -> None:
    for line in iter(pipe.readline, ""):
        print(f"[{name}] {line}", end="")
    pipe.close()


def _start_process(svc: Service) -> subprocess.Popen:
    kwargs = {
        "cwd": str(svc.cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "env": os.environ.copy(),
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    proc = subprocess.Popen(svc.cmd, **kwargs)
    t = threading.Thread(target=_stream_output, args=(svc.name, proc.stdout), daemon=True)
    t.start()
    return proc


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        else:
            proc.send_signal(signal.SIGTERM)
    except Exception:
        pass


def run(include_simulator: bool) -> int:
    services = build_services(include_simulator=include_simulator)
    _validate_services(services)

    print("Starting backend services...")
    processes: list[tuple[str, subprocess.Popen]] = []
    for svc in services:
        proc = _start_process(svc)
        processes.append((svc.name, proc))
        print(f"  - {svc.name} (pid={proc.pid})")

    print("\nServices are launching. Press Ctrl+C to stop all.\n")

    try:
        while True:
            time.sleep(0.7)
            for name, proc in processes:
                rc = proc.poll()
                if rc is not None:
                    print(f"\n[{name}] exited with code {rc}. Stopping all services.")
                    return rc if rc != 0 else 1
    except KeyboardInterrupt:
        print("\nStopping all services...")
        return 0
    finally:
        for _, proc in processes:
            _stop_process(proc)
        deadline = time.time() + 8
        for _, proc in processes:
            while proc.poll() is None and time.time() < deadline:
                time.sleep(0.15)
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all backend services in one terminal.")
    parser.add_argument(
        "--no-simulator",
        action="store_true",
        help="Start all backend services except simulator.",
    )
    args = parser.parse_args()
    code = run(include_simulator=not args.no_simulator)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
