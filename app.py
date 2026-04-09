"""Single-command backend launcher for local development on Windows.

Starts parser-service, ml-service, genai-service, api-gateway, and simulator
in parallel and prefixes each log line with the service name.
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import venv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Service:
    name: str
    cwd: Path
    venv_dir: Path
    requirements_file: Path
    cmd: list[str]


def _py(venv_dir: Path) -> str:
    if os.name == "nt":
        exe = venv_dir / "Scripts" / "python.exe"
    else:
        exe = venv_dir / "bin" / "python"
    return str(exe)


def build_services(include_simulator: bool = True) -> list[Service]:
    services = [
        Service(
            name="parser",
            cwd=ROOT / "parser-service",
            venv_dir=ROOT / "parser-service" / ".venv",
            requirements_file=ROOT / "parser-service" / "requirements.txt",
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
            venv_dir=ROOT / "ml-service" / ".venv",
            requirements_file=ROOT / "ml-service" / "requirements.txt",
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
            venv_dir=ROOT / "genai-service" / ".venv",
            requirements_file=ROOT / "genai-service" / "requirements.txt",
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
            venv_dir=ROOT / "api-gateway" / ".venv",
            requirements_file=ROOT / "api-gateway" / "requirements.txt",
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
                venv_dir=ROOT / "simulator" / ".venv",
                requirements_file=ROOT / "simulator" / "requirements.txt",
                cmd=[_py(ROOT / "simulator" / ".venv"), "generator.py"],
            )
        )
    return services


def _validate_services(services: list[Service]) -> None:
    missing: list[str] = []
    for svc in services:
        if not svc.cwd.exists():
            missing.append(f"{svc.name}: missing directory {svc.cwd}")
        if not svc.requirements_file.exists():
            missing.append(
                f"{svc.name}: missing requirements file at {svc.requirements_file}"
            )
    if missing:
        msg = "\n".join(missing)
        raise SystemExit(
            "Cannot start backend because some service paths are missing:\n"
            f"{msg}"
        )


def _run_setup_cmd(cmd: list[str], cwd: Path, label: str) -> None:
    print(f"[setup:{label}] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _bootstrap_service_venv(svc: Service) -> None:
    py_exe = Path(_py(svc.venv_dir))
    if py_exe.exists():
        return

    print(f"[setup:{svc.name}] .venv not found. Creating and installing dependencies...")
    venv.EnvBuilder(with_pip=True, clear=False).create(str(svc.venv_dir))

    py_cmd = [str(py_exe)]
    _run_setup_cmd(py_cmd + ["-m", "pip", "install", "--upgrade", "pip"], svc.cwd, svc.name)
    _run_setup_cmd(
        py_cmd + ["-m", "pip", "install", "-r", str(svc.requirements_file)],
        svc.cwd,
        svc.name,
    )
    print(f"[setup:{svc.name}] Environment ready.")


def _ensure_local_envs(services: list[Service]) -> None:
    for svc in services:
        try:
            _bootstrap_service_venv(svc)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(
                f"Failed while setting up {svc.name} environment (exit={exc.returncode})."
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive startup guard
            raise SystemExit(f"Failed to set up {svc.name} environment: {exc}") from exc


def _stream_output(name: str, pipe) -> None:
    for line in iter(pipe.readline, ""):
        print(f"[{name}] {line}", end="")
    pipe.close()


def _can_connect_tcp(host: str, port: int, timeout_sec: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def _with_runtime_defaults() -> dict[str, str]:
    env = os.environ.copy()
    if "KAFKA_BOOTSTRAP_SERVERS" not in env:
        env["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:29092"

    redis_url = env.get("REDIS_URL", "").strip() or "redis://localhost:6379/0"
    parsed = urlparse(redis_url)
    r_host = parsed.hostname or "localhost"
    r_port = int(parsed.port or 6379)
    redis_ok = _can_connect_tcp(r_host, r_port)

    if redis_ok:
        env["REDIS_URL"] = redis_url
        env["USE_KAFKA_UPLOAD_PATH"] = "1"
        print(
            f"[setup] Redis reachable at {r_host}:{r_port} -> "
            "enabling Kafka+Redis upload path."
        )
    else:
        env["USE_KAFKA_UPLOAD_PATH"] = "0"
        env.setdefault("USE_CLASSIFY_BATCH", "1")
        print(
            f"[setup] Redis not reachable at {r_host}:{r_port} -> "
            "using direct classify upload fallback."
        )
    return env


def _service_env(svc: Service, base_env: dict[str, str]) -> dict[str, str]:
    # Keep service-specific overrides possible while sharing startup detection.
    return dict(base_env)


def _start_process(svc: Service, base_env: dict[str, str]) -> subprocess.Popen:
    kwargs = {
        "cwd": str(svc.cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "env": _service_env(svc, base_env),
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
    _ensure_local_envs(services)
    base_env = _with_runtime_defaults()

    print("Starting backend services...")
    processes: list[tuple[str, subprocess.Popen]] = []
    for svc in services:
        proc = _start_process(svc, base_env)
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
