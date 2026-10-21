"""Hardware helpers (RAM / GPU providers) used for memory-aware processing."""
import ctypes
import os


def available_ram_bytes() -> int:
    try:
        if os.name == "nt":
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = MS()
            ms.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return int(ms.ullAvailPhys)
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) * 1024
    except Exception:
        pass
    return 4 * 1024 ** 3


def estimate_enhance_bytes(w: int, h: int, scale: int) -> int:
    """Rough peak memory for the pipeline (several full-size float/uint8 copies)."""
    return int(w * h * scale * scale * 3 * 6)


def gpu_providers() -> list:
    try:
        import onnxruntime as ort
        return [p for p in ort.get_available_providers() if p in ("CUDAExecutionProvider", "DmlExecutionProvider")]
    except Exception:
        return []
