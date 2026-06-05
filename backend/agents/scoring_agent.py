"""
AI Saham Indonesia — LangGraph Scoring Agent

Komponen paling penting dalam sistem: agent yang setiap Senin pagi
menjalankan scoring adaptif terhadap semua saham IDX dan menghasilkan
rekomendasi top 10 saham beserta alasan dari LLM.

Arsitektur LangGraph StateGraph:
    ┌─────────────────────────────────┐
    │            START                │
    └───────────┬─────────────────────┘
                │
    ┌───────────▼─────────────────────┐
    │  1. analisis_kondisi_pasar      │
    │     - Baca data makro terbaru   │
    │     - Cek volatilitas           │
    │     - Tentukan bobot adaptif    │
    └───────────┬─────────────────────┘
                │
    ┌───────────▼─────────────────────┐
    │  2. hitung_skor                 │
    │     - Skor fundamental (0-100)  │
    │     - Skor sentimen (0-100)     │
    │     - Skor sektor (0-100)       │
    │     - Skor makro (0-100)        │
    │     - Skor risiko (0-100)       │
    │     - Weighted sum → total      │
    └───────────┬─────────────────────┘
                │
    ┌───────────▼─────────────────────┐
    │  3. self_check (conditional)    │
    │     - Validasi kelengkapan data │
    │     - Tandai data terbatas      │
    │     - Route: lanjut / retry     │
    └───────────┬─────────────────────┘
                │ (lanjut)
    ┌───────────▼─────────────────────┐
    │  4. generate_alasan             │
    │     - Ambil top 10 saham        │
    │     - Panggil Qwen via Ollama   │
    │     - Buat alasan 3-4 kalimat   │
    │     - Tentukan BUY/HOLD/SELL    │
    └───────────┬─────────────────────┘
                │
    ┌───────────▼─────────────────────┐
    │            END                  │
    └─────────────────────────────────┘

Penggunaan:
    from backend.agents.scoring_agent import jalankan_scoring

    # Entry point utama (dipanggil scheduler setiap Senin 06:00)
    hasil = await jalankan_scoring(["BBCA", "TLKM", "ASII", ...])

    for saham in hasil:
        print(f"{saham['kode_saham']}: {saham['skor_total']:.1f} → {saham['rekomendasi']}")
        print(f"  Alasan: {saham['alasan']}")
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from loguru import logger
from sqlalchemy import func, select

from backend.config import settings
from backend.db.postgres import (
    Berita,
    Fundamental,
    Makro,
    Rekomendasi,
    ScoringMingguan,
    async_session,
)
from backend.rag.retriever import retrieve_context_for_scoring

# Timezone WIB
_WIB = timezone(timedelta(hours=7))


# ============================================================
# State Definition
# ============================================================

class ScoringState(TypedDict):
    """
    State yang mengalir melalui LangGraph scoring pipeline.

    Setiap node membaca dan menulis ke state ini.
    LangGraph secara otomatis meng-merge update dari setiap node.
    """
    daftar_saham: list[str]       # Input: kode saham yang akan di-scoring
    kondisi_pasar: dict           # Node 1: hasil analisis kondisi minggu ini
    bobot: dict                   # Node 1: bobot adaptif yang dipilih agent
    skor_per_saham: list[dict]    # Node 2: hasil scoring semua saham
    perlu_retry: list[str]        # Node 3: saham yang perlu di-recheck
    hasil_final: list[dict]       # Node 4: top 10 final dengan alasan


# ============================================================
# LLM Setup
# ============================================================

def _get_llm() -> ChatOllama:
    """Buat instance ChatOllama yang terhubung ke Qwen3 lokal."""
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.ollama_temperature,
        num_ctx=settings.ollama_num_ctx,
        timeout=settings.ollama_timeout,
    )


# ============================================================
# NODE 1: Analisis Kondisi Pasar
# ============================================================

async def analisis_kondisi_pasar(state: ScoringState) -> dict[str, Any]:
    """
    Analisis kondisi pasar saat ini untuk menentukan bobot scoring adaptif.

    Langkah:
    1. Baca data makro terbaru dari PostgreSQL (BI rate, kurs, IHSG, inflasi)
    2. Cek volatilitas: kurs bergerak > 2% atau IHSG turun > 3% minggu ini
    3. Cek apakah ada laporan keuangan baru rilis (berita tentang lapkeu)
    4. Tentukan bobot scoring adaptif berdasarkan kondisi

    Aturan bobot adaptif:
    - Laporan keuangan baru → fundamental naik ke 40%
    - Volatilitas tinggi → makro naik ke 30%, risiko naik ke 15%
    - Normal → 30/25/20/15/10 (default)

    Returns:
        Update state: kondisi_pasar, bobot
    """
    logger.info("=" * 60)
    logger.info("🏦 NODE 1: Analisis Kondisi Pasar")
    logger.info("=" * 60)

    kondisi: dict[str, Any] = {
        "tanggal_analisis": date.today().isoformat(),
        "makro_terbaru": {},
        "ada_lapkeu_baru": False,
        "volatilitas_tinggi": False,
        "rupiah_melemah_tajam": False,
        "ihsg_turun_tajam": False,
        "catatan": [],
    }

    # ─── Langkah 1: Baca data makro terbaru ───
    try:
        async with async_session() as session:
            # Ambil data makro terbaru per indikator
            for indikator in ["bi_rate", "kurs_usd_idr", "ihsg", "inflasi_yoy"]:
                stmt = (
                    select(Makro)
                    .where(Makro.indikator == indikator)
                    .order_by(Makro.tanggal.desc())
                    .limit(2)  # Ambil 2 terakhir untuk hitung perubahan
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                if rows:
                    latest = rows[0]
                    kondisi["makro_terbaru"][indikator] = {
                        "nilai": latest.nilai,
                        "tanggal": latest.tanggal.isoformat(),
                        "satuan": latest.satuan,
                    }

                    # Hitung perubahan jika ada data sebelumnya
                    if len(rows) >= 2:
                        previous = rows[1]
                        if previous.nilai and previous.nilai != 0:
                            pct_change = (
                                (latest.nilai - previous.nilai)
                                / abs(previous.nilai) * 100
                            )
                            kondisi["makro_terbaru"][indikator]["perubahan_pct"] = (
                                round(pct_change, 2)
                            )

                    logger.info(
                        f"   📊 {indikator}: {latest.nilai} {latest.satuan} "
                        f"(per {latest.tanggal})"
                    )

    except Exception as e:
        logger.error(f"❌ Gagal baca data makro: {type(e).__name__}: {e}")
        kondisi["catatan"].append(f"Data makro tidak tersedia: {e}")

    # Hentikan seluruh pipeline jika data makro kosong sama sekali (Kasus 4)
    if not kondisi["makro_terbaru"]:
        msg = "Data makro kosong sama sekali di database! Seluruh proses scoring dihentikan."
        logger.critical(f"🚨 {msg}")
        import backend.system_notifier as notifier
        notifier.report_error(
            source="scoring_agent",
            message=msg,
            level="CRITICAL",
            auto_open_browser=True
        )
        raise RuntimeError(msg)

    # ─── Langkah 2: Cek volatilitas ───
    kurs_data = kondisi["makro_terbaru"].get("kurs_usd_idr", {})
    ihsg_data = kondisi["makro_terbaru"].get("ihsg", {})

    kurs_change = kurs_data.get("perubahan_pct", 0)
    ihsg_change = ihsg_data.get("perubahan_pct", 0)

    # Kurs naik > 2% = Rupiah melemah tajam
    if abs(kurs_change) > 2.0:
        kondisi["rupiah_melemah_tajam"] = kurs_change > 0
        kondisi["volatilitas_tinggi"] = True
        kondisi["catatan"].append(
            f"Kurs USD/IDR bergerak {kurs_change:+.2f}% — "
            f"{'Rupiah melemah' if kurs_change > 0 else 'Rupiah menguat'} tajam"
        )
        logger.warning(f"⚠️  Kurs bergerak {kurs_change:+.2f}%!")

    # IHSG turun > 3% = volatilitas tinggi
    if ihsg_change < -3.0:
        kondisi["ihsg_turun_tajam"] = True
        kondisi["volatilitas_tinggi"] = True
        kondisi["catatan"].append(f"IHSG turun {ihsg_change:.2f}% — pasar bearish")
        logger.warning(f"⚠️  IHSG turun {ihsg_change:.2f}%!")

    # ─── Langkah 3: Cek laporan keuangan baru ───
    try:
        async with async_session() as session:
            seminggu_lalu = date.today() - timedelta(days=7)
            stmt = (
                select(func.count(Berita.id))
                .where(
                    Berita.tanggal_publish >= datetime.combine(
                        seminggu_lalu, datetime.min.time(), tzinfo=_WIB
                    ),
                    Berita.judul.ilike("%laporan keuangan%")
                    | Berita.judul.ilike("%financial report%")
                    | Berita.judul.ilike("%laba bersih%")
                    | Berita.judul.ilike("%earnings%")
                    | Berita.judul.ilike("%kuartal%")
                    | Berita.judul.ilike("%quarterly%"),
                )
            )
            result = await session.execute(stmt)
            count = result.scalar() or 0

            if count >= 3:  # Minimal 3 berita terkait lapkeu
                kondisi["ada_lapkeu_baru"] = True
                kondisi["catatan"].append(
                    f"Ditemukan {count} berita terkait laporan keuangan minggu ini"
                )
                logger.info(f"📋 {count} berita laporan keuangan terdeteksi")

    except Exception as e:
        logger.error(f"❌ Gagal cek berita lapkeu: {type(e).__name__}: {e}")

    # ─── Langkah 4: Tentukan bobot adaptif ───
    if kondisi["ada_lapkeu_baru"]:
        # Musim laporan keuangan → fundamental dominan
        bobot = {
            "fundamental": 0.40,
            "sentimen": 0.20,
            "sektor": 0.15,
            "makro": 0.15,
            "risiko": 0.10,
        }
        kondisi["catatan"].append(
            "BOBOT: Fundamental dinaikkan ke 40% (musim laporan keuangan)"
        )
        logger.info("📊 Bobot ADAPTIF: Fundamental 40% (musim lapkeu)")

    elif kondisi["volatilitas_tinggi"]:
        # Pasar volatile → makro dan risiko lebih penting
        bobot = {
            "fundamental": 0.20,
            "sentimen": 0.20,
            "sektor": 0.15,
            "makro": 0.30,
            "risiko": 0.15,
        }
        kondisi["catatan"].append(
            "BOBOT: Makro/Risiko dinaikkan (pasar volatil)"
        )
        logger.info("📊 Bobot ADAPTIF: Makro 30%, Risiko 15% (volatil)")

    else:
        # Kondisi normal → bobot default
        bobot = {
            "fundamental": settings.score_weight_fundamental,
            "sentimen": settings.score_weight_sentimen,
            "sektor": settings.score_weight_sektor,
            "makro": settings.score_weight_makro,
            "risiko": settings.score_weight_risiko,
        }
        logger.info("📊 Bobot DEFAULT: 30/25/20/15/10")

    # Validasi total bobot = 1.0
    total_bobot = sum(bobot.values())
    if abs(total_bobot - 1.0) > 0.01:
        logger.error(f"❌ Total bobot = {total_bobot}, seharusnya 1.0!")
        # Normalisasi darurat
        bobot = {k: v / total_bobot for k, v in bobot.items()}

    logger.info(
        f"📊 Bobot final: "
        + " | ".join(f"{k}={v:.0%}" for k, v in bobot.items())
    )

    return {"kondisi_pasar": kondisi, "bobot": bobot}


# ============================================================
# NODE 2: Hitung Skor
# ============================================================

def _skor_fundamental(data: dict[str, Any]) -> float:
    """
    Hitung skor fundamental (0-100) berdasarkan rasio keuangan.

    Komponen penilaian:
    - ROE (25 poin): >20% = 25, >15% = 20, >10% = 15, >5% = 10, else 5
    - EPS (25 poin): >0 = proporsional, <0 = 0
    - PBV (25 poin): <1 = 25, <1.5 = 20, <2 = 15, <3 = 10, else 5
    - DER (25 poin): <0.5 = 25, <1 = 20, <1.5 = 15, <2 = 10, else 5

    Args:
        data: Dict dengan key roe, eps, pbv, der

    Returns:
        Skor 0-100
    """
    skor = 0.0
    komponen_tersedia = 0

    # ROE (Return on Equity) — semakin tinggi semakin baik
    roe = data.get("roe")
    if roe is not None:
        komponen_tersedia += 1
        if roe > 20:
            skor += 25
        elif roe > 15:
            skor += 20
        elif roe > 10:
            skor += 15
        elif roe > 5:
            skor += 10
        elif roe > 0:
            skor += 5

    # EPS (Earnings Per Share) — harus positif dan semakin tinggi semakin baik
    eps = data.get("eps")
    if eps is not None:
        komponen_tersedia += 1
        if eps > 500:
            skor += 25
        elif eps > 200:
            skor += 20
        elif eps > 100:
            skor += 15
        elif eps > 0:
            skor += 10
        # EPS negatif = 0 poin

    # PBV (Price to Book Value) — semakin rendah semakin murah (value play)
    pbv = data.get("pbv")
    if pbv is not None and pbv > 0:
        komponen_tersedia += 1
        if pbv < 1.0:
            skor += 25  # Saham undervalued
        elif pbv < 1.5:
            skor += 20
        elif pbv < 2.0:
            skor += 15
        elif pbv < 3.0:
            skor += 10
        else:
            skor += 5

    # DER (Debt to Equity Ratio) — semakin rendah semakin sehat
    der = data.get("der")
    if der is not None and der >= 0:
        komponen_tersedia += 1
        if der < 0.5:
            skor += 25  # Utang sangat rendah
        elif der < 1.0:
            skor += 20
        elif der < 1.5:
            skor += 15
        elif der < 2.0:
            skor += 10
        else:
            skor += 5

    # Jika tidak ada data, return skor netral
    if komponen_tersedia == 0:
        return 50.0  # Skor netral jika data tidak tersedia

    # Normalisasi ke 0-100 berdasarkan komponen yang tersedia
    max_skor = komponen_tersedia * 25
    return round((skor / max_skor) * 100, 2)


def _skor_sentimen(berita_sentimen: list[float]) -> float:
    """
    Hitung skor sentimen (0-100) dari rata-rata sentimen berita.

    Konversi dari range [-1, 1] ke [0, 100]:
    - Sentimen -1.0 → skor 0
    - Sentimen  0.0 → skor 50
    - Sentimen +1.0 → skor 100

    Args:
        berita_sentimen: List skor sentimen berita [-1, 1]

    Returns:
        Skor 0-100
    """
    if not berita_sentimen:
        return 50.0  # Netral jika tidak ada berita

    rata_rata = sum(berita_sentimen) / len(berita_sentimen)
    # Konversi [-1, 1] → [0, 100]
    skor = (rata_rata + 1.0) / 2.0 * 100
    return round(max(0.0, min(100.0, skor)), 2)


def _skor_sektor(
    sektor_saham: str,
    kinerja_sektoral: dict[str, float],
    perubahan_ihsg: float,
) -> float:
    """
    Hitung skor sektor (0-100) berdasarkan performa relatif terhadap IHSG.

    Jika sektor outperform IHSG → skor tinggi
    Jika sektor underperform IHSG → skor rendah

    Args:
        sektor_saham: Nama sektor saham
        kinerja_sektoral: Dict mapping sektor → perubahan mingguan (%)
        perubahan_ihsg: Perubahan IHSG mingguan (%)

    Returns:
        Skor 0-100
    """
    kinerja_sektor = kinerja_sektoral.get(sektor_saham.lower(), 0)

    # Selisih performa sektor vs IHSG
    selisih = kinerja_sektor - perubahan_ihsg

    # Konversi selisih ke skor: +5% outperform = 100, -5% underperform = 0
    # Linear scaling di range [-5%, +5%]
    skor = 50.0 + (selisih / 5.0) * 50.0
    return round(max(0.0, min(100.0, skor)), 2)


def _skor_makro(kondisi_pasar: dict[str, Any], sektor: str) -> float:
    """
    Hitung skor makro (0-100) berdasarkan kondisi ekonomi.

    Faktor yang dipertimbangkan:
    - BI rate rendah → positif untuk saham (terutama properti, bank)
    - Inflasi terkendali → positif
    - Rupiah stabil/menguat → positif
    - IHSG trending naik → positif

    Args:
        kondisi_pasar: Dict kondisi pasar dari Node 1
        sektor: Sektor saham (untuk konteks)

    Returns:
        Skor 0-100
    """
    skor = 50.0  # Mulai dari netral
    makro = kondisi_pasar.get("makro_terbaru", {})

    # BI Rate — suku bunga rendah = positif untuk saham
    bi_rate_data = makro.get("bi_rate", {})
    bi_rate = bi_rate_data.get("nilai", 6.0)
    if bi_rate <= 5.0:
        skor += 15  # Suku bunga sangat rendah
    elif bi_rate <= 6.0:
        skor += 10
    elif bi_rate <= 7.0:
        skor += 5
    elif bi_rate > 7.5:
        skor -= 10  # Suku bunga tinggi = tekanan

    # Inflasi — inflasi terkendali (2-4%) = positif
    inflasi_data = makro.get("inflasi_yoy", {})
    inflasi = inflasi_data.get("nilai", 3.0)
    if 2.0 <= inflasi <= 4.0:
        skor += 10  # Inflasi ideal
    elif inflasi < 2.0:
        skor += 5   # Deflasi ringan
    elif inflasi > 7.0:
        skor -= 20  # Inflasi sangat tinggi
    elif inflasi > 5.0:
        skor -= 10  # Inflasi tinggi

    # Kurs — Rupiah melemah tajam = negatif
    kurs_data = makro.get("kurs_usd_idr", {})
    kurs_change = kurs_data.get("perubahan_pct", 0)
    if kurs_change > 2.0:
        skor -= 15  # Rupiah melemah tajam
    elif kurs_change > 1.0:
        skor -= 5
    elif kurs_change < -1.0:
        skor += 5   # Rupiah menguat

    # IHSG — tren naik = positif
    ihsg_data = makro.get("ihsg", {})
    ihsg_change = ihsg_data.get("perubahan_pct", 0)
    if ihsg_change > 2.0:
        skor += 10
    elif ihsg_change > 0:
        skor += 5
    elif ihsg_change < -3.0:
        skor -= 15

    # Bonus/penalti berdasarkan sektor terhadap kondisi makro
    sektor_lower = sektor.lower() if sektor else ""
    if "bank" in sektor_lower or "financ" in sektor_lower:
        # Bank sensitif terhadap suku bunga
        if bi_rate <= 5.5:
            skor += 5  # NIM bank bisa tertekan tapi kredit tumbuh
    elif "property" in sektor_lower or "properti" in sektor_lower:
        # Properti sangat sensitif terhadap suku bunga
        if bi_rate <= 5.5:
            skor += 10
        elif bi_rate > 7.0:
            skor -= 10

    return round(max(0.0, min(100.0, skor)), 2)


def _skor_risiko(
    data_fundamental: dict[str, Any],
    volume: int | None,
    ada_berita_negatif_besar: bool,
) -> float:
    """
    Hitung skor risiko (0-100). Skor tinggi = risiko RENDAH (aman).

    Faktor risiko:
    - DER > 2.0 → risiko tinggi (utang besar)
    - Volume rendah → risiko likuiditas
    - Ada berita negatif besar → risiko reputasi

    Args:
        data_fundamental: Dict data fundamental
        volume: Volume transaksi harian
        ada_berita_negatif_besar: Flag berita negatif signifikan

    Returns:
        Skor 0-100 (tinggi = AMAN, rendah = BERISIKO)
    """
    skor = 80.0  # Mulai dari asumsi risiko rendah

    # DER tinggi = utang besar = risiko tinggi
    der = data_fundamental.get("der")
    if der is not None:
        if der > 3.0:
            skor -= 30  # Utang sangat tinggi
        elif der > 2.0:
            skor -= 20
        elif der > 1.5:
            skor -= 10

    # Volume rendah = susah jual saat butuh (risiko likuiditas)
    if volume is not None:
        if volume < 100_000:
            skor -= 20  # Sangat tidak likuid
        elif volume < 500_000:
            skor -= 10

    # Berita negatif besar (skandal, gagal bayar, dll)
    if ada_berita_negatif_besar:
        skor -= 25

    return round(max(0.0, min(100.0, skor)), 2)


async def scrape_and_index_news_for_emiten(kode: str) -> None:
    """
    Melakukan scraping berita terupdate untuk emiten tertentu secara real-time,
    menganalisis sentimennya dengan LLM (Qwen), menyimpannya ke database (PostgreSQL),
    dan meng-index-nya ke ChromaDB (RAG).
    
    Dirancang untuk berjalan di background agar tidak memblock proses scoring utama.
    """
    logger.info(f"🔍 [On-Demand Scraping] Memulai pencarian berita segar untuk {kode}...")
    try:
        from backend.data.collectors.berita_collector import collect_berita
        from backend.data.preprocessors.data_cleaner import clean_berita, hitung_sentimen_qwen
        from backend.rag.indexer import index_batch_berita
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # 1. Scraping berita (hari_terakhir=7 untuk cakupan mingguan)
        raw_berita = await collect_berita(kode, hari_terakhir=7)
        if not raw_berita:
            logger.warning(f"⚠️ [On-Demand Scraping] Tidak menemukan berita baru untuk {kode} di internet.")
            return

        logger.info(f"📰 [On-Demand Scraping] Ditemukan {len(raw_berita)} berita mentah untuk {kode}. Memproses...")

        saved_berita_list = []
        async with async_session() as session:
            for item in raw_berita:
                try:
                    cleaned = clean_berita(item)
                    sentimen_text = cleaned.get("isi_berita") or cleaned["judul"]
                    # Hitung sentimen
                    cleaned["skor_sentimen"] = await hitung_sentimen_qwen(sentimen_text)

                    # Upsert to PostgreSQL
                    stmt = pg_insert(Berita).values(
                        kode_saham=cleaned["kode_saham"],
                        judul=cleaned["judul"],
                        url=cleaned["url"],
                        sumber=cleaned["sumber"],
                        tanggal_publish=cleaned["tanggal_publish"],
                        skor_sentimen=cleaned["skor_sentimen"],
                        isi_berita=cleaned.get("isi_berita"),
                        sudah_diembedding=False
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
                    res = await session.execute(stmt)
                    if res.rowcount > 0:
                        saved_berita_list.append(cleaned)
                except Exception as e:
                    logger.error(f"❌ [On-Demand Scraping] Gagal memproses berita '{item.get('judul', '')[:30]}': {e}")
            await session.commit()

        if saved_berita_list:
            logger.info(f"💾 [On-Demand Scraping] {len(saved_berita_list)} berita baru disimpan ke PostgreSQL. Melakukan embedding...")
            # Ambil berita yang baru disimpan untuk di-embed
            async with async_session() as session:
                stmt = select(Berita).where(
                    Berita.kode_saham == kode,
                    Berita.sudah_diembedding == False
                )
                res = await session.execute(stmt)
                unembedded = res.scalars().all()

                if unembedded:
                    berita_dict_list = []
                    for n in unembedded:
                        berita_dict_list.append({
                            "id": n.id,
                            "kode_saham": n.kode_saham,
                            "judul": n.judul,
                            "url": n.url,
                            "sumber": n.sumber,
                            "tanggal_publish": n.tanggal_publish,
                            "isi_berita": n.isi_berita,
                        })
                    stats = await index_batch_berita(berita_dict_list)
                    if stats["berhasil"] > 0:
                        success_urls = [n["url"] for n in berita_dict_list]
                        for n in unembedded:
                            if n.url in success_urls:
                                n.sudah_diembedding = True
                        await session.commit()
                        logger.info(f"✅ [On-Demand Scraping] Embedding selesai: {stats['berhasil']} berita ter-index ke ChromaDB.")
        
        logger.info(f"✅ [On-Demand Scraping] Selesai mengambil berita untuk {kode}.")

    except Exception as e:
        logger.error(f"❌ [On-Demand Scraping] Gagal menjalankan real-time scraping berita untuk {kode}: {e}")


async def scrape_and_save_fundamental_for_emiten(kode: str) -> dict[str, Any] | None:
    """
    Melakukan scraping data fundamental secara real-time untuk emiten tertentu
    dari Yahoo Finance + XBRL IDX, lalu menyimpannya ke database PostgreSQL.
    """
    logger.info(f"🔍 [On-Demand Fundamental] Mengambil data fundamental baru untuk {kode}...")
    try:
        from backend.data.collectors.fundamental_collector import collect_fundamental
        from backend.data.collectors.xbrl_collector import collect_xbrl_fundamental
        from backend.data.preprocessors.data_cleaner import normalize_fundamental
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # 1. Fetch dari Yahoo Finance
        raw_list = await collect_fundamental([kode])
        if not raw_list:
            logger.warning(f"⚠️ [On-Demand Fundamental] Yahoo Finance tidak mengembalikan data untuk {kode}")
            return None
        
        item = raw_list[0]

        # 2. Fetch dari XBRL IDX
        try:
            xbrl_data = await collect_xbrl_fundamental(kode)
            if xbrl_data:
                item["roe"] = xbrl_data.get("roe")
                item["eps"] = xbrl_data.get("eps")
                item["der"] = xbrl_data.get("der")
                
                harga = item.get("harga_terakhir")
                if harga is not None and item["eps"] and item["eps"] != 0:
                    item["pe_ratio"] = round(harga / item["eps"], 2)
                    if item["roe"] is not None:
                        item["pbv"] = round(item["pe_ratio"] * (item["roe"] / 100.0), 2)
        except Exception as ex:
            logger.warning(f"⚠️ [On-Demand Fundamental] Gagal mengambil XBRL untuk {kode}: {ex}")

        # 3. Normalisasi
        cleaned = normalize_fundamental(item)

        # 4. Simpan ke database
        async with async_session() as session:
            stmt = pg_insert(Fundamental).values(
                kode_saham=cleaned["kode_saham"],
                tanggal=cleaned["tanggal"],
                harga_terakhir=cleaned["harga_terakhir"],
                volume=cleaned["volume"],
                roe=cleaned["roe"],
                eps=cleaned["eps"],
                pbv=cleaned["pbv"],
                der=cleaned["der"],
                market_cap=cleaned["market_cap"],
                pe_ratio=cleaned["pe_ratio"],
                dividend_yield=cleaned["dividend_yield"]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["kode_saham", "tanggal"],
                set_={
                    "harga_terakhir": stmt.excluded.harga_terakhir,
                    "volume": stmt.excluded.volume,
                    "roe": stmt.excluded.roe,
                    "eps": stmt.excluded.eps,
                    "pbv": stmt.excluded.pbv,
                    "der": stmt.excluded.der,
                    "market_cap": stmt.excluded.market_cap,
                    "pe_ratio": stmt.excluded.pe_ratio,
                    "dividend_yield": stmt.excluded.dividend_yield,
                }
            )
            await session.execute(stmt)
            await session.commit()

        logger.info(f"✅ [On-Demand Fundamental] Berhasil memperbarui data fundamental untuk {kode}")
        return cleaned

    except Exception as e:
        logger.error(f"❌ [On-Demand Fundamental] Gagal mengambil data untuk {kode}: {e}")
        return None


async def hitung_skor(state: ScoringState) -> dict[str, Any]:
    """
    Hitung skor per komponen untuk setiap saham dan kalkulasi skor total.

    Untuk setiap saham:
    1. Ambil data fundamental terbaru dari PostgreSQL
    2. Ambil sentimen berita 7 hari terakhir
    3. Hitung skor per 5 komponen (0-100 masing-masing)
    4. Kalkulasi skor total = weighted sum dengan bobot dari Node 1

    Returns:
        Update state: skor_per_saham
    """
    logger.info("=" * 60)
    logger.info("📊 NODE 2: Hitung Skor")
    logger.info("=" * 60)

    bobot = state["bobot"]
    kondisi_pasar = state["kondisi_pasar"]
    daftar_saham = state["daftar_saham"]
    skor_per_saham: list[dict[str, Any]] = []

    # Ambil perubahan IHSG untuk perhitungan sektor
    ihsg_data = kondisi_pasar.get("makro_terbaru", {}).get("ihsg", {})
    perubahan_ihsg = ihsg_data.get("perubahan_pct", 0)

    # Kinerja sektoral placeholder (di versi berikutnya, ambil dari data riil)
    # Untuk sekarang, semua sektor dianggap perform sama dengan IHSG
    kinerja_sektoral: dict[str, float] = {}

    seminggu_lalu = date.today() - timedelta(days=7)

    for kode in daftar_saham:
        logger.info(f"   📈 Scoring {kode}...")

        try:
            data_fundamental: dict[str, Any] = {}
            volume: int | None = None
            sektor: str = ""
            berita_sentimen: list[float] = []
            ada_berita_negatif_besar = False

            async with async_session() as session:
                # ─── Ambil data fundamental terbaru ───
                stmt_fund = (
                    select(Fundamental)
                    .where(Fundamental.kode_saham == kode)
                    .order_by(Fundamental.tanggal.desc())
                    .limit(1)
                )
                result = await session.execute(stmt_fund)
                fund = result.scalar_one_or_none()

                if fund:
                    data_fundamental = {
                        "roe": fund.roe,
                        "eps": fund.eps,
                        "pbv": fund.pbv,
                        "der": fund.der,
                        "pe_ratio": fund.pe_ratio,
                        "dividend_yield": fund.dividend_yield,
                        "harga": fund.harga_terakhir,
                        "market_cap": fund.market_cap,
                    }
                    volume = fund.volume

                # ─── Ambil info sektor saham ───
                from backend.db.postgres import Saham

                stmt_saham = select(Saham).where(Saham.kode == kode)
                result = await session.execute(stmt_saham)
                saham_obj = result.scalar_one_or_none()
                if saham_obj:
                    sektor = saham_obj.sektor or ""

                # ─── Ambil sentimen berita 7 hari terakhir ───
                stmt_berita = (
                    select(Berita.skor_sentimen)
                    .where(
                        Berita.kode_saham == kode,
                        Berita.skor_sentimen.isnot(None),
                        Berita.tanggal_publish >= datetime.combine(
                            seminggu_lalu, datetime.min.time(), tzinfo=_WIB
                        ),
                    )
                )
                result = await session.execute(stmt_berita)
                sentimen_rows = result.scalars().all()
                berita_sentimen = [float(s) for s in sentimen_rows if s is not None]

                # Cek apakah ada berita sangat negatif (skor < -0.7)
                if any(s < -0.7 for s in berita_sentimen):
                    ada_berita_negatif_besar = True

            # ─── Validasi data fundamental kosong (Kasus 4) ───
            if not data_fundamental or (
                data_fundamental.get("roe") is None
                and data_fundamental.get("pbv") is None
                and data_fundamental.get("der") is None
                and data_fundamental.get("eps") is None
            ):
                msg_fund = f"Data fundamental untuk emiten {kode} kosong di database. Mencoba mengambil secara real-time..."
                logger.warning(f"⚠️ {msg_fund}")
                import backend.system_notifier as notifier
                notifier.report_error(
                    source="scoring_agent",
                    message=msg_fund,
                    level="ERROR",
                    auto_open_browser=False
                )

                # Ambil secara real-time
                cleaned_fund = await scrape_and_save_fundamental_for_emiten(kode)
                
                if cleaned_fund and (
                    cleaned_fund.get("roe") is not None
                    or cleaned_fund.get("pbv") is not None
                    or cleaned_fund.get("der") is not None
                    or cleaned_fund.get("eps") is not None
                ):
                    data_fundamental = cleaned_fund
                    volume = cleaned_fund.get("volume")
                    logger.info(f"✅ Berhasil memulihkan data fundamental {kode} secara real-time.")
                else:
                    msg_fail = f"Gagal mengambil data fundamental {kode} secara real-time. Menggunakan nilai netral agar emiten tidak terdelist."
                    logger.error(f"❌ {msg_fail}")
                    notifier.report_error(
                        source="scoring_agent",
                        message=msg_fail,
                        level="ERROR",
                        auto_open_browser=False
                    )
                    data_fundamental = {
                        "roe": None,
                        "eps": None,
                        "pbv": None,
                        "der": None,
                        "pe_ratio": None,
                        "dividend_yield": None,
                        "harga": None,
                        "market_cap": None
                    }

            # ─── Cek berita kosong dan picu on-demand scraping (Kasus 4) ───
            if not berita_sentimen:
                msg_news = f"Berita untuk emiten {kode} kosong di database. Memicu pencarian berita di latar belakang..."
                logger.warning(f"⚠️ {msg_news}")
                import backend.system_notifier as notifier
                notifier.report_error(
                    source="scoring_agent",
                    message=msg_news,
                    level="ERROR",
                    auto_open_browser=False
                )
                asyncio.create_task(scrape_and_index_news_for_emiten(kode))

            # ─── Hitung skor per komponen ───
            s_fundamental = _skor_fundamental(data_fundamental)
            s_sentimen = _skor_sentimen(berita_sentimen)
            s_sektor = _skor_sektor(sektor, kinerja_sektoral, perubahan_ihsg)
            s_makro = _skor_makro(kondisi_pasar, sektor)
            s_risiko = _skor_risiko(data_fundamental, volume, ada_berita_negatif_besar)

            # ─── Skor total: weighted sum ───
            skor_total = (
                s_fundamental * bobot["fundamental"]
                + s_sentimen * bobot["sentimen"]
                + s_sektor * bobot["sektor"]
                + s_makro * bobot["makro"]
                + s_risiko * bobot["risiko"]
            )

            # ─── Tentukan confidence ───
            # Confidence berdasarkan kelengkapan data
            data_points = sum(1 for v in data_fundamental.values() if v is not None)
            confidence_data = min(data_points / 6.0, 1.0)  # 6 rasio utama
            confidence_berita = min(len(berita_sentimen) / 5.0, 1.0)  # Ideal: 5 berita
            confidence = round((confidence_data * 0.6 + confidence_berita * 0.4), 2)

            hasil_saham = {
                "kode_saham": kode,
                "tanggal_scoring": date.today().isoformat(),
                "skor_total": round(skor_total, 2),
                "skor_fundamental": s_fundamental,
                "skor_sentimen": s_sentimen,
                "skor_sektor": s_sektor,
                "skor_makro": s_makro,
                "skor_risiko": s_risiko,
                "bobot_fundamental": bobot["fundamental"],
                "bobot_sentimen": bobot["sentimen"],
                "bobot_sektor": bobot["sektor"],
                "bobot_makro": bobot["makro"],
                "bobot_risiko": bobot["risiko"],
                "confidence": confidence,
                "sektor": sektor,
                "data_fundamental": data_fundamental,
                "jumlah_berita": len(berita_sentimen),
                "ada_berita_negatif_besar": ada_berita_negatif_besar,
            }

            skor_per_saham.append(hasil_saham)

            logger.info(
                f"   ✅ {kode}: Total={skor_total:.1f} "
                f"(F={s_fundamental:.0f} S={s_sentimen:.0f} "
                f"K={s_sektor:.0f} M={s_makro:.0f} R={s_risiko:.0f}) "
                f"conf={confidence:.2f}"
            )

        except Exception as e:
            logger.critical(f"🚨 CRITICAL: Gagal melakukan scoring untuk emiten {kode}. Seluruh proses dihentikan! Error: {e}")
            raise RuntimeError(f"Gagal melakukan scoring untuk emiten {kode}: {e}")

    # Sort berdasarkan skor total (descending)
    skor_per_saham.sort(key=lambda x: x["skor_total"], reverse=True)

    logger.info(f"📊 Scoring selesai: {len(skor_per_saham)} saham diproses")

    return {"skor_per_saham": skor_per_saham}


# ============================================================
# NODE 3: Self-Check (Conditional)
# ============================================================

async def self_check(state: ScoringState) -> dict[str, Any]:
    """
    Validasi kelengkapan data scoring dan tandai saham yang datanya terbatas.

    Kriteria data lengkap:
    - Data fundamental tersedia (minimal ROE, PBV)
    - Ada minimal 2 berita dengan sentimen

    Saham dengan data kurang lengkap diberi flag "data_terbatas"
    tapi tetap disertakan dalam hasil (dengan catatan).

    Returns:
        Update state: perlu_retry, skor_per_saham (dengan flag)
    """
    logger.info("=" * 60)
    logger.info("🔍 NODE 3: Self-Check Kelengkapan Data")
    logger.info("=" * 60)

    skor_per_saham = state["skor_per_saham"]
    perlu_retry: list[str] = []

    for saham in skor_per_saham:
        kode = saham["kode_saham"]
        masalah: list[str] = []

        # Cek kelengkapan fundamental
        data_fund = saham.get("data_fundamental", {})
        if data_fund.get("roe") is None and data_fund.get("pbv") is None:
            masalah.append("data fundamental tidak tersedia")

        # Cek jumlah berita
        if saham.get("jumlah_berita", 0) < 2:
            masalah.append(f"berita kurang (hanya {saham.get('jumlah_berita', 0)})")

        # Cek confidence
        if saham.get("confidence", 0) < 0.3:
            masalah.append(f"confidence rendah ({saham.get('confidence', 0):.2f})")

        if masalah:
            saham["data_terbatas"] = True
            saham["catatan_data"] = "; ".join(masalah)
            perlu_retry.append(kode)
            logger.warning(f"   ⚠️  {kode}: {saham['catatan_data']}")
        else:
            saham["data_terbatas"] = False
            saham["catatan_data"] = ""
            logger.info(f"   ✅ {kode}: data lengkap")

    logger.info(
        f"🔍 Self-check selesai: "
        f"{len(skor_per_saham) - len(perlu_retry)} lengkap, "
        f"{len(perlu_retry)} data terbatas"
    )

    return {"skor_per_saham": skor_per_saham, "perlu_retry": perlu_retry}


def _route_setelah_self_check(state: ScoringState) -> str:
    """
    Routing function setelah self_check.

    Saat ini selalu mengarahkan ke generate_alasan (v1).
    Di versi berikutnya, bisa mengarahkan ke retry/re-collect
    jika data terlalu banyak yang kurang.

    Returns:
        "generate_alasan" untuk lanjut, "hitung_skor" untuk retry
    """
    perlu_retry = state.get("perlu_retry", [])
    total = len(state.get("skor_per_saham", []))

    # V1: Selalu lanjut ke generate_alasan
    # V2 (future): retry jika > 50% saham datanya kurang
    if len(perlu_retry) > total * 0.5 and total > 0:
        logger.warning(
            f"⚠️  {len(perlu_retry)}/{total} saham data terbatas, "
            f"tapi tetap lanjut (v1 — tanpa retry)"
        )

    return "generate_alasan"


# ============================================================
# NODE 4: Generate Alasan
# ============================================================

async def generate_alasan(state: ScoringState) -> dict[str, Any]:
    """
    Generate alasan dan rekomendasi untuk top 10 saham menggunakan LLM.

    Untuk setiap saham di top 10:
    1. Ambil konteks dari ChromaDB (berita, laporan, makro)
    2. Kirim prompt ke Qwen3 via Ollama
    3. Parse response: alasan (3-4 kalimat) + rekomendasi (BUY/HOLD/SELL)

    Returns:
        Update state: hasil_final
    """
    logger.info("=" * 60)
    logger.info("🤖 NODE 4: Generate Alasan (Qwen3 via Ollama)")
    logger.info("=" * 60)

    skor_per_saham = state["skor_per_saham"]
    top_k = settings.top_k_saham  # Default: 10

    # Menyaring emiten dengan data_terbatas == True dari Top K rekomendasi utama (Kasus 4)
    kandidat_rekomendasi = [s for s in skor_per_saham if not s.get("data_terbatas")]
    
    # Fallback jika emiten dengan data lengkap sangat sedikit, kita campur agar rekomendasi tetap ada
    if len(kandidat_rekomendasi) < top_k:
        logger.warning(
            f"⚠️ Hanya ada {len(kandidat_rekomendasi)} saham dengan data lengkap. "
            f"Menyertakan saham dengan data terbatas sebagai fallback."
        )
        saham_terbatas = [s for s in skor_per_saham if s.get("data_terbatas")]
        kandidat_rekomendasi.extend(saham_terbatas)

    # Ambil top K saham dari hasil filter
    top_saham = kandidat_rekomendasi[:top_k]
    hasil_final: list[dict[str, Any]] = []

    # Siapkan LLM
    try:
        llm = _get_llm()
    except Exception as e:
        logger.error(f"❌ Gagal inisialisasi LLM: {e}")
        # Fallback: gunakan alasan template tanpa LLM
        for saham in top_saham:
            saham["alasan"] = _generate_alasan_fallback(saham)
            saham["rekomendasi"] = _tentukan_rekomendasi(saham["skor_total"])
            hasil_final.append(saham)
        return {"hasil_final": hasil_final}

    for i, saham in enumerate(top_saham, 1):
        kode = saham["kode_saham"]
        logger.info(f"   🤖 [{i}/{len(top_saham)}] Generating alasan untuk {kode}...")

        try:
            # Ambil konteks dari ChromaDB
            try:
                context = await retrieve_context_for_scoring(kode)
                konteks_berita = "\n".join(
                    [f"- {d['teks'][:200]}" for d in context.get("berita", [])[:3]]
                ) or "Tidak ada berita terkini."

                konteks_laporan = "\n".join(
                    [f"- {d['teks'][:200]}" for d in context.get("laporan_keuangan", [])[:2]]
                ) or "Tidak ada data laporan keuangan."
            except Exception:
                konteks_berita = "Tidak ada berita terkini."
                konteks_laporan = "Tidak ada data laporan keuangan."

            # Bangun prompt
            data_fund = saham.get("data_fundamental", {})
            catatan_data = (
                f"\n⚠️ Catatan: {saham['catatan_data']}"
                if saham.get("data_terbatas") else ""
            )

            prompt = f"""Kamu adalah analis saham Indonesia profesional. Berikan analisis singkat untuk saham berikut.

SAHAM: {kode}
SEKTOR: {saham.get('sektor', 'N/A')}
SKOR TOTAL: {saham['skor_total']:.1f}/100

SKOR PER KOMPONEN:
- Fundamental: {saham['skor_fundamental']:.1f}/100
- Sentimen: {saham['skor_sentimen']:.1f}/100
- Sektor: {saham['skor_sektor']:.1f}/100
- Makro: {saham['skor_makro']:.1f}/100
- Risiko: {saham['skor_risiko']:.1f}/100

DATA FUNDAMENTAL:
- ROE: {data_fund.get('roe', 'N/A')}%
- EPS: Rp {data_fund.get('eps', 'N/A')}
- PBV: {data_fund.get('pbv', 'N/A')}x
- DER: {data_fund.get('der', 'N/A')}x
- PE Ratio: {data_fund.get('pe_ratio', 'N/A')}x
- Harga: Rp {data_fund.get('harga', 'N/A')}
{catatan_data}

BERITA TERKINI:
{konteks_berita}

LAPORAN KEUANGAN:
{konteks_laporan}

INSTRUKSI:
1. Jelaskan dalam 3-4 kalimat mengapa saham {kode} mendapat skor {saham['skor_total']:.1f}/100 minggu ini
2. Sebutkan faktor positif utama dan risiko utama
3. Gunakan Bahasa Indonesia yang natural dan mudah dipahami
4. Akhiri dengan rekomendasi: BUY, HOLD, atau SELL
5. JANGAN gunakan format markdown, tulis dalam paragraf biasa

Format jawaban:
[ANALISIS]
(tulis analisis 3-4 kalimat di sini)

[REKOMENDASI]
(tulis BUY, HOLD, atau SELL)"""

            # Panggil LLM
            messages = [
                SystemMessage(content=(
                    "Kamu adalah analis saham senior yang memberikan analisis "
                    "ringkas dan akurat dalam Bahasa Indonesia. Jawab langsung "
                    "tanpa basa-basi. /no_think"
                )),
                HumanMessage(content=prompt),
            ]

            response = await llm.ainvoke(messages)
            response_text = response.content.strip()

            # Parse response
            alasan, rekomendasi = _parse_llm_response(
                response_text, saham["skor_total"]
            )

            saham["alasan"] = alasan
            saham["rekomendasi"] = rekomendasi

            logger.info(
                f"   ✅ {kode}: {rekomendasi} — "
                f"{alasan[:80]}..."
            )

        except Exception as e:
            logger.error(
                f"   ❌ Gagal generate alasan untuk {kode}: "
                f"{type(e).__name__}: {e}"
            )
            saham["alasan"] = _generate_alasan_fallback(saham)
            saham["rekomendasi"] = _tentukan_rekomendasi(saham["skor_total"])

        hasil_final.append(saham)

        # Delay kecil antar request LLM agar tidak overload Ollama
        if i < len(top_saham):
            await asyncio.sleep(1.0)

    logger.info(f"🤖 Alasan selesai: {len(hasil_final)} saham")

    return {"hasil_final": hasil_final}


def _parse_llm_response(
    response: str,
    skor_total: float,
) -> tuple[str, str]:
    """
    Parse response LLM menjadi alasan dan rekomendasi.

    Args:
        response: Response mentah dari LLM
        skor_total: Skor total saham (fallback untuk rekomendasi)

    Returns:
        Tuple (alasan, rekomendasi)
    """
    alasan = response
    rekomendasi = _tentukan_rekomendasi(skor_total)  # Default

    # Coba parse format [ANALISIS] dan [REKOMENDASI]
    if "[ANALISIS]" in response:
        parts = response.split("[ANALISIS]")
        if len(parts) > 1:
            analisis_part = parts[1]
            if "[REKOMENDASI]" in analisis_part:
                sub_parts = analisis_part.split("[REKOMENDASI]")
                alasan = sub_parts[0].strip()
                rekom_text = sub_parts[1].strip().upper()
            else:
                alasan = analisis_part.strip()
                rekom_text = ""

            # Parse rekomendasi
            if "BUY" in rekom_text or "BELI" in rekom_text:
                rekomendasi = "BUY"
            elif "SELL" in rekom_text or "JUAL" in rekom_text:
                rekomendasi = "SELL"
            elif "HOLD" in rekom_text or "TAHAN" in rekom_text:
                rekomendasi = "HOLD"

    elif "BUY" in response.upper()[-50:]:
        rekomendasi = "BUY"
    elif "SELL" in response.upper()[-50:]:
        rekomendasi = "SELL"
    elif "HOLD" in response.upper()[-50:]:
        rekomendasi = "HOLD"

    # Bersihkan alasan
    alasan = alasan.strip()
    if not alasan:
        alasan = "Analisis tidak tersedia."

    # Batasi panjang alasan
    if len(alasan) > 1000:
        alasan = alasan[:997] + "..."

    return alasan, rekomendasi


def _tentukan_rekomendasi(skor_total: float) -> str:
    """
    Tentukan rekomendasi berdasarkan skor total (fallback tanpa LLM).

    - Skor >= 70 → BUY
    - Skor 40-69 → HOLD
    - Skor < 40  → SELL
    """
    if skor_total >= 70:
        return "BUY"
    elif skor_total >= 40:
        return "HOLD"
    else:
        return "SELL"


def _generate_alasan_fallback(saham: dict[str, Any]) -> str:
    """
    Generate alasan template tanpa LLM (fallback jika Ollama tidak tersedia).

    Args:
        saham: Dict hasil scoring satu saham

    Returns:
        Alasan template dalam Bahasa Indonesia
    """
    kode = saham["kode_saham"]
    skor = saham["skor_total"]
    s_fund = saham["skor_fundamental"]
    s_sent = saham["skor_sentimen"]
    s_risk = saham["skor_risiko"]

    parts = []

    # Kalimat 1: overview skor
    if skor >= 70:
        parts.append(
            f"Saham {kode} mendapat skor {skor:.1f}/100, "
            f"menunjukkan prospek yang menarik minggu ini."
        )
    elif skor >= 50:
        parts.append(
            f"Saham {kode} mendapat skor {skor:.1f}/100, "
            f"menunjukkan kondisi yang cukup stabil."
        )
    else:
        parts.append(
            f"Saham {kode} mendapat skor {skor:.1f}/100, "
            f"mengindikasikan perlu kehati-hatian."
        )

    # Kalimat 2: fundamental
    if s_fund >= 70:
        parts.append(f"Dari sisi fundamental ({s_fund:.0f}/100), rasio keuangan terlihat solid.")
    elif s_fund >= 50:
        parts.append(f"Fundamental ({s_fund:.0f}/100) berada di level moderat.")
    else:
        parts.append(f"Fundamental ({s_fund:.0f}/100) perlu diperhatikan.")

    # Kalimat 3: sentimen dan risiko
    if s_sent >= 60:
        parts.append(f"Sentimen pasar positif ({s_sent:.0f}/100).")
    elif s_sent <= 40:
        parts.append(f"Sentimen pasar cenderung negatif ({s_sent:.0f}/100).")

    if s_risk < 50:
        parts.append(f"Profil risiko cukup tinggi ({s_risk:.0f}/100), perlu waspada.")

    if saham.get("data_terbatas"):
        parts.append(f"⚠️ Catatan: {saham.get('catatan_data', 'data terbatas')}.")

    return " ".join(parts)


# ============================================================
# LangGraph: Build & Compile StateGraph
# ============================================================

def build_scoring_graph() -> Any:
    """
    Bangun dan compile LangGraph StateGraph untuk scoring pipeline.

    Graph flow:
        START → analisis_kondisi_pasar → hitung_skor → self_check
        self_check → generate_alasan (v1: selalu lanjut)
        generate_alasan → END

    Returns:
        Compiled LangGraph yang siap di-invoke
    """
    logger.info("🔧 Building scoring graph...")

    graph = StateGraph(ScoringState)

    # Register nodes
    graph.add_node("analisis_kondisi_pasar", analisis_kondisi_pasar)
    graph.add_node("hitung_skor", hitung_skor)
    graph.add_node("self_check", self_check)
    graph.add_node("generate_alasan", generate_alasan)

    # Define edges
    graph.add_edge(START, "analisis_kondisi_pasar")
    graph.add_edge("analisis_kondisi_pasar", "hitung_skor")
    graph.add_edge("hitung_skor", "self_check")

    # Conditional edge setelah self_check
    graph.add_conditional_edges(
        "self_check",
        _route_setelah_self_check,
        {
            "generate_alasan": "generate_alasan",
            # Future: "hitung_skor": "hitung_skor" (untuk retry loop)
        },
    )

    graph.add_edge("generate_alasan", END)

    # Compile
    compiled = graph.compile()
    logger.info("✅ Scoring graph berhasil di-compile")

    return compiled


# ============================================================
# Simpan Hasil ke PostgreSQL
# ============================================================

async def _simpan_hasil_ke_db(hasil_final: list[dict[str, Any]]) -> int:
    """
    Simpan hasil scoring ke tabel scoring_mingguan di PostgreSQL.

    Menggunakan upsert logic: jika sudah ada scoring untuk kode+tanggal
    yang sama, update data yang ada.

    Args:
        hasil_final: List hasil scoring dari graph

    Returns:
        Jumlah record yang berhasil disimpan
    """
    logger.info("💾 Menyimpan hasil scoring ke PostgreSQL...")

    saved = 0

    async with async_session() as session:
        for saham in hasil_final:
            try:
                # Cek apakah sudah ada scoring untuk tanggal ini
                stmt = select(ScoringMingguan).where(
                    ScoringMingguan.kode_saham == saham["kode_saham"],
                    ScoringMingguan.tanggal_scoring == date.today(),
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                # Map rekomendasi string ke Enum
                rekom_map = {
                    "BUY": Rekomendasi.BUY,
                    "HOLD": Rekomendasi.HOLD,
                    "SELL": Rekomendasi.SELL,
                }
                rekom_enum = rekom_map.get(
                    saham.get("rekomendasi", "HOLD"), Rekomendasi.HOLD
                )

                if existing:
                    # Update existing record
                    existing.skor_total = saham["skor_total"]
                    existing.skor_fundamental = saham["skor_fundamental"]
                    existing.skor_sentimen = saham["skor_sentimen"]
                    existing.skor_sektor = saham["skor_sektor"]
                    existing.skor_makro = saham["skor_makro"]
                    existing.skor_risiko = saham["skor_risiko"]
                    existing.bobot_fundamental = saham["bobot_fundamental"]
                    existing.bobot_sentimen = saham["bobot_sentimen"]
                    existing.bobot_sektor = saham["bobot_sektor"]
                    existing.bobot_makro = saham["bobot_makro"]
                    existing.bobot_risiko = saham["bobot_risiko"]
                    existing.alasan = saham.get("alasan", "")
                    existing.rekomendasi = rekom_enum
                    existing.confidence = saham.get("confidence", 0.5)
                else:
                    # Insert new record
                    new_scoring = ScoringMingguan(
                        kode_saham=saham["kode_saham"],
                        tanggal_scoring=date.today(),
                        skor_total=saham["skor_total"],
                        skor_fundamental=saham["skor_fundamental"],
                        skor_sentimen=saham["skor_sentimen"],
                        skor_sektor=saham["skor_sektor"],
                        skor_makro=saham["skor_makro"],
                        skor_risiko=saham["skor_risiko"],
                        bobot_fundamental=saham["bobot_fundamental"],
                        bobot_sentimen=saham["bobot_sentimen"],
                        bobot_sektor=saham["bobot_sektor"],
                        bobot_makro=saham["bobot_makro"],
                        bobot_risiko=saham["bobot_risiko"],
                        alasan=saham.get("alasan", ""),
                        rekomendasi=rekom_enum,
                        confidence=saham.get("confidence", 0.5),
                    )
                    session.add(new_scoring)

                saved += 1

            except Exception as e:
                logger.error(
                    f"❌ Gagal simpan scoring {saham['kode_saham']}: "
                    f"{type(e).__name__}: {e}"
                )

        await session.commit()

    logger.info(f"💾 {saved}/{len(hasil_final)} scoring berhasil disimpan")
    return saved


# ============================================================
# Entry Point: jalankan_scoring()
# ============================================================

async def jalankan_scoring(
    daftar_saham: list[str],
    simpan_ke_db: bool = True,
) -> list[dict[str, Any]]:
    """
    Entry point utama untuk menjalankan scoring pipeline.

    Dipanggil oleh APScheduler setiap Senin 06:00 WIB, atau
    bisa dipanggil manual dari API endpoint.

    Alur:
    1. Build LangGraph scoring pipeline
    2. Jalankan graph dengan daftar saham sebagai input
    3. Simpan hasil ke PostgreSQL (opsional)
    4. Return top 10 saham beserta alasan

    Args:
        daftar_saham: List kode saham yang akan di-scoring
                      (contoh: ["BBCA", "TLKM", "ASII", ...])
        simpan_ke_db: Apakah hasil disimpan ke PostgreSQL (default: True)

    Returns:
        List of dict, setiap dict berisi:
            - kode_saham (str)
            - skor_total (float): 0-100
            - skor_fundamental, skor_sentimen, skor_sektor, skor_makro, skor_risiko
            - bobot_* (float): bobot yang digunakan
            - alasan (str): penjelasan dari LLM (3-4 kalimat)
            - rekomendasi (str): "BUY", "HOLD", atau "SELL"
            - confidence (float): 0-1
            - data_terbatas (bool): flag jika data kurang lengkap

    Example:
        >>> hasil = await jalankan_scoring(["BBCA", "TLKM", "ASII", "BMRI"])
        >>> for s in hasil:
        ...     print(f"{s['kode_saham']}: {s['skor_total']:.1f} → {s['rekomendasi']}")
        BBCA: 78.5 → BUY
        BMRI: 72.3 → BUY
        ASII: 65.1 → HOLD
        TLKM: 61.8 → HOLD
    """
    logger.info("🚀" + "=" * 58)
    logger.info("🚀 AI SAHAM INDONESIA — SCORING MINGGUAN")
    logger.info(f"🚀 Tanggal: {date.today().isoformat()}")
    logger.info(f"🚀 Jumlah saham: {len(daftar_saham)}")
    logger.info("🚀" + "=" * 58)

    start_time = datetime.now(_WIB)

    # Health Check database (Kasus 4)
    try:
        from sqlalchemy import text
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ Health Check database sukses. Database online.")
    except Exception as e:
        logger.critical(f"🚨 CRITICAL: Database offline! Membatalkan seluruh proses scoring. Error: {e}")
        raise RuntimeError(f"Database offline, scoring dibatalkan: {e}")

    # Build graph
    graph = build_scoring_graph()

    # Siapkan initial state
    initial_state: ScoringState = {
        "daftar_saham": [k.strip().upper() for k in daftar_saham],
        "kondisi_pasar": {},
        "bobot": {},
        "skor_per_saham": [],
        "perlu_retry": [],
        "hasil_final": [],
    }

    # Jalankan graph
    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"❌ Scoring pipeline gagal: {type(e).__name__}: {e}")
        raise

    hasil_final = final_state.get("hasil_final", [])

    # Simpan ke database
    if simpan_ke_db and hasil_final:
        try:
            await _simpan_hasil_ke_db(hasil_final)
        except Exception as e:
            logger.error(f"❌ Gagal simpan ke DB (hasil tetap dikembalikan): {e}")

    # Ringkasan
    elapsed = (datetime.now(_WIB) - start_time).total_seconds()

    logger.info("")
    logger.info("🏆" + "=" * 58)
    logger.info("🏆 HASIL SCORING MINGGUAN — TOP 10")
    logger.info("🏆" + "=" * 58)

    for i, saham in enumerate(hasil_final, 1):
        flag = "⚠️" if saham.get("data_terbatas") else "✅"
        logger.info(
            f"   {flag} #{i:2d} {saham['kode_saham']:6s} "
            f"Skor={saham['skor_total']:5.1f} "
            f"→ {saham.get('rekomendasi', '?'):4s} "
            f"(conf={saham.get('confidence', 0):.2f})"
        )

    logger.info("")
    logger.info(f"⏱️  Selesai dalam {elapsed:.1f} detik")
    logger.info("=" * 60)

    return hasil_final
