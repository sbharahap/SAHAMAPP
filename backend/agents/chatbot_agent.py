"""
AI Saham Indonesia — LangGraph RAG Chatbot Agent

Chatbot yang menjawab pertanyaan tentang saham Indonesia secara natural
dalam Bahasa Indonesia, dengan konteks dari ChromaDB (RAG) dan data
fundamental dari PostgreSQL.

Arsitektur LangGraph StateGraph:

    ┌───────────────────────────────────┐
    │             START                 │
    └──────────┬────────────────────────┘
               │
    ┌──────────▼────────────────────────┐
    │  1. klasifikasi_pertanyaan        │
    │     - Klasifikasi jenis query     │
    │     - Ekstrak kode saham          │
    │     - Deteksi pertanyaan ambigu   │
    └──────────┬────────────┬───────────┘
               │            │
          (bukan ambigu)  (ambigu)
               │            │
               │     ┌──────▼──────┐
               │     │    END      │ ← jawaban klarifikasi
               │     └─────────────┘
    ┌──────────▼────────────────────────┐
    │  2. ambil_konteks                 │
    │     - RAG dari ChromaDB           │
    │     - Data fundamental PostgreSQL │
    │     - Skor scoring minggu ini     │
    └──────────┬────────────────────────┘
               │
    ┌──────────▼────────────────────────┐
    │  3. generate_jawaban              │
    │     - Susun prompt + konteks      │
    │     - Panggil Qwen3 via Ollama    │
    │     - Jawab dalam Bahasa ID       │
    └──────────┬────────────────────────┘
               │
    ┌──────────▼────────────────────────┐
    │  4. cek_kualitas (conditional)    │
    │     - Confidence < 0.5 → retry   │
    │     - Confidence ≥ 0.5 → END     │
    └──────────┬────────────┬───────────┘
               │            │
         (confidence OK)  (retry)
               │            │
    ┌──────────▼──────┐     │
    │      END        │     │
    └─────────────────┘     │
               ┌────────────▼───────────┐
               │  2. ambil_konteks      │ ← top_k lebih besar
               │     (retry)            │
               └────────────────────────┘

Penggunaan:
    from backend.agents.chatbot_agent import chat

    # Pertanyaan spesifik
    result = await chat("Bagaimana kinerja BBCA kuartal ini?")
    print(result["jawaban"])

    # Dengan riwayat percakapan
    result = await chat(
        "Bagaimana dibanding BMRI?",
        riwayat=[
            {"role": "user", "content": "Bagaimana kinerja BBCA?"},
            {"role": "assistant", "content": "BBCA menunjukkan kinerja solid..."},
        ]
    )
"""

import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from loguru import logger
from sqlalchemy import select

from backend.config import settings
from backend.db.postgres import (
    Fundamental,
    Saham,
    ScoringMingguan,
    async_session,
)
from backend.rag.retriever import retrieve, retrieve_multi_saham

# Timezone WIB
_WIB = timezone(timedelta(hours=7))


# ============================================================
# State Definition
# ============================================================

class ChatState(TypedDict):
    """
    State yang mengalir melalui LangGraph chatbot pipeline.

    Setiap node membaca dan menulis ke state ini.
    """
    pertanyaan_original: str       # Input: pertanyaan user asli
    jenis_pertanyaan: str          # "spesifik" / "perbandingan" / "ambigu" / "umum"
    saham_yang_ditanyakan: list[str]  # Kode saham yang terdeteksi
    dokumen_relevan: list[dict]    # Hasil retrieval dari ChromaDB
    data_angka: dict               # Data fundamental & skor dari PostgreSQL
    jawaban_draft: str             # Jawaban draft dari LLM
    confidence: float              # Confidence score 0-1
    perlu_dokumen_tambahan: bool   # Flag untuk retry retrieval
    jawaban_final: str             # Jawaban final ke user
    riwayat: list[dict]            # Conversation history
    _retry_count: int              # Counter retry internal


# ============================================================
# LLM Setup
# ============================================================

def _get_llm() -> ChatOllama:
    """Buat instance ChatOllama yang terhubung ke Qwen3 lokal."""
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.5,  # Sedikit lebih rendah untuk chatbot (lebih faktual)
        num_ctx=settings.ollama_num_ctx,
        timeout=settings.ollama_timeout,
    )


# ============================================================
# Mapping Nama Perusahaan → Kode Saham
# ============================================================

# Daftar alias umum nama perusahaan ke kode saham
# Digunakan untuk mendeteksi saham dari nama informal
_ALIAS_SAHAM: dict[str, str] = {
    # Bank
    "bca": "BBCA", "bank bca": "BBCA", "bank central asia": "BBCA",
    "bri": "BBRI", "bank bri": "BBRI", "bank rakyat": "BBRI",
    "bni": "BBNI", "bank bni": "BBNI", "bank negara": "BBNI",
    "mandiri": "BMRI", "bank mandiri": "BMRI",
    "btn": "BBTN", "bank btn": "BBTN", "bank tabungan": "BBTN",
    "danamon": "BDMN", "bank danamon": "BDMN",
    "permata": "BNLI", "bank permata": "BNLI",
    "cimb niaga": "BNGA", "cimb": "BNGA",

    # Telekomunikasi
    "telkom": "TLKM", "telekomunikasi": "TLKM", "telkomsel": "TLKM",
    "indosat": "ISAT", "ooredoo": "ISAT",
    "xl": "EXCL", "xl axiata": "EXCL",

    # Otomotif & Konglomerasi
    "astra": "ASII", "astra international": "ASII",
    "united tractors": "UNTR",

    # Konsumer
    "unilever": "UNVR", "indofood": "INDF",
    "gudang garam": "GGRM", "hm sampoerna": "HMSP", "sampoerna": "HMSP",

    # Pertambangan & Energi
    "antam": "ANTM", "aneka tambang": "ANTM",
    "vale": "INCO", "vale indonesia": "INCO",
    "bukit asam": "PTBA", "adaro": "ADRO",
    "medco": "MEDC", "medco energi": "MEDC",

    # Properti
    "bsd": "BSDE", "bumi serpong": "BSDE",
    "ciputra": "CTRA",
    "pakuwon": "PWON",
    "summarecon": "SMRA",

    # Teknologi
    "ggrm": "GGRM", "gudang garam": "GGRM", "gudanggaram": "GGRM",
    "bukalapak": "BUKA",

    # Lainnya
    "ace hardware": "ACES", "aces": "ACES",
    "kalbe": "KLBF", "kalbe farma": "KLBF",
    "sido muncul": "SIDO",
}

# Regex untuk mendeteksi kode saham 4 huruf
_KODE_SAHAM_PATTERN = re.compile(r"\b([A-Z]{4})\b")


# ============================================================
# NODE 1: Klasifikasi Pertanyaan
# ============================================================

async def klasifikasi_pertanyaan(state: ChatState) -> dict[str, Any]:
    """
    Klasifikasi pertanyaan user dan ekstrak kode saham yang dimaksud.

    Langkah:
    1. Deteksi kode saham dari teks (4 huruf kapital atau alias nama)
    2. Gunakan LLM untuk klasifikasi jenis pertanyaan jika perlu
    3. Tentukan: spesifik / perbandingan / ambigu / umum

    Jika pertanyaan ambigu, langsung set jawaban_final dengan
    pertanyaan klarifikasi dan arahkan ke END.

    Returns:
        Update state: jenis_pertanyaan, saham_yang_ditanyakan, jawaban_final (jika ambigu)
    """
    pertanyaan = state["pertanyaan_original"]
    riwayat = state.get("riwayat", [])

    logger.info(f"💬 NODE 1: Klasifikasi — \"{pertanyaan[:80]}\"")

    # ─── Langkah 1: Ekstrak kode saham dari teks ───
    saham_ditemukan: list[str] = []

    # Cari kode saham 4 huruf (e.g., BBCA, TLKM)
    kode_matches = _KODE_SAHAM_PATTERN.findall(pertanyaan.upper())
    for kode in kode_matches:
        if kode not in saham_ditemukan:
            saham_ditemukan.append(kode)

    # Cari dari alias nama perusahaan
    pertanyaan_lower = pertanyaan.lower()
    # Sort alias by length descending agar "bank central asia" cocok sebelum "bank"
    sorted_aliases = sorted(_ALIAS_SAHAM.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in pertanyaan_lower:
            kode = _ALIAS_SAHAM[alias]
            if kode not in saham_ditemukan:
                saham_ditemukan.append(kode)

    # ─── Langkah 2: Cek riwayat jika tidak ada saham di pertanyaan saat ini ───
    if not saham_ditemukan and riwayat:
        # Coba ambil saham dari percakapan sebelumnya (konteks)
        for msg in reversed(riwayat):
            content = msg.get("content", "")
            prev_codes = _KODE_SAHAM_PATTERN.findall(content.upper())
            if prev_codes:
                saham_ditemukan = list(dict.fromkeys(prev_codes))  # Deduplicate, keep order
                logger.debug(
                    f"   📝 Saham dari riwayat: {saham_ditemukan}"
                )
                break

    # ─── Langkah 3: Klasifikasi jenis pertanyaan ───
    jenis: str

    # Deteksi perbandingan
    kata_banding = [
        "banding", "versus", " vs ", " vs.", "dibanding",
        "lebih baik", "mana yang", "antara", "pilih mana",
        "perbandingan", "compare",
    ]
    is_perbandingan = any(k in pertanyaan_lower for k in kata_banding)

    # Deteksi pertanyaan umum (tentang pasar, sektor, makro)
    kata_umum = [
        "ihsg", "pasar", "market", "sektor", "industri",
        "bi rate", "suku bunga", "inflasi", "kurs", "rupiah",
        "ekonomi", "makro", "rekomendasi minggu", "top 10",
        "saham terbaik", "saham bagus",
    ]
    is_umum = any(k in pertanyaan_lower for k in kata_umum)

    if len(saham_ditemukan) >= 2 or is_perbandingan:
        jenis = "perbandingan"
    elif len(saham_ditemukan) == 1:
        jenis = "spesifik"
    else:
        # Jika tidak ada kode saham terdeteksi, selalu gunakan LLM untuk klasifikasi
        # untuk memastikan relevansi dan menghindari kecocokan kata kunci semu.
        jenis = await _klasifikasi_dengan_llm(pertanyaan, riwayat)
        if jenis == "ambigu":
            logger.info(f"   ❓ Pertanyaan tidak relevan / ambigu, kembalikan penolakan")
            return {
                "jenis_pertanyaan": "ambigu",
                "saham_yang_ditanyakan": [],
                "jawaban_final": (
                    "Mohon maaf, saya hanya dapat menjawab pertanyaan seputar analisis saham, emiten IDX, investasi, dan ekonomi makro."
                ),
            }

    logger.info(
        f"   📋 Jenis: {jenis}, Saham: {saham_ditemukan or '(tidak spesifik)'}"
    )

    return {
        "jenis_pertanyaan": jenis,
        "saham_yang_ditanyakan": saham_ditemukan,
    }


async def _klasifikasi_dengan_llm(
    pertanyaan: str,
    riwayat: list[dict],
) -> str:
    """
    Gunakan LLM untuk mengklasifikasi pertanyaan yang tidak jelas.

    Ini dipanggil hanya jika deteksi rule-based tidak bisa menentukan
    jenis pertanyaan. LLM membantu mendeteksi pertanyaan implisit.

    Returns:
        "spesifik", "perbandingan", "umum", atau "ambigu"
    """
    try:
        llm = _get_llm()

        # Sertakan riwayat untuk konteks
        riwayat_teks = ""
        if riwayat:
            riwayat_teks = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Asisten'}: {m['content'][:100]}"
                for m in riwayat[-4:]  # 4 pesan terakhir
            )
            riwayat_teks = f"\nRiwayat percakapan:\n{riwayat_teks}\n"

        prompt = f"""Klasifikasikan pertanyaan berikut ke salah satu kategori:
- "spesifik": tentang satu saham tertentu
- "perbandingan": membandingkan 2 atau lebih saham
- "umum": tentang pasar, sektor, atau ekonomi secara umum
- "ambigu": tidak jelas apa yang ditanyakan, atau sama sekali TIDAK RELEVAN (out of scope) dengan dunia saham, pasar modal, emiten IDX, keuangan, investasi, atau analisis makroekonomi.
{riwayat_teks}
Pertanyaan: "{pertanyaan}"

Jawab HANYA dengan satu kata: spesifik, perbandingan, umum, atau ambigu
/no_think"""

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = response.content.strip().lower()

        # Parse jawaban LLM
        for kategori in ["spesifik", "perbandingan", "umum", "ambigu"]:
            if kategori in result:
                return kategori

        return "umum"  # Default

    except Exception as e:
        logger.debug(f"⚠️  LLM klasifikasi gagal: {e}, fallback ke 'umum'")
        return "umum"


def _route_setelah_klasifikasi(state: ChatState) -> str:
    """
    Router setelah klasifikasi pertanyaan.

    - Ambigu → langsung END (jawaban klarifikasi sudah di-set)
    - Lainnya → lanjut ke ambil_konteks
    """
    if state.get("jenis_pertanyaan") == "ambigu":
        return "end"
    return "ambil_konteks"


# ============================================================
# NODE 2: Ambil Konteks
# ============================================================

async def ambil_konteks(state: ChatState) -> dict[str, Any]:
    """
    Ambil konteks dari ChromaDB (RAG) dan PostgreSQL untuk menjawab.

    Sumber konteks:
    1. ChromaDB: dokumen relevan (berita, laporan, makro)
    2. PostgreSQL: data fundamental terbaru
    3. PostgreSQL: skor scoring mingguan terbaru
    4. PostgreSQL: data top 10 rekomendasi mingguan terbaru (jika ditanyakan)

    Jika ini retry (perlu_dokumen_tambahan=True), top_k diperbesar.

    Returns:
        Update state: dokumen_relevan, data_angka
    """
    pertanyaan = state["pertanyaan_original"]
    saham_list = state.get("saham_yang_ditanyakan", [])
    jenis = state.get("jenis_pertanyaan", "umum")
    is_retry = state.get("perlu_dokumen_tambahan", False)

    # Pada retry, perbesar jumlah dokumen
    top_k = 10 if is_retry else 5

    logger.info(
        f"📚 NODE 2: Ambil Konteks "
        f"(jenis={jenis}, saham={saham_list}, top_k={top_k}"
        f"{', RETRY' if is_retry else ''})"
    )

    dokumen_relevan: list[dict[str, Any]] = []
    data_angka: dict[str, Any] = {}

    # ─── Langkah 1: Retrieval dari ChromaDB ───
    try:
        if jenis == "perbandingan" and len(saham_list) >= 2:
            # Query per saham untuk perbandingan
            multi_results = await retrieve_multi_saham(
                query=pertanyaan,
                kode_list=saham_list,
                top_k_per_saham=max(3, top_k // len(saham_list)),
            )
            for kode, docs in multi_results.items():
                for doc in docs:
                    doc["metadata"]["query_saham"] = kode
                    dokumen_relevan.append(doc)

        elif jenis == "spesifik" and saham_list:
            # Query spesifik untuk satu saham
            dokumen_relevan = await retrieve(
                query=pertanyaan,
                kode_saham=saham_list[0],
                top_k=top_k,
            )

        else:
            # Query umum tanpa filter saham
            dokumen_relevan = await retrieve(
                query=pertanyaan,
                top_k=top_k,
            )

        logger.info(f"   📄 {len(dokumen_relevan)} dokumen dari ChromaDB")

    except Exception as e:
        logger.error(f"   ❌ Gagal retrieval ChromaDB: {type(e).__name__}: {e}")

    # ─── Langkah 2: Data dari PostgreSQL ───
    try:
        async with async_session() as session:
            # 2a. Deteksi apakah user menanyakan rekomendasi / top 10 secara umum
            pertanyaan_lower = pertanyaan.lower()
            minta_rekomendasi = any(
                k in pertanyaan_lower for k in [
                    "rekomendasi", "top 10", "saham terbaik", "pilihan saham",
                    "rekomendasi minggu", "scoring", "saham bagus"
                ]
            ) and not saham_list
            if minta_rekomendasi:
                # Cari tanggal scoring terakhir di DB
                stmt_date = (
                    select(ScoringMingguan.tanggal_scoring)
                    .order_by(ScoringMingguan.tanggal_scoring.desc())
                    .limit(1)
                )
                res_date = await session.execute(stmt_date)
                tanggal_terakhir = res_date.scalar_one_or_none()

                if tanggal_terakhir:
                    # Ambil TOP 10 saham teratas di tanggal scoring tersebut
                    stmt_top10 = (
                        select(ScoringMingguan, Saham.nama_perusahaan, Saham.sektor)
                        .join(Saham, ScoringMingguan.kode_saham == Saham.kode)
                        .where(ScoringMingguan.tanggal_scoring == tanggal_terakhir)
                        .order_by(ScoringMingguan.skor_total.desc())
                        .limit(settings.top_k_saham)
                    )
                    res_top10 = await session.execute(stmt_top10)
                    rows = res_top10.all()

                    daftar_rekomendasi = []
                    for idx, row in enumerate(rows, 1):
                        scoring_obj, nama_pt, sektor = row
                        daftar_rekomendasi.append({
                            "rank": idx,
                            "kode_saham": scoring_obj.kode_saham,
                            "nama_perusahaan": nama_pt,
                            "sektor": sektor,
                            "skor_total": scoring_obj.skor_total,
                            "rekomendasi": scoring_obj.rekomendasi.value,
                            "confidence": scoring_obj.confidence,
                            "alasan": scoring_obj.alasan or "",
                        })

                    if daftar_rekomendasi:
                        data_angka["TOP_10_REKOMENDASI"] = {
                            "judul": f"TOP 10 REKOMENDASI SAHAM MINGGU INI ({tanggal_terakhir.isoformat()})",
                            "daftar": daftar_rekomendasi
                        }
                        logger.info(f"   📈 Menambahkan TOP 10 Rekomendasi ({tanggal_terakhir}) ke konteks chatbot.")

            # 2b. Data fundamental & scoring spesifik jika ada saham_list
            if saham_list:
                for kode in saham_list:
                    saham_data: dict[str, Any] = {"kode": kode}

                    # Info perusahaan
                    stmt_saham = select(Saham).where(Saham.kode == kode)
                    result = await session.execute(stmt_saham)
                    saham_obj = result.scalar_one_or_none()
                    if saham_obj:
                        saham_data["nama"] = saham_obj.nama_perusahaan
                        saham_data["sektor"] = saham_obj.sektor

                    # Fundamental terbaru yang memiliki data rasio (roe tidak NULL)
                    stmt_fund = (
                        select(Fundamental)
                        .where(
                            Fundamental.kode_saham == kode,
                            Fundamental.roe.is_not(None)
                        )
                        .order_by(Fundamental.tanggal.desc())
                        .limit(1)
                    )
                    result = await session.execute(stmt_fund)
                    fund = result.scalar_one_or_none()

                    # Fallback jika tidak ada data yang memiliki rasio
                    if not fund:
                        stmt_fund_fallback = (
                            select(Fundamental)
                            .where(Fundamental.kode_saham == kode)
                            .order_by(Fundamental.tanggal.desc())
                            .limit(1)
                        )
                        result_fallback = await session.execute(stmt_fund_fallback)
                        fund = result_fallback.scalar_one_or_none()
                    if fund:
                        saham_data["fundamental"] = {
                            "harga": fund.harga_terakhir,
                            "volume": fund.volume,
                            "roe": fund.roe,
                            "eps": fund.eps,
                            "pbv": fund.pbv,
                            "der": fund.der,
                            "pe_ratio": fund.pe_ratio,
                            "market_cap": fund.market_cap,
                            "dividend_yield": fund.dividend_yield,
                            "tanggal": fund.tanggal.isoformat() if fund.tanggal else None,
                        }

                    # Skor scoring terbaru
                    stmt_skor = (
                        select(ScoringMingguan)
                        .where(ScoringMingguan.kode_saham == kode)
                        .order_by(ScoringMingguan.tanggal_scoring.desc())
                        .limit(1)
                    )
                    result = await session.execute(stmt_skor)
                    scoring = result.scalar_one_or_none()
                    if scoring:
                        saham_data["scoring"] = {
                            "skor_total": scoring.skor_total,
                            "skor_fundamental": scoring.skor_fundamental,
                            "skor_sentimen": scoring.skor_sentimen,
                            "skor_sektor": scoring.skor_sektor,
                            "skor_makro": scoring.skor_makro,
                            "skor_risiko": scoring.skor_risiko,
                            "rekomendasi": scoring.rekomendasi.value,
                            "alasan": scoring.alasan,
                            "confidence": scoring.confidence,
                            "tanggal": scoring.tanggal_scoring.isoformat(),
                        }

                    data_angka[kode] = saham_data
                    logger.debug(
                        f"   📊 {kode}: "
                        f"{'ada' if fund else 'tidak ada'} fundamental, "
                        f"{'ada' if scoring else 'tidak ada'} scoring"
                    )

    except Exception as e:
        logger.error(f"   ❌ Gagal baca PostgreSQL: {type(e).__name__}: {e}")

    logger.info(
        f"   📊 Data angka untuk {len(data_angka)} saham/entitas"
    )

    return {
        "dokumen_relevan": dokumen_relevan,
        "data_angka": data_angka,
        "perlu_dokumen_tambahan": False,  # Reset flag retry
    }


# ============================================================
# NODE 3: Generate Jawaban
# ============================================================

async def generate_jawaban(state: ChatState) -> dict[str, Any]:
    """
    Generate jawaban menggunakan LLM dengan konteks lengkap.

    Prompt disusun dari:
    1. System prompt dengan instruksi gaya jawaban
    2. Riwayat percakapan (conversation memory)
    3. Dokumen relevan dari ChromaDB
    4. Data fundamental dan skor dari PostgreSQL
    5. Pertanyaan user

    Returns:
        Update state: jawaban_draft, confidence, jawaban_final
    """
    pertanyaan = state["pertanyaan_original"]
    jenis = state.get("jenis_pertanyaan", "umum")
    saham_list = state.get("saham_yang_ditanyakan", [])
    dokumen = state.get("dokumen_relevan", [])
    data_angka = state.get("data_angka", {})
    riwayat = state.get("riwayat", [])

    logger.info(f"🤖 NODE 3: Generate Jawaban")

    # ─── Susun konteks dokumen ───
    konteks_docs = ""
    if dokumen:
        konteks_docs = "DOKUMEN REFERENSI:\n"
        for i, doc in enumerate(dokumen[:7], 1):  # Max 7 dokumen
            sumber = doc.get("metadata", {}).get("sumber", "?")
            skor = doc.get("skor_relevansi", 0)
            teks = doc.get("teks", "")[:300]
            konteks_docs += f"[{i}] (sumber: {sumber}, relevansi: {skor:.2f})\n{teks}\n\n"

    # ─── Susun konteks data angka ───
    konteks_angka = ""
    if data_angka:
        konteks_angka = "DATA SAHAM:\n"
        for kode, data in data_angka.items():
            if kode == "TOP_10_REKOMENDASI":
                konteks_angka += f"\n=== {data['judul']} ===\n"
                for item in data["daftar"]:
                    konteks_angka += (
                        f"Rank #{item['rank']}: {item['kode_saham']} ({item['nama_perusahaan']}) | "
                        f"Sektor: {item['sektor']} | Skor: {item['skor_total']:.1f}/100 -> "
                        f"{item['rekomendasi']} (Conf: {item['confidence']:.2f})\n"
                        f"Analisis: {item['alasan']}\n"
                    )
                konteks_angka += "=====================================\n"
                continue

            konteks_angka += f"\n--- {kode}"
            nama = data.get("nama", "")
            if nama:
                konteks_angka += f" ({nama})"
            konteks_angka += f" | Sektor: {data.get('sektor', 'N/A')} ---\n"

            fund = data.get("fundamental", {})
            if fund:
                konteks_angka += (
                    f"Harga: Rp {fund.get('harga', 'N/A'):,} | "
                    f"ROE: {fund.get('roe', 'N/A')}% | "
                    f"EPS: Rp {fund.get('eps', 'N/A')} | "
                    f"PBV: {fund.get('pbv', 'N/A')}x | "
                    f"DER: {fund.get('der', 'N/A')}x | "
                    f"PE: {fund.get('pe_ratio', 'N/A')}x | "
                    f"Div Yield: {fund.get('dividend_yield', 'N/A')}%\n"
                ) if fund.get('harga') else "Fundamental: data tidak tersedia\n"

            scoring = data.get("scoring", {})
            if scoring:
                konteks_angka += (
                    f"Skor: {scoring.get('skor_total', 'N/A')}/100 → "
                    f"{scoring.get('rekomendasi', 'N/A')} "
                    f"(confidence: {scoring.get('confidence', 'N/A')})\n"
                    f"Detail: F={scoring.get('skor_fundamental', 'N/A')} "
                    f"S={scoring.get('skor_sentimen', 'N/A')} "
                    f"K={scoring.get('skor_sektor', 'N/A')} "
                    f"M={scoring.get('skor_makro', 'N/A')} "
                    f"R={scoring.get('skor_risiko', 'N/A')}\n"
                )
                if scoring.get("alasan"):
                    konteks_angka += f"Analisis: {scoring['alasan'][:200]}\n"

    # ─── Susun riwayat percakapan ───
    konteks_riwayat = ""
    if riwayat:
        konteks_riwayat = "RIWAYAT PERCAKAPAN:\n"
        # Ambil 6 pesan terakhir agar tidak terlalu panjang
        for msg in riwayat[-6:]:
            role = "User" if msg["role"] == "user" else "Asisten"
            konteks_riwayat += f"{role}: {msg['content'][:200]}\n"
        konteks_riwayat += "\n"

    # ─── Penyesuaian batas kata ───
    # Jika ada data top 10 rekomendasi, naikkan batas kata ke 450 agar muat daftarnya
    minta_top10 = "TOP_10_REKOMENDASI" in data_angka
    word_limit = 450 if minta_top10 else 200

    # ─── Instruksi khusus berdasarkan jenis pertanyaan ───
    instruksi_jenis = {
        "spesifik": (
            "Jawab tentang saham spesifik yang ditanyakan. "
            "Sertakan data angka yang relevan jika tersedia."
        ),
        "perbandingan": (
            "Bandingkan saham-saham yang ditanyakan secara objektif. "
            "Buat tabel perbandingan jika memungkinkan. "
            "Berikan kesimpulan mana yang lebih menarik dan mengapa."
        ),
        "umum": (
            "Jawab pertanyaan tentang pasar/sektor/ekonomi secara umum. "
            "Jika data rekomendasi/top 20 tersedia di DATA SAHAM, sebutkan daftarnya "
            "secara berurutan (dari rank #1 sampai #20) beserta skor total dan rekomendasinya (RECOMMENDED/NEUTRAL/NEGATIVE) "
            "secara padat dan informatif."
        ),
    }

    instruksi = instruksi_jenis.get(jenis, instruksi_jenis["umum"])

    # ─── Bangun prompt ───
    system_prompt = f"""Kamu adalah asisten analis saham Indonesia yang cerdas dan ramah.

ATURAN UTAMA — WAJIB DIPATUHI:
1. Jawab HANYA berdasarkan informasi yang ada di DOKUMEN REFERENSI dan DATA SAHAM yang diberikan di bawah.
2. DILARANG KERAS mengarang, menambah, atau mengasumsikan data angka (harga, ROE, PBV, laba, dll) yang tidak tercantum dalam konteks.
3. Jika data yang dibutuhkan TIDAK ADA dalam konteks, katakan secara eksplisit: "Data [X] tidak tersedia dalam referensi saat ini."
4. Jangan menggunakan pengetahuan umum tentang saham di luar dokumen yang diberikan.

ATURAN FORMAT:
5. Jawab dalam Bahasa Indonesia yang natural dan mudah dipahami
6. Maksimal {word_limit} kata, padat dan informatif
7. Jangan gunakan format markdown kompleks
8. HANYA jawab pertanyaan user secara langsung, jangan menambahkan disclaimer bukan saran investasi di dalam bubble jawaban (disclaimer sudah ada di luar bubble).
9. {instruksi}
10. Akhiri jawaban dengan baris baru dan tulis confidence score-mu (0.0-1.0) dalam format: [CONFIDENCE: X.X]
    - Berikan confidence tinggi (>0.7) HANYA jika dokumen relevan mendukung jawaban secara langsung
    - Berikan confidence rendah (<0.5) jika dokumen kurang relevan atau data tidak lengkap

/no_think"""

    user_prompt = f"""{konteks_riwayat}{konteks_angka}
{konteks_docs}
PERTANYAAN USER:
{pertanyaan}

INGAT: Jawab hanya berdasarkan DOKUMEN REFERENSI dan DATA SAHAM di atas. Jika data tidak ada, katakan tidak tersedia."""

    # ─── Panggil LLM ───
    try:
        llm = _get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm.ainvoke(messages)
        response_text = response.content.strip()

        # Parse confidence dari response
        jawaban, confidence = _parse_jawaban_dan_confidence(response_text)

        logger.info(
            f"   ✅ Jawaban generated ({len(jawaban)} char, "
            f"confidence={confidence:.2f})"
        )

        # RAG Triad Evaluasi (fire-and-forget, batch_id="live" untuk tracking)
        if dokumen:
            contexts_list = [doc.get("teks", "") for doc in dokumen[:7]]
            from backend.rag.evaluator import evaluasi_rag_triad
            asyncio.create_task(
                evaluasi_rag_triad(
                    pertanyaan, contexts_list, jawaban,
                    batch_id="live", simpan_ke_db=True,
                )
            )

        return {
            "jawaban_draft": jawaban,
            "confidence": confidence,
            "jawaban_final": jawaban,
        }

    except Exception as e:
        logger.error(f"   ❌ Gagal generate jawaban: {type(e).__name__}: {e}")

        # Fallback: jawaban dari data yang tersedia tanpa LLM
        fallback = _generate_jawaban_fallback(
            pertanyaan, saham_list, data_angka, dokumen
        )

        return {
            "jawaban_draft": fallback,
            "confidence": 0.3,
            "jawaban_final": fallback,
        }


def _parse_jawaban_dan_confidence(response: str) -> tuple[str, float]:
    """
    Parse jawaban dan confidence score dari response LLM.

    LLM diminta menuliskan [CONFIDENCE: X.X] di akhir jawaban.

    Args:
        response: Response mentah dari LLM

    Returns:
        Tuple (jawaban_bersih, confidence)
    """
    confidence = 0.7  # Default

    # Cari pattern [CONFIDENCE: X.X]
    match = re.search(
        r"\[CONFIDENCE:\s*([\d.]+)\]",
        response,
        re.IGNORECASE,
    )

    if match:
        try:
            confidence = float(match.group(1))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            pass
        # Hapus tag confidence dari jawaban
        jawaban = response[:match.start()].strip()
    else:
        jawaban = response.strip()

    # Bersihkan trailing whitespace dan newlines
    jawaban = jawaban.rstrip()

    return jawaban, confidence


def _generate_jawaban_fallback(
    pertanyaan: str,
    saham_list: list[str],
    data_angka: dict[str, Any],
    dokumen: list[dict[str, Any]],
) -> str:
    """
    Generate jawaban tanpa LLM (fallback jika Ollama tidak tersedia).

    Menggunakan data yang tersedia untuk menyusun jawaban template.
    """
    parts = []

    # 1. Handle TOP_10_REKOMENDASI jika ada
    if "TOP_10_REKOMENDASI" in data_angka:
        data = data_angka["TOP_10_REKOMENDASI"]
        parts.append(f"=== {data['judul']} ===")
        for item in data["daftar"]:
            parts.append(
                f"{item['rank']}. {item['kode_saham']} ({item['nama_perusahaan']}) "
                f"| Skor: {item['skor_total']:.1f}/100 -> {item['rekomendasi']}"
            )
        parts.append("")

    # 2. Handle saham spesifik jika ada
    # Saring agar tidak memproses TOP_10_REKOMENDASI sebagai saham biasa
    saham_biasa = [s for s in saham_list if s != "TOP_10_REKOMENDASI"]
    if saham_biasa and data_angka:
        for kode in saham_biasa:
            data = data_angka.get(kode, {})
            if not data or "nama" not in data:
                continue
            nama = data.get("nama", kode)
            fund = data.get("fundamental", {})
            scoring = data.get("scoring", {})

            parts.append(f"📊 {kode} ({nama}):")

            if fund:
                harga = fund.get("harga")
                if harga:
                    parts.append(f"Harga terakhir: Rp {harga:,.0f}")
                roe = fund.get("roe")
                if roe:
                    parts.append(f"ROE: {roe}%")
                pbv = fund.get("pbv")
                if pbv:
                    parts.append(f"PBV: {pbv}x")

            if scoring:
                parts.append(
                    f"Skor: {scoring.get('skor_total', 'N/A')}/100 "
                    f"→ {scoring.get('rekomendasi', 'N/A')}"
                )
            parts.append("")

    elif not parts and dokumen:
        parts.append("Berdasarkan informasi yang tersedia:")
        for doc in dokumen[:3]:
            parts.append(f"- {doc.get('teks', '')[:150]}")
        parts.append("")

    elif not parts:
        parts.append(
            "Maaf, saya belum memiliki cukup data untuk menjawab "
            "pertanyaan ini secara akurat. Coba tanyakan dengan "
            "menyebutkan kode saham spesifik (contoh: BBCA, TLKM)."
        )

    # Tidak ada tambahan disclaimer di akhir jawaban karena sudah ada di bawah bubble
    pass

    return "\n".join(parts)


# ============================================================
# NODE 4: Cek Kualitas (Conditional)
# ============================================================

async def cek_kualitas(state: ChatState) -> dict[str, Any]:
    """
    Cek kualitas jawaban berdasarkan confidence score.

    Jika confidence < 0.5 dan belum pernah retry:
    - Set perlu_dokumen_tambahan = True
    - Akan di-route kembali ke ambil_konteks dengan top_k lebih besar

    Jika confidence >= 0.5 atau sudah retry:
    - Jawaban diterima apa adanya

    Returns:
        Update state: perlu_dokumen_tambahan
    """
    confidence = state.get("confidence", 0.5)
    retry_count = state.get("_retry_count", 0)
    jawaban = state.get("jawaban_draft", "")

    logger.info(
        f"🔍 NODE 4: Cek Kualitas "
        f"(confidence={confidence:.2f}, retry={retry_count})"
    )

    # Cek apakah jawaban terlalu pendek
    jawaban_terlalu_pendek = len(jawaban.strip()) < 30

    if (confidence < 0.5 or jawaban_terlalu_pendek) and retry_count < 1:
        logger.warning(
            f"   ⚠️  Kualitas kurang "
            f"(confidence={confidence:.2f}, len={len(jawaban)}), "
            f"retry dengan lebih banyak dokumen..."
        )
        return {
            "perlu_dokumen_tambahan": True,
            "_retry_count": retry_count + 1,
        }

    # Kualitas OK atau sudah retry — finalisasi jawaban
    if confidence < 0.5:
        logger.info(
            f"   ⚠️  Confidence masih rendah ({confidence:.2f}) "
            f"setelah retry, jawaban diterima apa adanya"
        )
    else:
        logger.info(f"   ✅ Kualitas OK (confidence={confidence:.2f})")

    return {
        "perlu_dokumen_tambahan": False,
        "jawaban_final": jawaban,
    }


def _route_setelah_cek_kualitas(state: ChatState) -> str:
    """
    Router setelah cek_kualitas.

    - perlu_dokumen_tambahan = True → kembali ke ambil_konteks (retry)
    - perlu_dokumen_tambahan = False → END
    """
    if state.get("perlu_dokumen_tambahan", False):
        return "retry"
    return "selesai"


# ============================================================
# LangGraph: Build & Compile StateGraph
# ============================================================

def build_chatbot_graph() -> Any:
    """
    Bangun dan compile LangGraph StateGraph untuk chatbot.

    Graph flow:
        START → klasifikasi_pertanyaan
        klasifikasi_pertanyaan → ambil_konteks (jika bukan ambigu)
        klasifikasi_pertanyaan → END (jika ambigu)
        ambil_konteks → generate_jawaban → cek_kualitas
        cek_kualitas → END (jika OK)
        cek_kualitas → ambil_konteks (jika retry)

    Returns:
        Compiled LangGraph yang siap di-invoke
    """
    logger.debug("🔧 Building chatbot graph...")

    graph = StateGraph(ChatState)

    # Register nodes
    graph.add_node("klasifikasi_pertanyaan", klasifikasi_pertanyaan)
    graph.add_node("ambil_konteks", ambil_konteks)
    graph.add_node("generate_jawaban", generate_jawaban)
    graph.add_node("cek_kualitas", cek_kualitas)

    # Edge: START → klasifikasi
    graph.add_edge(START, "klasifikasi_pertanyaan")

    # Conditional edge setelah klasifikasi
    graph.add_conditional_edges(
        "klasifikasi_pertanyaan",
        _route_setelah_klasifikasi,
        {
            "ambil_konteks": "ambil_konteks",
            "end": END,
        },
    )

    # Edge: ambil_konteks → generate_jawaban → cek_kualitas
    graph.add_edge("ambil_konteks", "generate_jawaban")
    graph.add_edge("generate_jawaban", "cek_kualitas")

    # Conditional edge setelah cek_kualitas
    graph.add_conditional_edges(
        "cek_kualitas",
        _route_setelah_cek_kualitas,
        {
            "selesai": END,
            "retry": "ambil_konteks",
        },
    )

    compiled = graph.compile()
    logger.debug("✅ Chatbot graph berhasil di-compile")

    return compiled


# ============================================================
# Singleton Graph Instance
# ============================================================

_chatbot_graph = None


def _get_chatbot_graph() -> Any:
    """
    Dapatkan singleton chatbot graph.

    Graph hanya di-compile sekali dan di-reuse untuk setiap request.
    """
    global _chatbot_graph
    if _chatbot_graph is None:
        _chatbot_graph = build_chatbot_graph()
    return _chatbot_graph


# ============================================================
# Entry Point: chat()
# ============================================================

async def chat(
    pertanyaan: str,
    riwayat: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Entry point utama untuk chatbot RAG.

    Menerima pertanyaan dalam Bahasa Indonesia tentang saham,
    mengambil konteks dari ChromaDB dan PostgreSQL, lalu menjawab
    menggunakan Qwen3 via Ollama.

    Args:
        pertanyaan: Pertanyaan user dalam Bahasa Indonesia
        riwayat: Riwayat percakapan sebelumnya (opsional)
                 Format: [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        Dict dengan field:
            - jawaban (str): Jawaban final untuk user
            - saham (list[str]): Kode saham yang dibahas
            - jenis (str): Jenis pertanyaan yang terdeteksi
            - confidence (float): Confidence score 0-1
            - sumber_data (int): Jumlah dokumen referensi yang digunakan

    Example:
        >>> result = await chat("Bagaimana kinerja BBCA kuartal ini?")
        >>> print(result["jawaban"])
        BBCA menunjukkan kinerja yang solid di kuartal ini...

        >>> print(result["confidence"])
        0.85

        >>> # Dengan riwayat
        >>> result = await chat(
        ...     "Bagaimana dibanding BMRI?",
        ...     riwayat=[
        ...         {"role": "user", "content": "Analisis BBCA"},
        ...         {"role": "assistant", "content": "BBCA memiliki ROE 21%..."},
        ...     ]
        ... )
    """
    if not pertanyaan or not pertanyaan.strip():
        return {
            "jawaban": "Silakan ajukan pertanyaan tentang saham Indonesia.",
            "saham": [],
            "jenis": "ambigu",
            "confidence": 1.0,
            "sumber_data": 0,
        }

    logger.info(f"💬 Chat: \"{pertanyaan[:100]}\"")

    graph = _get_chatbot_graph()

    # Siapkan initial state
    initial_state: ChatState = {
        "pertanyaan_original": pertanyaan.strip(),
        "jenis_pertanyaan": "",
        "saham_yang_ditanyakan": [],
        "dokumen_relevan": [],
        "data_angka": {},
        "jawaban_draft": "",
        "confidence": 0.0,
        "perlu_dokumen_tambahan": False,
        "jawaban_final": "",
        "riwayat": riwayat or [],
        "_retry_count": 0,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"❌ Chatbot pipeline gagal: {type(e).__name__}: {e}")
        return {
            "jawaban": (
                "Maaf, terjadi kesalahan saat memproses pertanyaan Anda. "
                "Silakan coba lagi dalam beberapa saat."
            ),
            "saham": [],
            "jenis": "error",
            "confidence": 0.0,
            "sumber_data": 0,
        }

    jawaban_final = (
        final_state.get("jawaban_final", "")
        or final_state.get("jawaban_draft", "")
        or "Maaf, saya tidak bisa menjawab pertanyaan ini saat ini."
    )

    result = {
        "jawaban": jawaban_final,
        "saham": final_state.get("saham_yang_ditanyakan", []),
        "jenis": final_state.get("jenis_pertanyaan", "umum"),
        "confidence": final_state.get("confidence", 0.5),
        "sumber_data": len(final_state.get("dokumen_relevan", [])),
    }

    logger.info(
        f"💬 Response: jenis={result['jenis']}, "
        f"saham={result['saham']}, "
        f"confidence={result['confidence']:.2f}, "
        f"sumber={result['sumber_data']}"
    )

    return result
