"""
AI Saham Indonesia — RAG Retriever

Modul ini menangani pencarian dokumen relevan dari ChromaDB
berdasarkan query pengguna. Mendukung filtering per saham,
per jenis dokumen, dan query perbandingan multi-saham.

Alur retrieval:
    1. Terima query dalam Bahasa Indonesia
    2. Embed query menggunakan BGE-M3 (sama dengan model indexing)
    3. Cari vektor terdekat di ChromaDB (cosine similarity)
    4. Filter berdasarkan metadata (kode_saham, jenis_dokumen)
    5. Return dokumen yang relevan beserta skor

Penggunaan:
    from backend.rag.retriever import retrieve, retrieve_multi_saham

    # Pencarian umum
    hasil = await retrieve("Bagaimana kinerja bank di Q1 2024?")

    # Pencarian spesifik per saham
    hasil = await retrieve(
        "Laba bersih kuartal terakhir",
        kode_saham="BBCA",
        top_k=5,
    )

    # Perbandingan antar saham
    hasil = await retrieve_multi_saham(
        "Perbandingan ROE dan pertumbuhan laba",
        kode_list=["BBCA", "BMRI", "BBNI"],
        top_k_per_saham=3,
    )

Catatan:
    - Skor relevansi menggunakan cosine similarity (0-1, makin tinggi = makin mirip)
    - ChromaDB mengembalikan distance (bukan similarity) untuk cosine,
      jadi kita konversi: similarity = 1 - distance
"""

import asyncio
from typing import Any, Literal

from loguru import logger

from backend.data.preprocessors.embedder import get_embedder
from backend.db.chroma import (
    COLLECTION_BERITA,
    COLLECTION_LAPORAN,
    COLLECTION_MAKRO,
    get_collection,
)

# Mapping jenis dokumen ke collection
_COLLECTION_MAP: dict[str, str] = {
    "berita": COLLECTION_BERITA,
    "laporan_keuangan": COLLECTION_LAPORAN,
    "data_makro": COLLECTION_MAKRO,
}

# Tipe jenis dokumen
JenisDokumen = Literal["berita", "laporan_keuangan", "data_makro"]


def _build_where_filter(
    kode_saham: str | None = None,
    sumber: str | None = None,
    tanggal_dari: str | None = None,
    tanggal_sampai: str | None = None,
) -> dict[str, Any] | None:
    """
    Bangun filter 'where' untuk query ChromaDB.

    ChromaDB mendukung filtering metadata menggunakan operator
    $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or.

    Args:
        kode_saham: Filter berdasarkan kode saham (contoh: "BBCA")
        sumber: Filter berdasarkan sumber (contoh: "kontan")
        tanggal_dari: Filter tanggal minimal (format ISO: "2024-01-01")
        tanggal_sampai: Filter tanggal maksimal (format ISO: "2024-12-31")

    Returns:
        Dict filter ChromaDB, atau None jika tidak ada filter
    """
    conditions: list[dict[str, Any]] = []

    if kode_saham:
        conditions.append({"kode_saham": {"$eq": kode_saham.upper()}})

    if sumber:
        conditions.append({"sumber": {"$eq": sumber.lower()}})

    if tanggal_dari:
        conditions.append({"tanggal": {"$gte": tanggal_dari}})

    if tanggal_sampai:
        conditions.append({"tanggal": {"$lte": tanggal_sampai}})

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


def _format_result(
    document: str,
    metadata: dict[str, Any],
    distance: float,
) -> dict[str, Any]:
    """
    Format satu hasil pencarian menjadi dict yang konsisten.

    Konversi ChromaDB distance (cosine) menjadi similarity score.
    Untuk cosine distance: similarity = 1 - distance

    Args:
        document: Teks dokumen yang ditemukan
        metadata: Metadata dokumen dari ChromaDB
        distance: Cosine distance dari ChromaDB

    Returns:
        Dict dengan field: teks, metadata, skor_relevansi
    """
    # Cosine distance → similarity score
    # ChromaDB cosine distance: 0 = identik, 2 = berlawanan
    skor_relevansi = max(0.0, 1.0 - distance)

    return {
        "teks": document,
        "metadata": dict(metadata),
        "skor_relevansi": round(skor_relevansi, 4),
    }


async def retrieve(
    query: str,
    kode_saham: str | None = None,
    jenis_dokumen: JenisDokumen | None = None,
    sumber: str | None = None,
    tanggal_dari: str | None = None,
    tanggal_sampai: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Cari dokumen relevan berdasarkan query.

    Proses:
    1. Embed query menggunakan BGE-M3
    2. Query ChromaDB dengan cosine similarity
    3. Filter berdasarkan metadata (opsional)
    4. Return top_k dokumen paling relevan

    Args:
        query: Pertanyaan atau kata kunci pencarian (Bahasa Indonesia/Inggris)
        kode_saham: Filter hanya untuk saham tertentu (contoh: "BBCA")
        jenis_dokumen: Filter jenis dokumen (berita/laporan_keuangan/data_makro)
                       Jika None, cari di SEMUA collection
        sumber: Filter berdasarkan sumber (contoh: "kontan")
        tanggal_dari: Filter tanggal minimal (ISO format)
        tanggal_sampai: Filter tanggal maksimal (ISO format)
        top_k: Jumlah dokumen yang dikembalikan (default: 5)

    Returns:
        List of dict, setiap dict berisi:
            - teks (str): Teks dokumen yang relevan
            - metadata (dict): Metadata dokumen (kode_saham, sumber, dll)
            - skor_relevansi (float): 0.0-1.0 (makin tinggi = makin relevan)

        List diurutkan dari skor tertinggi ke terendah.

    Example:
        >>> results = await retrieve(
        ...     "Laba bersih BBCA kuartal 1",
        ...     kode_saham="BBCA",
        ...     top_k=3,
        ... )
        >>> for r in results:
        ...     print(f"[{r['skor_relevansi']:.2f}] {r['teks'][:80]}...")
        [0.85] BBCA melaporkan laba bersih sebesar Rp 12,1 triliun di kuartal...
        [0.72] Bank Central Asia mencatat pertumbuhan laba bersih 10% YoY...
        [0.68] Kinerja BBCA di Q1 2024 melampaui ekspektasi konsensus...
    """
    if not query or not query.strip():
        logger.warning("⚠️  Query kosong, return empty")
        return []

    logger.info(
        f"🔍 Retrieve: '{query[:80]}' "
        f"(saham={kode_saham or 'semua'}, "
        f"jenis={jenis_dokumen or 'semua'}, "
        f"top_k={top_k})"
    )

    # Step 1: Embed query
    embedder = get_embedder()
    query_embedding = await asyncio.to_thread(
        embedder.encode,
        [query],
    )
    query_vec = query_embedding[0]

    # Step 2: Tentukan collection mana yang akan di-query
    if jenis_dokumen:
        collection_names = [_COLLECTION_MAP[jenis_dokumen]]
    else:
        # Cari di semua collection
        collection_names = list(_COLLECTION_MAP.values())

    # Step 3: Build filter
    where_filter = _build_where_filter(
        kode_saham=kode_saham,
        sumber=sumber,
        tanggal_dari=tanggal_dari,
        tanggal_sampai=tanggal_sampai,
    )

    # Step 4: Query setiap collection
    all_results: list[dict[str, Any]] = []

    for col_name in collection_names:
        try:
            collection = await asyncio.to_thread(get_collection, col_name, False)

            # Cek apakah collection punya dokumen
            count = await asyncio.to_thread(collection.count)
            if count == 0:
                logger.debug(f"📂 Collection '{col_name}' kosong, skip")
                continue

            # Query ChromaDB
            # n_results tidak boleh melebihi jumlah dokumen
            n = min(top_k, count)

            query_params: dict[str, Any] = {
                "query_embeddings": [query_vec],
                "n_results": n,
                "include": ["documents", "metadatas", "distances"],
            }

            if where_filter:
                query_params["where"] = where_filter

            results = await asyncio.to_thread(
                collection.query,
                **query_params,
            )

            # Parse hasil
            if results and results.get("documents"):
                documents = results["documents"][0]  # [0] karena 1 query
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]

                for doc, meta, dist in zip(documents, metadatas, distances):
                    if doc:  # Skip None documents
                        formatted = _format_result(doc, meta, dist)
                        formatted["metadata"]["collection"] = col_name
                        all_results.append(formatted)

        except Exception as e:
            # Collection mungkin tidak ada (belum pernah diindex)
            logger.debug(
                f"⚠️  Error query collection '{col_name}': "
                f"{type(e).__name__}: {e}"
            )
            continue

    # Step 5: Sort berdasarkan skor relevansi (descending)
    all_results.sort(key=lambda x: x["skor_relevansi"], reverse=True)

    # Ambil top_k dari gabungan semua collection
    final_results = all_results[:top_k]

    logger.info(
        f"🔍 Ditemukan {len(final_results)} dokumen relevan "
        f"(dari {len(all_results)} total di {len(collection_names)} collection)"
    )

    for i, r in enumerate(final_results, 1):
        logger.debug(
            f"   #{i} [{r['skor_relevansi']:.3f}] "
            f"({r['metadata'].get('collection', '?')}) "
            f"{r['teks'][:60]}..."
        )

    return final_results


async def retrieve_multi_saham(
    query: str,
    kode_list: list[str],
    jenis_dokumen: JenisDokumen | None = None,
    top_k_per_saham: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """
    Cari dokumen untuk beberapa saham sekaligus (perbandingan).

    Berguna untuk query seperti "Bandingkan kinerja BBCA vs BMRI"
    yang membutuhkan konteks dari masing-masing saham.

    Setiap saham mendapat top_k_per_saham dokumen terpisah,
    dikelompokkan berdasarkan kode saham.

    Args:
        query: Pertanyaan pencarian
        kode_list: List kode saham yang ingin dibandingkan
        jenis_dokumen: Filter jenis dokumen (opsional)
        top_k_per_saham: Jumlah dokumen per saham (default: 3)

    Returns:
        Dict mapping kode_saham → list of hasil retrieval

    Example:
        >>> results = await retrieve_multi_saham(
        ...     "Perbandingan ROE dan pertumbuhan laba",
        ...     kode_list=["BBCA", "BMRI", "BBNI"],
        ...     top_k_per_saham=3,
        ... )
        >>> for kode, docs in results.items():
        ...     print(f"\\n{kode}: {len(docs)} dokumen")
        ...     for d in docs:
        ...         print(f"  [{d['skor_relevansi']:.2f}] {d['teks'][:60]}")
        BBCA: 3 dokumen
          [0.85] BBCA melaporkan ROE sebesar 21% di FY 2023...
          ...
        BMRI: 3 dokumen
          [0.81] PT Bank Mandiri mencatat pertumbuhan laba...
          ...
    """
    logger.info(
        f"🔍 Multi-retrieve: '{query[:60]}' untuk "
        f"{len(kode_list)} saham ({', '.join(kode_list)})"
    )

    results: dict[str, list[dict[str, Any]]] = {}

    # Query setiap saham secara parallel
    tasks = []
    for kode in kode_list:
        kode_clean = kode.strip().upper()
        tasks.append(
            retrieve(
                query=query,
                kode_saham=kode_clean,
                jenis_dokumen=jenis_dokumen,
                top_k=top_k_per_saham,
            )
        )

    # Jalankan semua query secara parallel
    task_results = await asyncio.gather(*tasks, return_exceptions=True)

    for kode, result in zip(kode_list, task_results):
        kode_clean = kode.strip().upper()
        if isinstance(result, Exception):
            logger.error(
                f"❌ Gagal retrieve untuk {kode_clean}: "
                f"{type(result).__name__}: {result}"
            )
            results[kode_clean] = []
        else:
            results[kode_clean] = result

    total_docs = sum(len(docs) for docs in results.values())
    logger.info(
        f"🔍 Multi-retrieve selesai: {total_docs} dokumen total "
        f"untuk {len(kode_list)} saham"
    )

    return results


async def retrieve_context_for_scoring(
    kode_saham: str,
    top_k_berita: int = 5,
    top_k_laporan: int = 3,
    top_k_makro: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """
    Ambil konteks lengkap untuk scoring satu saham.

    Mengambil dokumen dari ketiga collection (berita, laporan, makro)
    secara parallel. Digunakan oleh scoring agent untuk mengumpulkan
    informasi sebelum memberikan rekomendasi.

    Args:
        kode_saham: Kode saham yang akan di-scoring
        top_k_berita: Jumlah berita terbaru
        top_k_laporan: Jumlah chunk laporan keuangan
        top_k_makro: Jumlah data makro

    Returns:
        Dict dengan 3 key: "berita", "laporan_keuangan", "data_makro"
        Setiap value adalah list of dict hasil retrieval

    Example:
        >>> ctx = await retrieve_context_for_scoring("BBCA")
        >>> print(f"Berita: {len(ctx['berita'])}")
        >>> print(f"Laporan: {len(ctx['laporan_keuangan'])}")
        >>> print(f"Makro: {len(ctx['data_makro'])}")
    """
    kode = kode_saham.strip().upper()
    logger.info(f"📋 Mengambil konteks scoring untuk {kode}...")

    # Query untuk setiap jenis dokumen — disesuaikan untuk relevansi
    query_berita = f"berita terbaru saham {kode} kinerja prospek"
    query_laporan = f"laporan keuangan {kode} laba pendapatan aset"
    query_makro = "kondisi ekonomi Indonesia suku bunga inflasi pertumbuhan"

    # Jalankan semua query secara parallel
    berita_task = retrieve(
        query=query_berita,
        kode_saham=kode,
        jenis_dokumen="berita",
        top_k=top_k_berita,
    )
    laporan_task = retrieve(
        query=query_laporan,
        kode_saham=kode,
        jenis_dokumen="laporan_keuangan",
        top_k=top_k_laporan,
    )
    makro_task = retrieve(
        query=query_makro,
        jenis_dokumen="data_makro",
        top_k=top_k_makro,
    )

    results = await asyncio.gather(
        berita_task,
        laporan_task,
        makro_task,
        return_exceptions=True,
    )

    context: dict[str, list[dict[str, Any]]] = {
        "berita": results[0] if not isinstance(results[0], Exception) else [],
        "laporan_keuangan": results[1] if not isinstance(results[1], Exception) else [],
        "data_makro": results[2] if not isinstance(results[2], Exception) else [],
    }

    # Log error jika ada
    for i, (name, res) in enumerate(zip(
        ["berita", "laporan_keuangan", "data_makro"], results
    )):
        if isinstance(res, Exception):
            logger.error(f"❌ Gagal retrieve {name}: {res}")

    total = sum(len(docs) for docs in context.values())
    logger.info(
        f"📋 Konteks scoring {kode}: "
        f"{len(context['berita'])} berita, "
        f"{len(context['laporan_keuangan'])} laporan, "
        f"{len(context['data_makro'])} makro "
        f"({total} total)"
    )

    return context
