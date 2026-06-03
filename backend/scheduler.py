"""
AI Saham Indonesia — Background Job Scheduler

Mengonfigurasi dan mengelola pekerjaan terjadwal (cron jobs) secara lokal.
Menggunakan APScheduler dengan AsyncIOScheduler disesuaikan ke timezone Asia/Jakarta (WIB).
"""

from datetime import date, datetime, timedelta, timezone
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from backend.config import settings
from backend.db.postgres import async_session, Saham
from backend.workers import (
    scrape_fundamental_job,
    scrape_makro_job,
    scrape_news_job,
    run_scoring_job,
    update_last_prices_job,
)
from backend.agents.alert_agent import jalankan_monitoring

# Timezone WIB (UTC+7)
_WIB = timezone(timedelta(hours=7))

# Initialize scheduler singleton
scheduler = AsyncIOScheduler(timezone=_WIB)


# ============================================================
# Job Wrappers dengan Try/Except & Logging
# ============================================================

async def job_weekly_scoring() -> None:
    """
    Job 1: Mengambil seluruh watchlist saham dari PostgreSQL,
    lalu menjalankan pipeline scoring mingguan (scoring_agent).
    Dijalankan setiap hari Senin jam 06:00 WIB.
    """
    logger.info("⏱️ [SCHEDULER] Menjalankan Job 1: Scoring & Rekomendasi Mingguan...")
    try:
        async with async_session() as session:
            result = await session.execute(select(Saham.kode))
            watchlist = list(result.scalars().all())

        if not watchlist:
            logger.warning("⚠️ [SCHEDULER] Watchlist saham kosong. Scoring dibatalkan.")
            return

        logger.info(f"🚀 [SCHEDULER] Scoring {len(watchlist)} saham...")
        await run_scoring_job()
        logger.info("✅ [SCHEDULER] Job 1: Scoring selesai dengan sukses.")

    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Job 1: Gagal menjalankan scoring mingguan: {e}")


async def job_sentiment_monitoring() -> None:
    """
    Job 2: Menjalankan Alert Agent untuk memantau fluktuasi sentimen.
    Mengecek berita baru dan memicu push notification jika delta > 10 poin.
    Dijalankan setiap 30 menit.
    """
    logger.info("⏱️ [SCHEDULER] Menjalankan Job 2: Pemantauan Alert Sentimen...")
    try:
        await jalankan_monitoring()
        logger.info("✅ [SCHEDULER] Job 2: Monitoring selesai.")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Job 2: Gagal menjalankan pemantauan sentimen: {e}")


async def job_daily_data_update() -> None:
    """
    Job 3: Memperbarui data fundamental keuangan emiten (dari Yahoo Finance)
    serta indikator makroekonomi (BI rate, inflasi, kurs USD/IDR, IHSG).
    Dijalankan setiap hari jam 07:00 WIB.
    """
    logger.info("⏱️ [SCHEDULER] Menjalankan Job 3: Pembaruan Data Fundamental & Makroekonomi...")
    
    # Run Fundamental Update
    try:
        logger.info("📊 [SCHEDULER] Memulai update data fundamental harian...")
        await scrape_fundamental_job()
        logger.info("✅ [SCHEDULER] Data fundamental berhasil diperbarui.")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Gagal memperbarui data fundamental: {e}")

    # Run Macro Update
    try:
        logger.info("🌍 [SCHEDULER] Memulai update data makroekonomi harian...")
        await scrape_makro_job()
        logger.info("✅ [SCHEDULER] Data makroekonomi berhasil diperbarui.")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Gagal memperbarui data makroekonomi: {e}")


async def job_last_price_update() -> None:
    """
    Job 4: Memperbarui hanya last price dan volume emiten di watchlist
    dari Yahoo Finance secara cepat. Dijalankan setiap 30 menit.
    """
    logger.info("⏱️ [SCHEDULER] Menjalankan Job 4: Update Last Price & Volume (30 Menit)...")
    try:
        await update_last_prices_job()
        logger.info("✅ [SCHEDULER] Job 4: Update Last Price selesai.")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Job 4: Gagal menjalankan update last price: {e}")


# ============================================================
# Scheduler Lifecycle Control
# ============================================================

def setup_scheduler() -> None:
    """
    Mendaftarkan seluruh background jobs ke scheduler dengan pemicu interval/cron.
    """
    logger.info("⏰ Mengonfigurasi background jobs scheduler...")

    # Job 1: Setiap hari Senin jam 06:00 WIB
    scheduler.add_job(
        job_weekly_scoring,
        CronTrigger(
            day_of_week=settings.scoring_cron_day_of_week,  # default 'mon'
            hour=settings.scoring_cron_hour,               # default 6
            minute=settings.scoring_cron_minute            # default 0
        ),
        id="weekly_scoring_job",
        name="Weekly Scoring & Recommendations",
        replace_existing=True,
    )

    # Job 2: Setiap 30 menit
    scheduler.add_job(
        job_sentiment_monitoring,
        IntervalTrigger(minutes=settings.alert_check_interval_minutes),  # default 30 menit
        id="sentiment_monitoring_job",
        name="Sentiment Volatility Monitoring & Alerts",
        replace_existing=True,
    )

    # Job 3: Setiap hari jam 07:00 WIB
    scheduler.add_job(
        job_daily_data_update,
        CronTrigger(hour=7, minute=0),
        id="daily_data_update_job",
        name="Daily Fundamental & Macro Data Update",
        replace_existing=True,
    )

    # Job 4: Setiap 30 menit untuk fast price updates
    scheduler.add_job(
        job_last_price_update,
        IntervalTrigger(minutes=30),
        id="last_price_update_job",
        name="Fast Stock Last Price Update (Every 30m)",
        replace_existing=True,
    )

    logger.info("✅ Konfigurasi jobs scheduler selesai.")


def start_scheduler() -> None:
    """
    Menyalakan scheduler di background.
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ Background scheduler berhasil dinyalakan.")
    else:
        logger.warning("⏰ Scheduler sudah berjalan.")


def stop_scheduler() -> None:
    """
    Menghentikan scheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Background scheduler berhasil dimatikan.")
