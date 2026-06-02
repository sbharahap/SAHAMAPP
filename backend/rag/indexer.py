"""
AI Saham Indonesia — RAG Indexer

Modul ini menangani proses indexing dokumen ke ChromaDB menggunakan
LlamaIndex sebagai orchestrator dan BGE-M3 sebagai embedding model.

Alur indexing:
    1. Terima teks mentah + metadata
    2. Chunk teks menjadi potongan 512 token dengan overlap 64 token
    3. Embed setiap chunk menggunakan BGE-M3 (via embedder.py singleton)
    4. Simpan embedding + metadata ke ChromaDB collection yang sesuai

Tiga collection tersedia:
    - berita           : berita dari RSS, web scraping
    - laporan_keuangan : teks dari PDF laporan keuangan emiten
    - data_makro       : ringkasan dan analisis makroekonomi

Penggunaan:
    from backend.rag.indexer import index_dokumen, index_batch_berita

    # Index satu dokumen
    await index_dokumen(
        teks="BBCA cetak laba bersih Rp 10 triliun...",
        metadata={
            "kode_saham": "BBCA",
            "jenis_dokumen": "berita",
            "tanggal": "2024-01-15",
            "sumber": "kontan",
        }
    )

    # Index batch berita dari collector
    await index_batch_berita(berita_list)

Catatan:
    - BGE-M3 di-load sekali (singleton) dan tetap di memori
    - Chunking menggunakan LlamaIndex SentenceSplitter (token-based)
    - Metadata disimpan bersama embedding di ChromaDB untuk filtering
"""

import asyncio
import hashlib
import uuid
from datetime import date, datetime
from typing import Any, Literal

from loguru import logger

from backend.data.preprocessors.embedder import get_embedder
from backend.db.chroma import (
    COLLECTION_BERITA,
    COLLECTION_LAPORAN,
    COLLECTION_MAKRO,
    get_collection,
)

# ============================================================
# Konfigurasi Chunking
# ============================================================

# Ukuran chunk dalam karakter (estimasi: 1 token ≈ 4 karakter untuk Indonesia)
# 512 token × 4 = 2048 karakter
_CHUNK_SIZE: int = 512
_CHUNK_OVERLAP: int = 64

# Tipe dokumen yang valid
JenisDokumen = Literal["berita", "laporan_keuangan", "data_makro"]

# Mapping jenis dokumen ke nama collection ChromaDB
_COLLECTION_MAP: dict[str, str] = {
    "berita": COLLECTION_BERITA,
    "laporan_keuangan": COLLECTION_LAPORAN,
    "data_makro": COLLECTION_MAKRO,
}


# ============================================================
# LlamaIndex Custom Embedding Adapter
# ============================================================

def _get_llama_embedding_model() -> Any:
    """
    Buat LlamaIndex-compatible embedding model yang membungkus
    BGE-M3 singleton dari embedder.py.

    LlamaIndex butuh objek yang mengimplementasikan BaseEmbedding.
    Kita buat custom class yang mendelegasikan ke BGEEmbedder.

    Returns:
        LlamaIndex BaseEmbedding instance
    """
    from llama_index.core.embeddings import BaseEmbedding
    from pydantic import PrivateAttr

    class BGEM3LlamaIndexAdapter(BaseEmbedding):
        """
        Adapter agar BGE-M3 singleton bisa dipakai oleh LlamaIndex.

        Mendelegasikan semua operasi embedding ke BGEEmbedder singleton
        yang sudah ada, sehingga model tidak di-load ulang.
        """

        _embedder: Any = PrivateAttr()

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                model_name="BAAI/bge-m3",
                embed_batch_size=32,
                **kwargs,
            )
            self._embedder = get_embedder()

        @classmethod
        def class_name(cls) -> str:
            return "BGEM3LlamaIndexAdapter"

        def _get_query_embedding(self, query: str) -> list[float]:
            """Embed query pencarian."""
            return self._embedder.encode([query])[0]

        def _get_text_embedding(self, text: str) -> list[float]:
            """Embed satu teks dokumen."""
            return self._embedder.encode([text])[0]

        def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
            """Embed batch teks dokumen (lebih efisien)."""
            return self._embedder.encode(texts)

        # Versi async — delegasi ke sync karena BGE-M3 sudah efisien
        async def _aget_query_embedding(self, query: str) -> list[float]:
            return await asyncio.to_thread(self._get_query_embedding, query)

        async def _aget_text_embedding(self, text: str) -> list[float]:
            return await asyncio.to_thread(self._get_text_embedding, text)

        async def _aget_text_embeddings(
            self, texts: list[str]
        ) -> list[list[float]]:
            return await asyncio.to_thread(self._get_text_embeddings, texts)

    return BGEM3LlamaIndexAdapter()


# ============================================================
# Text Chunking
# ============================================================

def _chunk_teks(
    teks: str,
    chunk_size: int = _CHUNK_SIZE,
    chunk_overlap: int = _CHUNK_OVERLAP,
) -> list[str]:
    """
    Potong teks menjadi chunk-chunk berukuran tetap dengan overlap.

    Menggunakan LlamaIndex SentenceSplitter yang memotong di batas
    kalimat (bukan di tengah kata). Ini menghasilkan chunk yang
    lebih natural dan meaningful.

    Args:
        teks: Teks lengkap yang akan dipotong
        chunk_size: Ukuran maksimum per chunk (dalam token)
        chunk_overlap: Overlap antar chunk (dalam token)

    Returns:
        List of string, setiap string adalah satu chunk
    """
    if not teks or not teks.strip():
        return []

    try:
        from llama_index.core.node_parser import SentenceSplitter

        splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # SentenceSplitter.split_text() mengembalikan list of str
        chunks = splitter.split_text(teks)

        # Filter chunk kosong
        chunks = [c.strip() for c in chunks if c.strip()]

        logger.debug(
            f"✂️  Teks ({len(teks)} char) dipotong menjadi "
            f"{len(chunks)} chunk (size={chunk_size}, overlap={chunk_overlap})"
        )

        return chunks

    except Exception as e:
        logger.error(f"❌ Error saat chunking: {type(e).__name__}: {e}")
        # Fallback: potong manual berdasarkan karakter
        # Estimasi: 1 token ≈ 4 karakter
        char_size = chunk_size * 4
        char_overlap = chunk_overlap * 4
        chunks = []
        start = 0
        while start < len(teks):
            end = min(start + char_size, len(teks))
            chunk = teks[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += char_size - char_overlap

        return chunks


def _generate_doc_id(teks: str, metadata: dict[str, Any]) -> str:
    """
    Generate ID unik untuk dokumen berdasarkan konten dan metadata.

    Menggunakan hash SHA-256 agar dokumen yang sama tidak
    disimpan duplikat di ChromaDB.

    Args:
        teks: Teks chunk
        metadata: Metadata dokumen

    Returns:
        String ID unik (hex hash)
    """
    # Buat fingerprint dari konten + metadata kunci
    fingerprint = (
        f"{metadata.get('kode_saham', '')}"
        f"|{metadata.get('sumber', '')}"
        f"|{metadata.get('tanggal', '')}"
        f"|{metadata.get('url', '')}"  # Tambahkan URL agar unik per artikel
        f"|{teks[:200]}"  # 200 char pertama dari teks
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]


def _serialize_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """
    Serialisasi metadata ke format yang diterima ChromaDB.

    ChromaDB hanya menerima metadata dengan nilai bertipe:
    str, int, float, bool. Tipe lain (date, datetime, None)
    perlu dikonversi.

    Args:
        metadata: Metadata original

    Returns:
        Metadata yang sudah diserialisasi
    """
    serialized: dict[str, str | int | float | bool] = {}

    for key, value in metadata.items():
        if value is None:
            serialized[key] = ""  # ChromaDB tidak terima None
        elif isinstance(value, (date, datetime)):
            serialized[key] = value.isoformat()
        elif isinstance(value, bool):
            serialized[key] = value
        elif isinstance(value, (int, float)):
            serialized[key] = value
        else:
            serialized[key] = str(value)

    return serialized


# ============================================================
# Fungsi Utama: Index Dokumen
# ============================================================

async def index_dokumen(
    teks: str,
    metadata: dict[str, Any],
    jenis_dokumen: JenisDokumen = "berita",
) -> int:
    """
    Index satu dokumen ke ChromaDB.

    Proses:
    1. Chunk teks menjadi potongan 512 token (overlap 64)
    2. Embed setiap chunk menggunakan BGE-M3
    3. Simpan embedding + metadata ke collection yang sesuai

    Args:
        teks: Teks lengkap dokumen
        metadata: Metadata wajib:
            - kode_saham (str): Kode saham terkait (contoh: "BBCA")
            - tanggal (str/date): Tanggal dokumen
            - sumber (str): Sumber dokumen (contoh: "kontan", "idx")
        jenis_dokumen: Tipe dokumen ("berita", "laporan_keuangan", "data_makro")

    Returns:
        Jumlah chunk yang berhasil di-index

    Example:
        >>> count = await index_dokumen(
        ...     teks="BBCA cetak laba bersih Rp 10 triliun di Q1 2024...",
        ...     metadata={"kode_saham": "BBCA", "tanggal": "2024-01-15", "sumber": "kontan"},
        ...     jenis_dokumen="berita",
        ... )
        >>> print(f"{count} chunk di-index")
    """
    if not teks or not teks.strip():
        logger.warning("⚠️  Teks kosong, skip indexing")
        return 0

    # Validasi jenis dokumen
    if jenis_dokumen not in _COLLECTION_MAP:
        raise ValueError(
            f"jenis_dokumen harus salah satu dari {list(_COLLECTION_MAP.keys())}, "
            f"bukan '{jenis_dokumen}'"
        )

    # Tambahkan jenis_dokumen ke metadata
    metadata_full = {
        **metadata,
        "jenis_dokumen": jenis_dokumen,
    }

    # Step 1: Chunk teks
    chunks = await asyncio.to_thread(_chunk_teks, teks)
    if not chunks:
        logger.warning("⚠️  Tidak ada chunk yang dihasilkan, skip indexing")
        return 0

    # Step 2: Embed semua chunk sekaligus (batch, efisien)
    embedder = get_embedder()
    embeddings = await asyncio.to_thread(
        embedder.encode,
        chunks,
    )

    # Step 3: Siapkan data untuk ChromaDB
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int | float | bool]] = []
    embedding_list: list[list[float]] = []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        # ID unik per chunk
        chunk_metadata = {
            **metadata_full,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        doc_id = _generate_doc_id(chunk, chunk_metadata)

        ids.append(doc_id)
        documents.append(chunk)
        metadatas.append(_serialize_metadata(chunk_metadata))
        embedding_list.append(embedding)

    # Step 4: Simpan ke ChromaDB
    collection_name = _COLLECTION_MAP[jenis_dokumen]
    try:
        collection = await asyncio.to_thread(get_collection, collection_name)

        # Upsert: update jika ID sudah ada, insert jika belum
        await asyncio.to_thread(
            collection.upsert,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embedding_list,
        )

        logger.info(
            f"📥 Indexed {len(chunks)} chunk ke '{collection_name}' "
            f"[{metadata_full.get('kode_saham', '?')} | "
            f"{metadata_full.get('sumber', '?')}]"
        )

        return len(chunks)

    except Exception as e:
        logger.error(
            f"❌ Gagal index ke '{collection_name}': "
            f"{type(e).__name__}: {e}"
        )
        raise


async def index_batch_berita(
    berita_list: list[dict[str, Any]],
    batch_size: int = 20,
) -> dict[str, int]:
    """
    Index banyak berita sekaligus ke ChromaDB collection 'berita'.

    Memproses berita secara batch untuk efisiensi. Setiap berita
    di-chunk dan di-embed, lalu disimpan ke ChromaDB.

    Args:
        berita_list: List of dict dari berita_collector, setiap dict berisi:
            - judul (str): Judul berita
            - kode_saham (str|None): Kode saham terkait
            - url (str): URL sumber
            - sumber (str): Nama sumber
            - tanggal_publish (datetime): Tanggal publish
        batch_size: Jumlah berita per batch embedding

    Returns:
        Dict statistik:
            - total: Jumlah berita yang diproses
            - berhasil: Jumlah berita berhasil di-index
            - gagal: Jumlah berita yang gagal
            - total_chunks: Total chunk yang dihasilkan

    Example:
        >>> from backend.data.collectors import collect_berita
        >>> berita = await collect_berita("BBCA")
        >>> stats = await index_batch_berita(berita)
        >>> print(stats)
        {"total": 15, "berhasil": 14, "gagal": 1, "total_chunks": 42}
    """
    logger.info(f"📰 Memulai batch indexing: {len(berita_list)} berita...")

    stats = {
        "total": len(berita_list),
        "berhasil": 0,
        "gagal": 0,
        "total_chunks": 0,
    }

    if not berita_list:
        return stats

    # Kumpulkan semua teks dan metadata terlebih dahulu
    all_chunks: list[str] = []
    all_chunk_metas: list[dict[str, Any]] = []
    berita_chunk_map: list[tuple[int, int]] = []  # (start_idx, end_idx) per berita

    for berita in berita_list:
        try:
            # Teks untuk indexing: gabungan judul (berita dari RSS biasanya hanya judul)
            teks = berita.get("judul", "").strip()
            if not teks:
                stats["gagal"] += 1
                continue

            # Chunk teks
            chunks = _chunk_teks(teks)
            if not chunks:
                # Teks terlalu pendek untuk di-chunk, gunakan apa adanya
                chunks = [teks]

            start_idx = len(all_chunks)

            metadata = {
                "kode_saham": berita.get("kode_saham", "") or "",
                "jenis_dokumen": "berita",
                "tanggal": berita.get("tanggal_publish", ""),
                "sumber": berita.get("sumber", ""),
                "url": berita.get("url", ""),
                "judul": berita.get("judul", "")[:200],
            }

            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_chunk_metas.append({
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })

            end_idx = len(all_chunks)
            berita_chunk_map.append((start_idx, end_idx))

        except Exception as e:
            logger.error(
                f"❌ Error preprocessing berita '{berita.get('judul', '?')[:50]}': "
                f"{type(e).__name__}: {e}"
            )
            stats["gagal"] += 1

    if not all_chunks:
        logger.warning("⚠️  Tidak ada chunk untuk di-embed")
        return stats

    # Batch embed semua chunk sekaligus (jauh lebih efisien)
    logger.info(f"🧠 Embedding {len(all_chunks)} chunk dari {len(berita_list)} berita...")

    try:
        embedder = get_embedder()

        # Proses embedding dalam batch
        all_embeddings: list[list[float]] = []
        for batch_start in range(0, len(all_chunks), batch_size):
            batch_end = min(batch_start + batch_size, len(all_chunks))
            batch_texts = all_chunks[batch_start:batch_end]

            batch_embeddings = await asyncio.to_thread(
                embedder.encode,
                batch_texts,
            )
            all_embeddings.extend(batch_embeddings)

            logger.debug(
                f"🧠 Batch {batch_start//batch_size + 1}: "
                f"embedded {len(batch_texts)} chunk"
            )

    except Exception as e:
        logger.error(f"❌ Gagal embedding batch: {type(e).__name__}: {e}")
        stats["gagal"] = stats["total"]
        return stats

    # Simpan ke ChromaDB
    try:
        collection = await asyncio.to_thread(get_collection, COLLECTION_BERITA)

        # Siapkan data untuk upsert (dan hilangkan ID duplikat dalam satu batch)
        unique_ids: list[str] = []
        unique_chunks: list[str] = []
        unique_metas: list[dict] = []
        unique_embeddings: list[list[float]] = []

        seen_ids = set()
        for i, (chunk, meta) in enumerate(zip(all_chunks, all_chunk_metas)):
            doc_id = _generate_doc_id(chunk, meta)
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_ids.append(doc_id)
                unique_chunks.append(chunk)
                unique_metas.append(_serialize_metadata(meta))
                unique_embeddings.append(all_embeddings[i])

        # Upsert dalam batch ke ChromaDB
        chroma_batch_size = 100  # ChromaDB optimal batch size
        for batch_start in range(0, len(unique_ids), chroma_batch_size):
            batch_end = min(batch_start + chroma_batch_size, len(unique_ids))

            await asyncio.to_thread(
                collection.upsert,
                ids=unique_ids[batch_start:batch_end],
                documents=unique_chunks[batch_start:batch_end],
                metadatas=unique_metas[batch_start:batch_end],
                embeddings=unique_embeddings[batch_start:batch_end],
            )

        stats["berhasil"] = stats["total"] - stats["gagal"]
        stats["total_chunks"] = len(all_chunks)

        logger.info(
            f"✅ Batch indexing selesai: "
            f"{stats['berhasil']}/{stats['total']} berita berhasil, "
            f"{stats['total_chunks']} total chunk"
        )

    except Exception as e:
        logger.error(f"❌ Gagal simpan ke ChromaDB: {type(e).__name__}: {e}")
        stats["gagal"] = stats["total"]
        stats["berhasil"] = 0

    return stats


async def index_laporan_keuangan(
    teks: str,
    kode_saham: str,
    periode: str,
    sumber: str = "idx",
) -> int:
    """
    Index teks laporan keuangan emiten ke ChromaDB.

    Digunakan setelah ekstraksi teks dari PDF laporan keuangan.

    Args:
        teks: Teks lengkap (atau sebagian) laporan keuangan
        kode_saham: Kode saham emiten
        periode: Periode laporan (contoh: "Q1 2024", "FY 2023")
        sumber: Sumber dokumen (default: "idx")

    Returns:
        Jumlah chunk yang berhasil di-index
    """
    return await index_dokumen(
        teks=teks,
        metadata={
            "kode_saham": kode_saham.upper(),
            "tanggal": date.today().isoformat(),
            "sumber": sumber,
            "periode": periode,
        },
        jenis_dokumen="laporan_keuangan",
    )


async def index_data_makro(
    teks: str,
    indikator: str,
    sumber: str = "bank_indonesia",
) -> int:
    """
    Index teks ringkasan/analisis makroekonomi ke ChromaDB.

    Args:
        teks: Teks analisis atau ringkasan data makro
        indikator: Nama indikator (contoh: "bi_rate", "inflasi")
        sumber: Sumber data (default: "bank_indonesia")

    Returns:
        Jumlah chunk yang berhasil di-index
    """
    return await index_dokumen(
        teks=teks,
        metadata={
            "kode_saham": "",
            "tanggal": date.today().isoformat(),
            "sumber": sumber,
            "indikator": indikator,
        },
        jenis_dokumen="data_makro",
    )
