"""
AI Saham Indonesia — System Notifier

Modul ini bertindak sebagai pusat notifikasi administrator melalui web dashboard lokal.
Ketika terjadi error kritis (scoring gagal, DB offline, dll), modul ini akan:
  1. Menyimpan error ke in-memory store (daftar terbatas 50 entri)
  2. Menyiarkan event ke semua dashboard browser yang sedang terbuka via SSE
  3. Membuka browser secara otomatis ke halaman admin dashboard (tab Error)
     jika browser belum terbuka / error sangat kritis

Arsitektur:
  - `report_error()`   → dipanggil dari scoring_agent, workers, dll saat ada error
  - `report_info()`    → dipanggil untuk log penting non-error (scoring selesai, dll)
  - `/api/admin/events` → SSE endpoint di main.py, subscribe ke asyncio.Queue
  - Dashboard JS        → EventSource subscribe, render banner + tabel error real-time
"""

import asyncio
import json
import webbrowser
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Literal

from loguru import logger

from backend.config import settings

# ============================================================
# Timezone WIB
# ============================================================
_WIB = timezone(timedelta(hours=7))

# ============================================================
# In-Memory Error Store (max 50 entri, FIFO)
# ============================================================
_MAX_ERRORS = 50

# Setiap entri: {"id", "level", "source", "message", "timestamp"}
_error_store: deque[dict] = deque(maxlen=_MAX_ERRORS)
_error_counter: int = 0

# ============================================================
# SSE Subscriber Queues
# Setiap browser tab yang subscribe akan punya asyncio.Queue-nya sendiri.
# Ketika ada event baru, kita taruh ke semua queue.
# ============================================================
_subscribers: list[asyncio.Queue] = []


def _now_str() -> str:
    return datetime.now(_WIB).strftime("%Y-%m-%d %H:%M:%S WIB")


def _broadcast(event_data: dict) -> None:
    """Taruh event ke semua subscriber queue (non-blocking)."""
    payload = json.dumps(event_data, ensure_ascii=False)
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # Subscriber lambat; skip, jangan crash server


def subscribe() -> asyncio.Queue:
    """Daftarkan subscriber baru. Kembalikan Queue-nya."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    logger.debug(f"📡 SSE subscriber baru terdaftar. Total: {len(_subscribers)}")
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Hapus subscriber dari daftar."""
    try:
        _subscribers.remove(q)
        logger.debug(f"📡 SSE subscriber dihapus. Sisa: {len(_subscribers)}")
    except ValueError:
        pass


# ============================================================
# Public API: report_error() dan report_info()
# ============================================================

def report_error(
    source: str,
    message: str,
    level: Literal["ERROR", "CRITICAL"] = "ERROR",
    auto_open_browser: bool = False,
) -> None:
    """
    Laporkan error sistem ke dashboard administrator.

    Args:
        source:  Nama modul/komponen yang melaporkan error (contoh: "scoring_agent", "workers")
        message: Pesan error yang deskriptif
        level:   "ERROR" untuk error biasa, "CRITICAL" untuk error yang menghentikan proses
        auto_open_browser: Jika True, buka browser ke halaman admin secara otomatis
    """
    global _error_counter
    _error_counter += 1

    entry = {
        "id": _error_counter,
        "level": level,
        "source": source,
        "message": message,
        "timestamp": _now_str(),
    }
    _error_store.appendleft(entry)  # Terbaru di atas

    # Log ke terminal juga
    if level == "CRITICAL":
        logger.critical(f"🚨 [{source}] {message}")
    else:
        logger.error(f"❌ [{source}] {message}")

    # Siarkan ke semua browser dashboard yang sedang terbuka
    _broadcast({"type": "error", "data": entry})

    # Buka browser otomatis ke tab admin jika diminta
    if auto_open_browser:
        _open_admin_dashboard()


def report_info(source: str, message: str) -> None:
    """
    Laporkan event penting (non-error) ke dashboard administrator.
    Contoh: scoring selesai, scraping berhasil, dll.
    """
    global _error_counter
    _error_counter += 1

    entry = {
        "id": _error_counter,
        "level": "INFO",
        "source": source,
        "message": message,
        "timestamp": _now_str(),
    }
    _error_store.appendleft(entry)

    logger.info(f"✅ [{source}] {message}")
    _broadcast({"type": "info", "data": entry})


def get_all_errors() -> list[dict]:
    """Ambil semua error yang tersimpan (terbaru di atas)."""
    return list(_error_store)


def get_unresolved_errors() -> list[dict]:
    """Ambil hanya event level ERROR dan CRITICAL."""
    return [e for e in _error_store if e["level"] in ("ERROR", "CRITICAL")]


# ============================================================
# Auto-open Browser
# ============================================================
_browser_opened: bool = False  # Hanya buka sekali per sesi server


def _open_admin_dashboard() -> None:
    """
    Buka browser ke halaman admin dashboard secara otomatis.
    Menggunakan flag agar tidak terus-menerus membuka tab baru.
    Browser dibuka ke tab admin (#admin) dengan highlight error.
    """
    global _browser_opened

    url = f"http://localhost:{settings.app_port}/#admin"

    if _browser_opened:
        logger.info(f"🌐 Browser sudah pernah dibuka sebelumnya. Tidak membuka lagi.")
        return

    try:
        logger.warning(f"🌐 AUTO-OPEN BROWSER: Membuka dashboard admin di {url}")
        webbrowser.open(url)
        _browser_opened = True
    except Exception as e:
        logger.error(f"❌ Gagal membuka browser otomatis: {e}")


def reset_browser_flag() -> None:
    """Reset flag browser (untuk testing atau setelah restart)."""
    global _browser_opened
    _browser_opened = False
