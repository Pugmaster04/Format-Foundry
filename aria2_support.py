import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Callable


def build_rpc_payload(method: str, params: list[Any] | None = None, request_id: str = "uch") -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": f"aria2.{method}",
        "params": params or [],
    }


def build_rpc_request(port: int, method: str, params: list[Any] | None = None, request_id: str = "uch") -> urllib.request.Request:
    payload = build_rpc_payload(method, params=params, request_id=request_id)
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
    timeout: float = 1.5,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> Any:
    request = build_rpc_request(port, method, params=params, request_id=request_id)
    with opener(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    return data.get("result") if isinstance(data, dict) else None


def process_is_running(process: subprocess.Popen[str] | None) -> bool:
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
) -> list[str]:
    return [
        executable,
        "--dir",
        str(destination),
        "--enable-rpc=true",
        "--rpc-listen-all=false",
        f"--rpc-listen-port={rpc_port}",
        *(extra_args or []),
        *sources,
    ]
