"""What the machine running the BACKEND can do.

This describes the computer that runs this Python process (and so the Ollama it
talks to), never a browser visitor's laptop: the frontend only ever receives the
result through the API. On a hosted deployment (Vercel, containers) it describes
that server, and `deployment()` says so, so the UI never implies a visitor's
machine was inspected.

Detection uses only the standard library plus `nvidia-smi` when present. What it
can and cannot see is explicit in the result (`gpu.source`), because guessing
would make the recommendations wrong in exactly the cases they matter:
  * NVIDIA GPUs: read through nvidia-smi (needs the NVIDIA driver).
  * Apple Silicon: unified memory, reported as "apple-silicon"; treated as RAM.
  * AMD / Intel GPUs: not detected (reported as none); Ollama may still use them.
No hostname, user name or serial number is collected.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

GB = 1024**3


@dataclass(frozen=True)
class Gpu:
    name: str
    vram_total_gb: float
    vram_free_gb: Optional[float]
    source: str  # "nvidia-smi" | "apple-silicon"


@dataclass(frozen=True)
class Hardware:
    os: str  # "windows" | "linux" | "macos" | other
    cpu_threads: int
    ram_total_gb: float
    ram_available_gb: Optional[float]
    gpu: Optional[Gpu]
    notes: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _round(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 1)


# --- RAM ------------------------------------------------------------------------

def _windows_memory() -> tuple[float, float]:
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        raise OSError("GlobalMemoryStatusEx failed")
    return status.ullTotalPhys / GB, status.ullAvailPhys / GB


def _linux_memory() -> tuple[float, float]:
    values: Dict[str, int] = {}
    with open("/proc/meminfo", encoding="ascii") as handle:
        for line in handle:
            key, _, rest = line.partition(":")
            match = re.match(r"\s*(\d+)", rest)
            if match:
                values[key] = int(match.group(1)) * 1024
    total = values["MemTotal"]
    available = values.get("MemAvailable", values.get("MemFree", 0))
    # Inside a container the cgroup limit is the real ceiling.
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            raw = open(path, encoding="ascii").read().strip()
            if raw.isdigit() and int(raw) < total:
                total = int(raw)
                available = min(available, total)
        except OSError:
            continue
    return total / GB, available / GB


def _macos_memory() -> tuple[float, Optional[float]]:
    total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=3).strip())
    return total / GB, None


def _memory() -> tuple[float, Optional[float]]:
    if sys.platform.startswith("win"):
        return _windows_memory()
    if sys.platform == "darwin":
        return _macos_memory()
    return _linux_memory()


# --- GPU ------------------------------------------------------------------------

def _nvidia_gpu() -> Optional[Gpu]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.check_output(
            [exe, "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            timeout=5,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    best: Optional[Gpu] = None
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            total = float(parts[1]) * 1024**2 / GB
            free = float(parts[2]) * 1024**2 / GB
        except ValueError:
            continue
        gpu = Gpu(parts[0], _round(total) or 0.0, _round(free), "nvidia-smi")
        # Ollama splits one model across GPUs poorly; plan around the biggest one.
        if best is None or gpu.vram_total_gb > best.vram_total_gb:
            best = gpu
    return best


_cache: tuple[float, Hardware] | None = None


def detect(force: bool = False) -> Hardware:
    """Cached for 30 s: free memory changes, the machine does not."""
    global _cache
    now = time.monotonic()
    if not force and _cache and now - _cache[0] < 30:
        return _cache[1]

    notes: list = []
    try:
        total, available = _memory()
    except Exception:  # noqa: BLE001 - detection must never take the app down
        total, available = 0.0, None
        notes.append("Couldn't read system memory, so recommendations are conservative.")

    gpu = _nvidia_gpu()
    machine = platform.machine().lower()
    if gpu is None and sys.platform == "darwin" and machine in ("arm64", "aarch64"):
        # Unified memory: the GPU can use a large share of RAM, but not all of it.
        gpu = Gpu("Apple Silicon (unified memory)", _round(total * 0.66) or 0.0, None, "apple-silicon")
    if gpu is None:
        notes.append("No NVIDIA GPU was detected. AMD and Intel graphics aren't detected, so models are sized for the CPU.")

    os_name = "windows" if sys.platform.startswith("win") else ("macos" if sys.platform == "darwin" else platform.system().lower())
    result = Hardware(
        os=os_name,
        cpu_threads=os.cpu_count() or 1,
        ram_total_gb=_round(total) or 0.0,
        ram_available_gb=_round(available),
        gpu=gpu,
        notes=notes,
    )
    _cache = (now, result)
    return result


# --- where is this backend running? ---------------------------------------------

def deployment() -> Dict[str, Any]:
    """Whether this backend is a hosted/serverless one. Hosted backends can't reach
    a model on someone's laptop, and their hardware isn't the visitor's."""
    hosted_markers = [name for name in ("VERCEL", "AWS_LAMBDA_FUNCTION_NAME", "K_SERVICE", "RENDER", "FLY_APP_NAME", "RAILWAY_ENVIRONMENT") if os.getenv(name)]
    return {
        "hosted": bool(hosted_markers),
        "serverless": bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("K_SERVICE")),
        "note": (
            "This backend is hosted, so the figures below describe the server, not your computer. "
            "A hosted backend cannot use models running on your laptop."
            if hosted_markers
            else "This backend runs on the computer shown below. Models are installed and run there."
        ),
    }
