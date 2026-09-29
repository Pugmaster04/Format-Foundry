import json
import os
import subprocess
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeGuard


def build_rpc_payload(method: str, params: list[Any] | None = None, request_id: str = "uch", *, secret: str = "") -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": f"aria2.{method}",
        "params": ([f"token:{secret}"] if secret else []) + (params or []),
    }


def build_rpc_request(port: int, method: str, params: list[Any] | None = None, request_id: str = "uch", *, secret: str = "") -> urllib.request.Request:
    payload = build_rpc_payload(method, params=params, request_id=request_id, secret=secret)
    return urllib.request.Request(
        f"http://127.0.0.1:{port}/jsonrpc",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def call_rpc(
    port: int,
    method: str,
    params: list[Any] | None = None,
    *,
    request_id: str = "uch",
    secret: str = "",
    timeout: float = 1.5,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> Any:
    request = build_rpc_request(port, method, params=params, request_id=request_id, secret=secret)
    with opener(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or data.get("id") != request_id:
        raise RuntimeError("Invalid aria2 RPC response.")
    if "error" in data:
        raise RuntimeError("aria2 rejected the RPC request.")
    if "result" not in data:
        raise RuntimeError("aria2 RPC response is missing its result.")
    return data["result"]


def process_is_running(process: subprocess.Popen[str] | None) -> TypeGuard[subprocess.Popen[str]]:
    return process is not None and process.poll() is None


def terminate_process(process: subprocess.Popen[str] | None) -> bool:
    if not process_is_running(process):
        return False
    process.terminate()
    return True


def build_download_command(
    executable: str,
    destination: Path,
    rpc_port: int,
    sources: list[str],
    *,
    extra_args: list[str] | None = None,
    secret: str = "",
) -> list[str]:
    return [
        executable,
        "--no-conf=true",
        f"--stop-with-process={os.getpid()}",
        "--max-download-result=100000",
        "--dir",
        str(destination),
        "--enable-rpc=true",
        "--rpc-listen-all=false",
        f"--rpc-listen-port={rpc_port}",
        *([f"--rpc-secret={secret}"] if secret else []),
        *(extra_args or []),
        *sources,
    ]


def redacted_command(command: list[str]) -> list[str]:
    return ["--rpc-secret=[REDACTED]" if arg.startswith("--rpc-secret=") else arg for arg in command]


class CompletionMonitor:
    """A fresh, owned aria2 daemon is complete only after its RPC queue settles."""

    def __init__(self, port: int, secret: str):
        self.port = port
        self.secret = secret
        self.settled = 0
        self.last_gids: set[str] = set()

    def complete(self) -> bool:
        def rpc(method: str, params: list[Any] | None = None) -> Any:
            return call_rpc(self.port, method, params, secret=self.secret)

        active = rpc("tellActive")
        waiting = rpc("tellWaiting", [0, 100000])
        stopped = rpc("tellStopped", [0, 100000])
        if not all(isinstance(items, list) for items in (active, waiting, stopped)):
            raise RuntimeError("Invalid aria2 queue response.")
        if active or waiting or not stopped:
            self.settled = 0
            return False
        gids = {str(item["gid"]) for item in stopped}
        children = {str(gid) for item in stopped for gid in item.get("followedBy", [])}
        if not children.issubset(gids):
            self.settled = 0
            return False
        self.settled = self.settled + 1 if gids == self.last_gids else 0
        self.last_gids = gids
        if self.settled < 2:
            return False
        if any(item.get("status") != "complete" for item in stopped):
            raise RuntimeError("One or more aria2 downloads failed or were removed. Review the transfer log.")
        rpc("shutdown")
        return True


def reap_process(process: subprocess.Popen[str]) -> int:
    try:
        return process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            return process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            return process.wait(timeout=3)
