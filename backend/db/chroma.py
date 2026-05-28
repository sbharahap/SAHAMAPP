"""
AI Saham Indonesia — ChromaDB Client

Modul ini mengelola koneksi ke ChromaDB server (via Docker) dan
menyediakan akses ke tiga collection utama:

    1. berita           — embedding berita dari berbagai sumber
    2. laporan_keuangan — embedding teks dari PDF laporan keuangan
    3. data_makro       — embedding ringkasan/analisis makroekonomi

Setiap collection menggunakan cosine similarity untuk pencarian
vektor, karena embedding BGE-M3 sudah dinormalisasi (L2 norm = 1).

Penggunaan:
    from backend.db.chroma import get_chroma_client, get_collection

    client = get_chroma_client()
    col_berita = get_collection("berita")

    # Atau langsung:
    col_berita = get_collection("berita")
"""

import threading
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from loguru import logger

from backend.config import settings

# ============================================================
# Nama-nama collection yang digunakan
# ============================================================

COLLECTION_BERITA = "berita"
COLLECTION_LAPORAN = "laporan_keuangan"
COLLECTION_MAKRO = "data_makro"

ALL_COLLECTIONS = [COLLECTION_BERITA, COLLECTION_LAPORAN, COLLECTION_MAKRO]

# ============================================================
# Singleton ChromaDB Client
# ============================================================

_client: ClientAPI | None = None
_client_lock = threading.Lock()


def get_chroma_client() -> ClientAPI:
    """
    Dapatkan singleton ChromaDB HTTP client.

    Client terhubung ke ChromaDB server yang berjalan di Docker.
    Menggunakan singleton pattern agar koneksi tidak dibuat berulang.

    Returns:
        chromadb.HttpClient yang sudah terkoneksi

    Raises:
        ConnectionError: Jika ChromaDB server tidak bisa dihubungi
    """
    global _client

    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client

        logger.info(
            f"🔌 Menghubungkan ke ChromaDB: "
            f"{settings.chroma_host}:{settings.chroma_port}..."
        )

        try:
            _client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            # Verifikasi koneksi
            heartbeat = _client.heartbeat()
            logger.info(f"✅ ChromaDB terhubung (heartbeat: {heartbeat})")

            return _client

        except Exception as e:
            _client = None
            logger.error(
                f"❌ Gagal koneksi ke ChromaDB: {type(e).__name__}: {e}\n"
                f"💡 Pastikan ChromaDB berjalan: docker compose up -d chromadb"
            )
            raise ConnectionError(
                f"Tidak bisa terhubung ke ChromaDB di "
                f"{settings.chroma_host}:{settings.chroma_port}"
            ) from e


def get_collection(
    nama: str,
    create_if_not_exists: bool = True,
) -> Collection:
    """
    Dapatkan ChromaDB collection berdasarkan nama.

    Args:
        nama: Nama collection (gunakan konstanta COLLECTION_*)
        create_if_not_exists: Buat collection jika belum ada

    Returns:
        chromadb Collection object

    Example:
        >>> col = get_collection(COLLECTION_BERITA)
        >>> col.count()
        1234
    """
    client = get_chroma_client()

    try:
        if create_if_not_exists:
            collection = client.get_or_create_collection(
                name=nama,
                metadata={
                    "hnsw:space": "cosine",  # Cosine similarity (BGE-M3 normalized)
                    "description": f"AI Saham Indonesia — {nama}",
                },
            )
        else:
            collection = client.get_collection(name=nama)

        logger.debug(
            f"📂 Collection '{nama}': {collection.count()} dokumen"
        )
        return collection

    except Exception as e:
        logger.error(f"❌ Gagal akses collection '{nama}': {e}")
        raise


def init_all_collections() -> dict[str, Collection]:
    """
    Inisialisasi semua collection yang dibutuhkan.

    Membuat collection jika belum ada. Aman dijalankan berulang
    karena menggunakan get_or_create_collection.

    Returns:
        Dict mapping nama collection ke Collection object
    """
    logger.info("📂 Menginisialisasi semua ChromaDB collections...")

    collections: dict[str, Collection] = {}
    for nama in ALL_COLLECTIONS:
        collections[nama] = get_collection(nama, create_if_not_exists=True)

    logger.info(
        f"✅ {len(collections)} collections siap: "
        f"{', '.join(f'{n} ({c.count()})' for n, c in collections.items())}"
    )

    return collections


def reset_collection(nama: str) -> Collection:
    """
    ⚠️ Hapus dan buat ulang collection (semua data hilang).

    Hanya untuk development/testing.
    """
    client = get_chroma_client()
    logger.warning(f"⚠️  Mereset collection '{nama}' — semua data akan hilang!")

    try:
        client.delete_collection(name=nama)
    except Exception:
        pass  # Collection mungkin belum ada

    return get_collection(nama, create_if_not_exists=True)
