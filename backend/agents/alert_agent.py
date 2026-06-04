"""
AI Saham Indonesia — Alert Agent (LangGraph)

Agent yang memantau fluktuasi sentimen secara real-time berdasarkan berita baru.
Jika sentimen saham berubah signifikan (> 10 poin) dibanding rata-rata seminggu
terakhir, agent akan memicu alert dan mengirimkan push notification.

Penggunaan:
    from backend.agents.alert_agent import jalankan_monitoring
    await jalankan_monitoring()
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, TypedDict

import httpx
from loguru import logger
from sqlalchemy import select
from langgraph.graph import END, START, StateGraph

from backend.config import settings
from backend.db.postgres import (
    async_session,
    Saham,
    Berita,
    Alert,
)
from backend.data.collectors.berita_collector import collect_berita_batch
from backend.data.preprocessors.data_cleaner import clean_berita, hitung_sentimen_sederhana, hitung_sentimen_qwen

# Timezone WIB (UTC+7)
_WIB = timezone(timedelta(hours=7))


# ============================================================
# State Definition
# ============================================================

class AlertState(TypedDict):
    berita_baru: list[dict[str, Any]]
    saham_terdampak: list[str]
    perubahan_skor: dict[str, float]      # {kode_saham: delta_skor}
    alert_yang_dikirim: list[dict[str, Any]]


# ============================================================
# NODE 1: Cek Berita Baru
# ============================================================

async def cek_berita_baru(state: AlertState) -> dict[str, Any]:
    """
    Mengambil berita baru dari RSS untuk seluruh saham watchlist aktif,
    memfilter yang belum terdaftar di database (berdasarkan URL),
    dan menghitung skor sentimen berita baru tersebut.
    """
    logger.info("=" * 60)
    logger.info("🚨 NODE 1: Cek Berita Baru")
    logger.info("=" * 60)

    # 1. Dapatkan watchlist aktif dari database
    try:
        async with async_session() as session:
            result = await session.execute(select(Saham.kode))
            watchlist = result.scalars().all()
    except Exception as e:
        logger.error(f"❌ Gagal mengambil watchlist saham: {e}")
        return {"berita_baru": []}

    if not watchlist:
        logger.warning("⚠️ Watchlist saham kosong. Monitoring dibatalkan.")
        return {"berita_baru": []}

    # 2. Collect berita untuk semua saham (batch) untuk 2 hari terakhir
    logger.info(f"📰 Mengambil berita terkini untuk {len(watchlist)} saham...")
    try:
        berita_didapat = await collect_berita_batch(list(watchlist), hari_terakhir=2)
    except Exception as e:
        logger.error(f"❌ Gagal mengambil berita batch: {e}")
        return {"berita_baru": []}

    if not berita_didapat:
        logger.info("📰 Tidak ditemukan berita baru dari RSS feed.")
        return {"berita_baru": []}

    # 3. Filter berita yang belum ada di database berdasarkan URL
    urls = [b["url"] for b in berita_didapat if "url" in b]
    berita_baru: list[dict[str, Any]] = []

    try:
        async with async_session() as session:
            # Query URL yang sudah ada di database
            stmt = select(Berita.url).where(Berita.url.in_(urls))
            result = await session.execute(stmt)
            existing_urls = set(result.scalars().all())

            # Filter yang belum ada
            for item in berita_didapat:
                url = item.get("url")
                if url and url not in existing_urls:
                    # Bersihkan berita
                    cleaned = clean_berita(item)
                    # Hitung skor sentimen (Kasus 5)
                    cleaned["skor_sentimen"] = await hitung_sentimen_qwen(cleaned["judul"])
                    berita_baru.append(cleaned)
                    
    except Exception as e:
        logger.error(f"❌ Gagal memeriksa URL berita di database: {e}")
        return {"berita_baru": []}

    logger.info(f"📰 Terdeteksi {len(berita_baru)} berita baru yang belum di-index.")
    return {"berita_baru": berita_baru}


# ============================================================
# NODE 2: Evaluasi Dampak
# ============================================================

async def evaluasi_dampak(state: AlertState) -> dict[str, Any]:
    """
    Mengestimasi fluktuasi sentimen per saham berdasarkan berita baru.
    Membandingkan rata-rata sentimen berita baru dengan rata-rata sentimen
    berita lama (7 hari terakhir) di database.
    Jika selisih skor > 10 poin, tandai saham tersebut sebagai terdampak.
    """
    logger.info("=" * 60)
    logger.info("🔍 NODE 2: Evaluasi Dampak Sentimen")
    logger.info("=" * 60)

    berita_baru = state.get("berita_baru", [])
    if not berita_baru:
        logger.info("🔍 Tidak ada berita baru untuk dievaluasi.")
        return {"saham_terdampak": [], "perubahan_skor": {}}

    saham_terdampak: list[str] = []
    perubahan_skor: dict[str, float] = {}

    # Kelompokkan berita baru berdasarkan kode saham
    berita_per_saham: dict[str, list[dict]] = {}
    for b in berita_baru:
        kode = b.get("kode_saham")
        if kode:
            if kode not in berita_per_saham:
                berita_per_saham[kode] = []
            berita_per_saham[kode].append(b)

    seminggu_lalu = datetime.now(timezone.utc) - timedelta(days=7)

    for kode, item_list in berita_per_saham.items():
        # 1. Hitung rata-rata sentimen baru (skala 0-100)
        rata_sentimen_baru = sum(b["skor_sentimen"] for b in item_list) / len(item_list)
        skor_sentimen_baru = (rata_sentimen_baru + 1.0) / 2.0 * 100

        # 2. Ambil sentimen lama (7 hari terakhir) dari DB
        skor_sentimen_lama = 50.0  # Default netral jika tidak ada data lama
        try:
            async with async_session() as session:
                stmt = select(Berita.skor_sentimen).where(
                    Berita.kode_saham == kode,
                    Berita.skor_sentimen.isnot(None),
                    Berita.tanggal_publish >= seminggu_lalu
                )
                result = await session.execute(stmt)
                sentimen_lama_list = result.scalars().all()

                if sentimen_lama_list:
                    rata_sentimen_lama = sum(sentimen_lama_list) / len(sentimen_lama_list)
                    skor_sentimen_lama = (rata_sentimen_lama + 1.0) / 2.0 * 100
        except Exception as e:
            logger.error(f"❌ Gagal mengambil sentimen lama {kode} dari DB: {e}")

        # 3. Hitung delta perubahan skor
        delta = skor_sentimen_baru - skor_sentimen_lama
        logger.info(
            f"   📈 {kode}: Skor Lama={skor_sentimen_lama:.1f}, "
            f"Skor Baru={skor_sentimen_baru:.1f} → Delta={delta:+.1f} poin"
        )

        # 4. Jika perubahan > 10 poin (naik atau turun)
        if abs(delta) > 10.0:
            saham_terdampak.append(kode)
            perubahan_skor[kode] = round(delta, 2)
            logger.warning(
                f"   🚨 ALARM: Fluktuasi sentimen {kode} melampaui threshold! "
                f"Delta = {delta:+.1f} poin"
            )

    return {
        "saham_terdampak": saham_terdampak,
        "perubahan_skor": perubahan_skor,
    }


def _route_setelah_evaluasi(state: AlertState) -> str:
    """
    Routing logic untuk evaluasi dampak.
    Jika tidak ada saham terdampak -> langsung END.
    Jika ada saham terdampak -> lanjut ke kirim_alert.
    """
    saham_list = state.get("saham_terdampak", [])
    if not saham_list:
        logger.info("➡️ Aliran: Tidak ada perubahan sentimen signifikan. END.")
        return "end"
    logger.info(f"➡️ Aliran: {len(saham_list)} saham terdampak. Kirim Alert.")
    return "kirim_alert"


# ============================================================
# NODE 3: Kirim Alert
# ============================================================

async def kirim_alert(state: AlertState) -> dict[str, Any]:
    """
    Menyimpan alert ke database PostgreSQL dan mengirim push notification
    ke endpoint FastAPI (yang nantinya akan meneruskan ke iPhone).
    """
    logger.info("=" * 60)
    logger.info("🚀 NODE 3: Kirim Alert")
    logger.info("=" * 60)

    saham_terdampak = state.get("saham_terdampak", [])
    perubahan_skor = state.get("perubahan_skor", {})
    berita_baru = state.get("berita_baru", [])
    alert_yang_dikirim: list[dict[str, Any]] = []

    # Buat mapping kode_saham -> judul berita baru paling relevan/terkini
    berita_terbaru: dict[str, str] = {}
    for b in berita_baru:
        kode = b.get("kode_saham")
        if kode and (kode not in berita_terbaru):
            berita_terbaru[kode] = b.get("judul", "")

    # Jalankan HTTP client untuk push alert
    async with httpx.AsyncClient(timeout=10.0) as client:
        for kode in saham_terdampak:
            delta = perubahan_skor.get(kode, 0.0)
            judul_berita = berita_terbaru.get(kode, "Berita Terkini")
            
            tanda = "+" if delta > 0 else ""
            pesan = (
                f"Sentimen {kode} berubah signifikan. "
                f"Ada berita besar: \"{judul_berita}\" ({tanda}{delta:.1f} poin)"
            )

            alert_payload = {
                "saham": kode,
                "pesan": pesan,
                "delta": delta
            }

            logger.info(f"💾 Menyimpan alert untuk {kode} ke PostgreSQL...")
            
            dikirim_sukses = False
            # 1. Simpan ke database relasional
            try:
                async with async_session() as session:
                    new_alert = Alert(
                        kode_saham=kode,
                        tanggal=datetime.now(_WIB),
                        pesan=pesan,
                        delta=delta,
                        dikirim=False
                    )
                    session.add(new_alert)
                    await session.commit()
                    
                    # Ambil ID untuk referensi
                    alert_id = new_alert.id
            except Exception as e:
                logger.error(f"❌ Gagal menyimpan alert ke PostgreSQL: {e}")
                alert_id = None

            # 2. Kirim push notification ke server API lokal
            # Server FastAPI akan meneruskan ke handphone (iPhone via APNS)
            endpoint_url = f"http://localhost:{settings.app_port}/api/alerts/push"
            try:
                logger.info(f"Sending push alert to: {endpoint_url}")
                response = await client.post(endpoint_url, json=alert_payload)
                if response.status_code == 200:
                    logger.info(f"✅ Push notification berhasil dikirim untuk {kode}.")
                    dikirim_sukses = True
                else:
                    logger.warning(
                        f"⚠️ Server merespon HTTP {response.status_code} "
                        f"saat mengirim alert {kode}."
                    )
            except Exception as e:
                logger.error(f"❌ Gagal terhubung ke endpoint push alert: {e}")

            # 3. Update flag dikirim di DB jika sukses
            if dikirim_sukses and alert_id:
                try:
                    async with async_session() as session:
                        stmt = select(Alert).where(Alert.id == alert_id)
                        res = await session.execute(stmt)
                        db_alert = res.scalar_one_or_none()
                        if db_alert:
                            db_alert.dikirim = True
                            await session.commit()
                            logger.info(f"✅ Status alert ID {alert_id} diperbarui menjadi 'dikirim'.")
                except Exception as e:
                    logger.error(f"❌ Gagal memperbarui status kirim alert di DB: {e}")

            alert_yang_dikirim.append(alert_payload)

    # 4. Simpan berita baru yang memicu alert ke PostgreSQL juga (sebagai metadata)
    # Ini membantu agar berita tidak di-scrape ulang & data relasional sinkron
    try:
        async with async_session() as session:
            for b in berita_baru:
                stmt = select(Berita.id).where(Berita.url == b["url"])
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    new_news = Berita(
                        kode_saham=b["kode_saham"],
                        judul=b["judul"],
                        url=b["url"],
                        sumber=b["sumber"],
                        tanggal_publish=b["tanggal_publish"],
                        skor_sentimen=b["skor_sentimen"],
                        sudah_diembedding=False
                    )
                    session.add(new_news)
            await session.commit()
            logger.info("💾 Berita pemicu alert telah di-backfill ke PostgreSQL.")
    except Exception as e:
        logger.error(f"❌ Gagal backfill berita pemicu alert ke PostgreSQL: {e}")

    return {"alert_yang_dikirim": alert_yang_dikirim}


# ============================================================
# LangGraph: Build & Compile StateGraph
# ============================================================

def build_alert_graph() -> Any:
    """
    Membangun dan mengompilasi StateGraph sederhana untuk memantau fluktuasi sentimen.
    """
    logger.debug("🔧 Building alert graph...")
    
    graph = StateGraph(AlertState)

    # Register Nodes
    graph.add_node("cek_berita_baru", cek_berita_baru)
    graph.add_node("evaluasi_dampak", evaluasi_dampak)
    graph.add_node("kirim_alert", kirim_alert)

    # Register Edges
    graph.add_edge(START, "cek_berita_baru")
    graph.add_edge("cek_berita_baru", "evaluasi_dampak")

    # Conditional router setelah evaluasi_dampak
    graph.add_conditional_edges(
        "evaluasi_dampak",
        _route_setelah_evaluasi,
        {
            "kirim_alert": "kirim_alert",
            "end": END
        }
    )

    graph.add_edge("kirim_alert", END)

    compiled = graph.compile()
    logger.debug("✅ Alert graph berhasil di-compile.")
    
    return compiled


# ============================================================
# Entry Point: jalankan_monitoring()
# ============================================================

async def jalankan_monitoring() -> None:
    """
    Entry point utama untuk monitoring alert sentimen saham.
    Dipanggil secara berkala oleh APScheduler.
    """
    logger.info("🚨" + "=" * 58)
    logger.info("🚨 MEMULAI PEMANTAUAN ALERT SENTIMEN SAHAM")
    logger.info("🚨" + "=" * 58)

    graph = build_alert_graph()

    initial_state: AlertState = {
        "berita_baru": [],
        "saham_terdampak": [],
        "perubahan_skor": {},
        "alert_yang_dikirim": []
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        alerts = final_state.get("alert_yang_dikirim", [])
        
        logger.info("")
        logger.info("🚨" + "=" * 58)
        logger.info(f"🚨 PEMANTAUAN SELESAI: {len(alerts)} alert dipicu.")
        for a in alerts:
            logger.warning(f"   • {a['saham']} (delta={a['delta']:+.1f}): {a['pesan']}")
        logger.info("🚨" + "=" * 58)
        
    except Exception as e:
        logger.error(f"❌ Gagal menjalankan pipeline monitoring alert: {e}")
