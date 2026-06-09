import threading
from typing import Dict, Any

_lock = threading.Lock()
_progress: Dict[str, Dict[str, Any]] = {
    "scrape_news": {"percent": 0, "status": "idle", "message": "Siap"},
    "scrape_fundamental": {"percent": 0, "status": "idle", "message": "Siap"},
    "scrape_makro": {"percent": 0, "status": "idle", "message": "Siap"},
    "run_scoring": {"percent": 0, "status": "idle", "message": "Siap"},
    "run_alerts": {"percent": 0, "status": "idle", "message": "Siap"},
}

def set_progress(job_name: str, percent: int, status: str = "running", message: str = ""):
    with _lock:
        if job_name in _progress:
            _progress[job_name] = {
                "percent": percent,
                "status": status,
                "message": message
            }

def get_progress(job_name: str) -> Dict[str, Any]:
    with _lock:
        return _progress.get(job_name, {"percent": 0, "status": "idle", "message": "Tidak diketahui"})

def get_all_progress() -> Dict[str, Dict[str, Any]]:
    with _lock:
        return dict(_progress)
