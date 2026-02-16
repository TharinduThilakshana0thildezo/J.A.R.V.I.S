from __future__ import annotations

from typing import Dict, List, Optional

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None

from jarvis_ai.memory.logs import Logger
from jarvis_ai.tools.safety import require_confirmation


def system_info() -> Dict[str, str]:
    return {"os": "windows"}


def system_stats() -> Dict[str, float]:
    if psutil is None:
        raise RuntimeError("psutil package is not installed")
    return {
        "cpu_percent": float(psutil.cpu_percent(interval=0.2)),
        "memory_percent": float(psutil.virtual_memory().percent),
        "disk_percent": float(psutil.disk_usage("/").percent),
    }


def list_processes(limit: int = 20) -> List[Dict[str, str]]:
    if psutil is None:
        raise RuntimeError("psutil package is not installed")
    results: List[Dict[str, str]] = []
    for proc in psutil.process_iter(["pid", "name"]):
        if len(results) >= limit:
            break
        info = proc.info
        results.append({"pid": str(info.get("pid")), "name": str(info.get("name"))})
    return results


def kill_process(pid: int, require_confirm: bool = True, logger: Optional[Logger] = None) -> None:
    if psutil is None:
        raise RuntimeError("psutil package is not installed")
    if require_confirm and not require_confirmation(f"kill process {pid}"):
        raise PermissionError("User denied process termination")
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        if logger:
            logger.log(task=f"kill_process {pid}", decision="kill_process", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"kill_process {pid}", decision="kill_process", outcome="failed", error=str(exc))
        raise
