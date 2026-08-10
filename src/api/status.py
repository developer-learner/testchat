"""Lightweight system status for the UI footer strip."""

import logging
import os
import subprocess

from fastapi import APIRouter

from src.services import models as models_service
from src.services import websearch

router = APIRouter()

logger = logging.getLogger(__name__)

_PAGE_SIZE = 16384  # Apple Silicon page size; corrected live from vm_stat header


def _ram_totals() -> tuple[float, float]:
    """Return (used_gb, total_gb) for the whole machine, 0.0 on failure."""
    used_gb = 0.0
    total_gb = 0.0
    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2
        )
        total_gb = int(out.stdout.strip()) / 1024**3
    except Exception:
        logger.exception("hw.memsize failed")
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=2)
        page_size = _PAGE_SIZE
        pages = {"active": 0, "wired down": 0, "occupied by compressor": 0}
        for line in out.stdout.splitlines():
            if "page size of" in line:
                page_size = int(line.split("page size of")[1].split()[0])
                continue
            for key in pages:
                if line.startswith(f"Pages {key}:"):
                    pages[key] = int(line.split(":")[1].strip().rstrip("."))
        used_gb = sum(pages.values()) * page_size / 1024**3
    except Exception:
        logger.exception("vm_stat failed")
    return used_gb, total_gb


def _script_model_rss_gb(model_id: str) -> float:
    """RSS of a script model's process in GB, 0.0 if not running or unknown."""
    pid = None
    proc = models_service._get_process(model_id)
    if proc is not None and proc.poll() is None:
        pid = proc.pid
    else:
        entry = models_service.get_script_model(model_id)
        if entry is None:
            return 0.0
        # Fallback for servers started outside this app: match on the launch
        # command's script name, the most distinctive stable token.
        pattern = os.path.basename(entry["command"][-1])
        try:
            out = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                text=True,
                timeout=2,
            )
            first = out.stdout.strip().splitlines()
            if first:
                pid = int(first[0])
        except Exception:
            return 0.0
    if pid is None:
        return 0.0
    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return int(out.stdout.strip()) / 1024**2
    except Exception:
        return 0.0


def _nemotron_rss_gb() -> float:
    """RSS of the Nemotron process in GB, 0.0 if not running or unknown."""
    return _script_model_rss_gb("nemotron")


def _loadable_gb() -> float:
    """Return the amount of GB available for model loading, 0.0 on failure."""
    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=2
        )
        total_gb = int(out.stdout.strip()) / 1024**3

        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=2)
        page_size = 16384
        pages: dict[str, int] = {}
        for line in out.stdout.splitlines():
            if "page size of" in line:
                page_size = int(line.split("page size of")[1].split()[0])
                continue
            for key in (
                "Pages free:",
                "Pages speculative:",
                "Pages purgeable:",
                "File-backed pages:",
                "Pages wired down:",
            ):
                if line.startswith(key):
                    pages[key] = int(line.split(":")[1].strip().rstrip("."))

        free = pages.get("Pages free:", 0)
        speculative = pages.get("Pages speculative:", 0)
        purgeable = pages.get("Pages purgeable:", 0)
        file_backed = pages.get("File-backed pages:", 0)
        wired_down = pages.get("Pages wired down:", 0)

        reclaimable_gb = (
            (free + speculative + purgeable + file_backed) * page_size / 1024**3
        )
        wired_gb = wired_down * page_size / 1024**3

        try:
            out = subprocess.run(
                ["sysctl", "-n", "iogpu.wired_limit_mb"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            limit_mb = int(out.stdout.strip())
            if limit_mb > 0:
                cap_gb = limit_mb / 1024
            else:
                cap_gb = 0.75 * total_gb
        except Exception:
            cap_gb = 0.75 * total_gb

        return max(0.0, min(reclaimable_gb, cap_gb - wired_gb) - 4.0)
    except Exception:
        logger.exception("loadable calc failed")
        return 0.0


@router.get("/api/v1/status")
def get_status() -> dict:
    used_gb, total_gb = _ram_totals()
    nemotron_loaded = models_service.is_nemotron_loaded()
    script_models = []
    for model_id in models_service.SCRIPT_MODELS:
        loaded = (
            nemotron_loaded
            if model_id == "nemotron"
            else models_service.is_script_model_loaded(model_id)
        )
        script_models.append(
            {
                "id": model_id,
                "loaded": loaded,
                "rss_gb": round(_script_model_rss_gb(model_id), 1) if loaded else 0.0,
            }
        )
    return {
        "nemotron_loaded": nemotron_loaded,
        "nemotron_rss_gb": round(_nemotron_rss_gb(), 1) if nemotron_loaded else 0.0,
        "models": script_models,
        "ram_used_gb": round(used_gb, 1),
        "ram_total_gb": round(total_gb, 1),
        "loadable_gb": round(_loadable_gb(), 1),
        "web_configured": websearch.is_configured(),
    }
