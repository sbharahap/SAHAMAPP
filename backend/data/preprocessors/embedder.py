"""
AI Saham Indonesia — BGE-M3 Embedder (Singleton)

Modul ini menyediakan embedding model BGE-M3 dari HuggingFace untuk
mengubah teks (berita, laporan keuangan, transkrip) menjadi vektor
yang disimpan di ChromaDB.

BGE-M3 dipilih karena:
    - Bilingual ID/EN — memahami teks Bahasa Indonesia dan Inggris
    - Ukuran sedang (~2GB RAM) — muat di Apple Silicon 16GB
    - Kualitas embedding tinggi di benchmark MTEB

Desain:
    - SINGLETON pattern: model di-load sekali saja saat pertama kali
      dibutuhkan, lalu disimpan di memori untuk panggilan berikutnya
    - Thread-safe via threading.Lock
    - Cache model lokal agar tidak re-download setiap kali
    - Batch processing dengan ukuran yang efisien untuk RAM 16GB

Penggunaan:
    from backend.data.preprocessors.embedder import (
        embed_dokumen,
        embed_batch,
    )

    # Embed satu dokumen
    vektor = embed_dokumen("BBCA cetak laba bersih Rp 10 triliun")
    # vektor = [0.0123, -0.0456, ...] (1024 dimensi)

    # Embed banyak dokumen sekaligus (lebih efisien)
    vektors = embed_batch(["berita 1", "berita 2", "berita 3"])

    # Akses model langsung (advanced)
    embedder = get_embedder()
    model = embedder.model  # SentenceTransformer instance

Catatan:
    - Pertama kali dijalankan akan download model (~1.5GB)
    - Setelah itu model di-cache di ~/.cache/huggingface/
    - Di Apple Silicon, otomatis menggunakan MPS (Metal) untuk akselerasi
"""

import threading
from typing import Any

from loguru import logger

from backend.config import settings


class BGEEmbedder:
    """
    Singleton wrapper untuk model embedding BGE-M3.

    Model di-load secara lazy (saat pertama kali dibutuhkan) dan
    disimpan sebagai class attribute. Thread-safe via Lock.

    Attributes:
        model: Instance SentenceTransformer yang sudah di-load
        dimension: Dimensi vektor output (1024 untuk BGE-M3)

    Catatan Memory:
        BGE-M3 membutuhkan ~2GB RAM setelah di-load.
        Dengan batch_size=32, peak memory ~3-4GB saat embed_batch.
        Aman untuk mesin dengan RAM 16GB (masih sisa ~12GB
        untuk PostgreSQL, ChromaDB, dan OS).
    """

    _instance: "BGEEmbedder | None" = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "BGEEmbedder":
        """Singleton: hanya buat satu instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Inisialisasi embedder.

        Model TIDAK di-load di sini (lazy loading).
        Panggil _ensure_model_loaded() untuk load model.
        """
        # Hindari re-inisialisasi pada singleton
        if BGEEmbedder._initialized:
            return
        BGEEmbedder._initialized = True

        self._model: Any = None  # SentenceTransformer, di-load lazy
        self._model_name: str = settings.embedding_model
        self._device: str = settings.embedding_device
        self._batch_size: int = settings.embedding_batch_size
        self._dimension: int | None = None  # Diisi setelah model di-load

        logger.info(
            f"🧠 BGEEmbedder dikonfigurasi: "
            f"model={self._model_name}, device={self._device}, "
            f"batch_size={self._batch_size}"
        )

    def _ensure_model_loaded(self) -> None:
        """
        Load model jika belum di-load (lazy loading + thread-safe).

        Model hanya di-load sekali. Panggilan berikutnya langsung
        menggunakan model yang sudah ada di memori.
        """
        if self._model is not None:
            return

        with self._lock:
            # Double-check setelah acquire lock
            if self._model is not None:
                return

            logger.info(
                f"⏳ Loading embedding model: {self._model_name} "
                f"(pertama kali bisa butuh beberapa menit untuk download)..."
            )

            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    self._model_name,
                    device=self._device,
                    # Cache model di direktori default HuggingFace
                    # (~/.cache/huggingface/hub/)
                    trust_remote_code=True,
                )

                # Dapatkan dimensi embedding
                test_embedding = self._model.encode(
                    ["test"],
                    show_progress_bar=False,
                )
                self._dimension = len(test_embedding[0])

                logger.info(
                    f"✅ Model {self._model_name} berhasil di-load! "
                    f"Dimensi: {self._dimension}, Device: {self._device}"
                )

            except Exception as e:
                logger.error(
                    f"❌ Gagal load model {self._model_name}: "
                    f"{type(e).__name__}: {e}"
                )
                raise RuntimeError(
                    f"Gagal load embedding model. "
                    f"Pastikan sentence-transformers terinstall dan "
                    f"device '{self._device}' tersedia. Error: {e}"
                ) from e

    @property
    def model(self) -> Any:
        """Akses model SentenceTransformer (auto-load jika belum)."""
        self._ensure_model_loaded()
        return self._model

    @property
    def dimension(self) -> int:
        """Dimensi vektor embedding (1024 untuk BGE-M3)."""
        self._ensure_model_loaded()
        assert self._dimension is not None
        return self._dimension

    def encode(
        self,
        texts: list[str],
        batch_size: int | None = None,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> list[list[float]]:
        """
        Encode list teks menjadi list vektor embedding.

        Args:
            texts: List teks yang akan di-embed
            batch_size: Ukuran batch (None = gunakan default dari config)
            show_progress: Tampilkan progress bar
            normalize: Normalisasi vektor ke unit length (L2 norm = 1)
                       Penting untuk cosine similarity di ChromaDB

        Returns:
            List of list[float], setiap inner list adalah vektor embedding
        """
        self._ensure_model_loaded()
        assert self._model is not None

        if not texts:
            return []

        effective_batch_size = batch_size or self._batch_size

        logger.debug(
            f"🧠 Encoding {len(texts)} teks, "
            f"batch_size={effective_batch_size}..."
        )

        try:
            embeddings = self._model.encode(
                texts,
                batch_size=effective_batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=normalize,
                # convert_to_numpy=True sudah default
            )

            # Konversi numpy array ke list[list[float]] untuk serialisasi
            result = [embedding.tolist() for embedding in embeddings]

            logger.debug(
                f"✅ Encoding selesai: {len(result)} vektor, "
                f"dimensi={len(result[0]) if result else 0}"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error saat encoding: {type(e).__name__}: {e}")
            raise

    def unload(self) -> None:
        """
        Unload model dari memori untuk membebaskan RAM.

        Berguna jika perlu memuat model lain atau menghemat memori
        saat embedding tidak dibutuhkan untuk waktu yang lama.
        """
        if self._model is not None:
            logger.info(f"🗑️ Unloading model {self._model_name}...")
            del self._model
            self._model = None

            # Force garbage collection untuk bebaskan memori GPU/MPS
            import gc
            gc.collect()

            try:
                import torch
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except (ImportError, AttributeError):
                pass

            logger.info("✅ Model berhasil di-unload dari memori")


# ============================================================
# Singleton Instance & Public API
# ============================================================

def get_embedder() -> BGEEmbedder:
    """
    Dapatkan singleton instance BGEEmbedder.

    Returns:
        BGEEmbedder instance (model belum tentu sudah di-load,
        akan di-load otomatis saat pertama kali digunakan)
    """
    return BGEEmbedder()


def embed_dokumen(teks: str) -> list[float]:
    """
    Ubah satu teks menjadi vektor embedding.

    Wrapper sederhana untuk kasus embed satu dokumen saja.
    Untuk banyak dokumen, gunakan embed_batch() yang lebih efisien.

    Args:
        teks: Teks yang akan di-embed (berita, laporan, dll)

    Returns:
        List[float] — vektor embedding (1024 dimensi untuk BGE-M3)

    Example:
        >>> vektor = embed_dokumen("BBCA cetak laba Rp 10 triliun")
        >>> len(vektor)
        1024
        >>> type(vektor[0])
        <class 'float'>
    """
    if not teks or not teks.strip():
        logger.warning("⚠️ Teks kosong, mengembalikan zero vector")
        embedder = get_embedder()
        embedder._ensure_model_loaded()
        return [0.0] * embedder.dimension

    result = get_embedder().encode([teks])
    return result[0]


def embed_batch(
    teks_list: list[str],
    batch_size: int | None = None,
    show_progress: bool = True,
) -> list[list[float]]:
    """
    Ubah banyak teks menjadi vektor embedding sekaligus.

    Lebih efisien daripada memanggil embed_dokumen() berulang kali
    karena GPU/MPS bisa memproses batch secara paralel.

    Estimasi performa di Apple Silicon M1/M2 (16GB RAM):
        - batch_size=32: ~50-100 teks/detik
        - batch_size=16: ~30-60 teks/detik (lebih hemat RAM)
        - batch_size=64: ~80-120 teks/detik (butuh RAM lebih)

    Args:
        teks_list: List teks yang akan di-embed
        batch_size: Override batch size (None = gunakan default dari config)
        show_progress: Tampilkan progress bar (berguna untuk batch besar)

    Returns:
        List[List[float]] — list vektor embedding, urutan sama dengan input

    Example:
        >>> vektors = embed_batch(["berita 1", "berita 2", "berita 3"])
        >>> len(vektors)
        3
        >>> len(vektors[0])
        1024
    """
    if not teks_list:
        return []

    # Filter teks kosong dan ganti dengan placeholder
    # (agar index output tetap sesuai dengan input)
    embedder = get_embedder()
    cleaned: list[str] = []
    empty_indices: set[int] = set()

    for i, teks in enumerate(teks_list):
        if not teks or not teks.strip():
            empty_indices.add(i)
            cleaned.append("kosong")  # Placeholder, akan diganti zero vector
        else:
            cleaned.append(teks.strip())

    logger.info(
        f"🧠 Memulai batch embedding: {len(cleaned)} teks "
        f"({len(empty_indices)} kosong akan di-skip)"
    )

    results = embedder.encode(
        cleaned,
        batch_size=batch_size,
        show_progress=show_progress,
    )

    # Ganti embedding placeholder dengan zero vector
    if empty_indices:
        zero_vec = [0.0] * embedder.dimension
        for idx in empty_indices:
            results[idx] = zero_vec

    logger.info(f"✅ Batch embedding selesai: {len(results)} vektor dihasilkan")

    return results
