"""System hardware detection and LLM model recommendations."""

from fastapi import APIRouter
import logging
import platform
import subprocess
import shutil

router = APIRouter(prefix="/api/v1/system", tags=["system"])
logger = logging.getLogger(__name__)


def _detect_gpu() -> dict:
    """Probe for NVIDIA (nvidia-smi) or AMD (rocm-smi) GPU."""
    # NVIDIA
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().splitlines()[0]
                parts = [p.strip() for p in line.split(",")]
                name = parts[0]
                vram_gb = round(int(parts[1]) / 1024, 1) if len(parts) > 1 else 0
                return {"available": True, "name": name, "vram_gb": vram_gb, "type": "nvidia"}
        except Exception:
            pass

    # AMD ROCm
    if shutil.which("rocm-smi"):
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return {"available": True, "name": "AMD GPU (ROCm)", "vram_gb": 0, "type": "amd"}
        except Exception:
            pass

    return {"available": False, "name": None, "vram_gb": 0, "type": None}


def _recommend(ram_gb: float, vram_gb: float) -> dict:
    """Return sensible model defaults based on available hardware."""
    # GPU-first path
    if vram_gb >= 24:
        llm = "llama3:70b-q4_K_M"
    elif vram_gb >= 16:
        llm = "llama3:8b-q8_0"
    elif vram_gb >= 8:
        llm = "llama3:8b-q4_K_M"
    elif vram_gb >= 4:
        llm = "gemma3:4b"
    # CPU-only path
    elif ram_gb >= 32:
        llm = "llama3:8b-q8_0"
    elif ram_gb >= 16:
        llm = "llama3:8b-q4_K_M"
    elif ram_gb >= 8:
        llm = "mistral:7b-q4_0"
    else:
        llm = "gemma3:2b"

    embedding = "mxbai-embed-large" if ram_gb >= 16 else "nomic-embed-text"

    # Suggest quantization level for manual pulls
    if vram_gb >= 8 or ram_gb >= 16:
        quant = "q4_K_M"
    elif vram_gb >= 4 or ram_gb >= 8:
        quant = "q4_0"
    else:
        quant = "q2_K"

    return {"llm": llm, "embedding": embedding, "quantization": quant}


@router.get("/info")
async def system_info():
    """Return CPU, RAM, GPU info and recommended model settings."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        ram_gb = round(mem.total / (1024 ** 3), 1)
        ram_used_gb = round(mem.used / (1024 ** 3), 1)
        cpu_cores_physical = psutil.cpu_count(logical=False) or 0
        cpu_cores_logical = psutil.cpu_count(logical=True) or 0
        cpu_pct = psutil.cpu_percent(interval=0.1)
    except ImportError:
        ram_gb, ram_used_gb = 0, 0
        cpu_cores_physical, cpu_cores_logical, cpu_pct = 0, 0, 0

    gpu = _detect_gpu()
    rec = _recommend(ram_gb, gpu["vram_gb"])

    # Detect WSL2: Linux kernel built by Microsoft
    is_wsl2 = False
    try:
        with open("/proc/version", "r") as f:
            is_wsl2 = "microsoft" in f.read().lower()
    except OSError:
        pass

    return {
        "platform": platform.system(),
        "is_wsl2": is_wsl2,
        "cpu": {
            "model": platform.processor() or platform.machine(),
            "cores_physical": cpu_cores_physical,
            "cores_logical": cpu_cores_logical,
            "usage_pct": cpu_pct,
        },
        "ram": {
            "total_gb": ram_gb,
            "used_gb": ram_used_gb,
        },
        "gpu": gpu,
        "recommended": rec,
    }


@router.get("/docker")
async def docker_health():
    """Check which DEPFIX-related Docker containers are running."""
    if not shutil.which("docker"):
        return {"docker_installed": False, "containers": []}

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"],
            capture_output=True, text=True, timeout=8,
        )
        containers = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                containers.append({
                    "name":   parts[0],
                    "status": parts[1],
                    "image":  parts[2],
                })
        return {"docker_installed": True, "containers": containers}
    except subprocess.TimeoutExpired:
        return {"docker_installed": True, "containers": [], "error": "docker ps timed out"}
    except Exception as exc:
        return {"docker_installed": True, "containers": [], "error": str(exc)}
