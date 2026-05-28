"""
AI Saham Indonesia — FastAPI Server & Entrypoint

Modul ini menginisialisasi server web FastAPI, menghubungkan routing modular,
mengaktifkan background scheduler, men-serve frontend statis, dan mengonfigurasi
CORS middleware untuk akses dari aplikasi client iOS SwiftUI.

Cara menjalankan:
    uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.init_db import init_database
from backend.db.postgres import async_session, get_db_session, Saham, Fundamental, Makro, Berita, ScoringMingguan, Alert
from backend.data.preprocessors.embedder import get_embedder
from backend.workers import (
    seed_saham_if_empty,
    scrape_news_job,
    scrape_fundamental_job,
    scrape_makro_job,
    run_scoring_job,
)
from backend.agents.alert_agent import jalankan_monitoring
from backend.scheduler import setup_scheduler, start_scheduler, stop_scheduler

# Import routes
from backend.api.routes.rekomendasi import router as rekomendasi_router
from backend.api.routes.chatbot import router as chatbot_router
from backend.api.routes.data import router as data_router

_WIB = timezone(timedelta(hours=7))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler untuk inisialisasi database, memuat model AI (BGE-M3)
    ke memori, mengaktifkan background scheduler, dan menghentikan scheduler
    saat shutdown.
    """
    logger.info("🚀 Memulai aplikasi AI Saham Indonesia...")
    
    # 1. Inisialisasi Database (Create tables)
    try:
        await init_database()
    except Exception as e:
        logger.error(f"❌ Inisialisasi database gagal: {e}")
    
    # 1b. Inisialisasi ChromaDB Collections
    try:
        from backend.db.chroma import init_all_collections
        await asyncio.to_thread(init_all_collections)
    except Exception as e:
        logger.error(f"❌ Inisialisasi ChromaDB collections gagal: {e}")
    
    # 2. Seeding default saham
    try:
        await seed_saham_if_empty()
    except Exception as e:
        logger.error(f"❌ Seeding saham gagal: {e}")

    # 3. Muat Model Embedding BGE-M3 ke memori saat startup
    try:
        logger.info("🧠 Memuat model embedding BGE-M3 (lokal) ke memori...")
        # get_embedder() men-download (jika belum ada) dan meload model ke RAM/MPS/CUDA
        await asyncio.to_thread(get_embedder)
        logger.info("🧠 Model embedding BGE-M3 berhasil dimuat.")
    except Exception as e:
        logger.error(f"❌ Gagal memuat model embedding BGE-M3: {e}")

    # 4. Jalankan initial scrape secara asinkron agar DB terisi jika masih kosong
    async def run_initial_data_gathering():
        async with async_session() as session:
            # Cek data makro & fundamental
            makro_count = await session.scalar(select(func.count(Makro.id)))
            fund_count = await session.scalar(select(func.count(Fundamental.id)))
            
            if makro_count == 0 or fund_count == 0:
                logger.info("🌱 Database kosong dari data makro/fundamental. Menjalankan scraping awal...")
                await scrape_makro_job()
                await scrape_fundamental_job()
                await scrape_news_job()
                await run_scoring_job()

    # Jalankan initial gathering di background task
    asyncio.create_task(run_initial_data_gathering())

    # 5. Start Scheduler
    try:
        setup_scheduler()
        start_scheduler()
    except Exception as e:
        logger.error(f"❌ Gagal menyalakan scheduler: {e}")

    yield
    
    # Shutdown Scheduler
    try:
        stop_scheduler()
    except Exception as e:
        logger.error(f"❌ Gagal menonaktifkan scheduler: {e}")
    logger.info("🛑 Aplikasi AI Saham Indonesia dihentikan.")


# Build FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API untuk Sistem Rekomendasi Saham Indonesia & Chatbot RAG lokal",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS Middleware (diperluas agar bisa diakses oleh aplikasi SwiftUI / iOS Client secara nirkabel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Membuka akses CORS agar development dari simulator / iPhone berjalan lancar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Include APIRouters
# ============================================================

# Prefix "/api" di depan router modular untuk memisahkan API dari static front-end
app.include_router(rekomendasi_router, prefix="/api")
app.include_router(chatbot_router, prefix="/api")
app.include_router(data_router, prefix="/api")

# Register routers under root prefix as well to support SwiftUI and direct curl calls
app.include_router(rekomendasi_router)
app.include_router(chatbot_router)
app.include_router(data_router)


# ============================================================
# REST API Models & Extra Endpoints (Status & Trigger)
# ============================================================

class AlertPushRequest(BaseModel):
    saham: str = Field(..., description="Kode saham terkait")
    pesan: str = Field(..., description="Pesan alert sentimen")
    delta: float = Field(..., description="Nilai perubahan sentimen")


class SahamRequest(BaseModel):
    kode: str = Field(..., max_length=10, description="Kode saham IDX, contoh: BBCA")
    nama_perusahaan: str = Field(..., description="Nama lengkap perusahaan")
    sektor: str = Field(..., description="Sektor industri")
    sub_sektor: Optional[str] = Field(None, description="Sub-sektor industri")


@app.get("/api/status")
async def get_status(db: AsyncSession = Depends(get_db_session)):
    """
    Mendapatkan status server, database, scheduler, dan statistik data.
    """
    try:
        # Hitung statistik
        saham_count = await db.scalar(select(func.count(Saham.kode)))
        fund_count = await db.scalar(select(func.count(Fundamental.id)))
        makro_count = await db.scalar(select(func.count(Makro.id)))
        berita_count = await db.scalar(select(func.count(Berita.id)))
        scoring_count = await db.scalar(select(func.count(ScoringMingguan.id)))
        alert_count = await db.scalar(select(func.count(Alert.id)))

        # Cari tanggal scoring terakhir
        stmt_last_scoring = select(ScoringMingguan.tanggal_scoring).order_by(ScoringMingguan.tanggal_scoring.desc()).limit(1)
        res_last_scoring = await db.execute(stmt_last_scoring)
        last_scoring_date = res_last_scoring.scalar_one_or_none()

        # Dapatkan status scheduler jobs dari module scheduler
        from backend.scheduler import scheduler as active_sched
        jobs = []
        if active_sched.running:
            for job in active_sched.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                })

        return {
            "status": "online",
            "environment": settings.app_env,
            "timestamp": datetime.now(_WIB).isoformat(),
            "database": {
                "saham_total": saham_count,
                "fundamental_total": fund_count,
                "makro_total": makro_count,
                "berita_total": berita_count,
                "scoring_total": scoring_count,
                "alerts_total": alert_count,
                "tanggal_scoring_terakhir": last_scoring_date.isoformat() if last_scoring_date else None,
            },
            "scheduler": {
                "running": active_sched.running,
                "jobs": jobs
            }
        }
    except Exception as e:
        logger.error(f"❌ Gagal mendapatkan status: {e}")
        raise HTTPException(status_code=500, detail=f"Database / Server error: {str(e)}")


@app.post("/api/alerts/push")
async def push_alert(request: AlertPushRequest):
    """
    Endpoint simulator push notification ke handphone/iPhone.
    """
    logger.warning(
        f"📱 PUSH NOTIFICATION SENT -> Saham: {request.saham} | "
        f"Delta: {request.delta:+.1f} | Pesan: {request.pesan}"
    )
    return {"status": "success", "message": "Alert push notification simulated."}


@app.get("/api/alerts")
async def get_alerts(limit: int = 20, db: AsyncSession = Depends(get_db_session)):
    """
    Mendapatkan riwayat alert terbaru dari database PostgreSQL.
    """
    try:
        stmt = select(Alert).order_by(Alert.tanggal.desc()).limit(limit)
        result = await db.execute(stmt)
        alerts = result.scalars().all()
        return alerts
    except Exception as e:
        logger.error(f"❌ Gagal mengambil riwayat alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/saham")
async def add_saham(request: SahamRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Menambahkan saham baru ke dalam daftar pantau sistem.
    """
    try:
        kode = request.kode.strip().upper()
        # Cek apakah sudah ada
        stmt_exist = select(Saham).where(Saham.kode == kode)
        res_exist = await db.execute(stmt_exist)
        if res_exist.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Saham {kode} sudah terdaftar.")

        new_saham = Saham(
            kode=kode,
            nama_perusahaan=request.nama_perusahaan.strip(),
            sektor=request.sektor.strip(),
            sub_sektor=request.sub_sektor.strip() if request.sub_sektor else None,
            tanggal_listing=None
        )
        db.add(new_saham)
        await db.commit()
        logger.info(f"➕ Saham baru ditambahkan: {kode}")
        return {"status": "success", "message": f"Saham {kode} berhasil ditambahkan."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Gagal menambah saham: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/trigger")
async def trigger_job(job_name: str, background_tasks: BackgroundTasks):
    """
    Memicu background job manual secara asynchronous.
    """
    valid_jobs = {
        "scrape_news": (scrape_news_job, "Scraping Berita & RAG Indexing"),
        "scrape_fundamental": (scrape_fundamental_job, "Scraping Data Fundamental"),
        "scrape_makro": (scrape_makro_job, "Scraping Data Makroekonomi"),
        "run_scoring": (run_scoring_job, "Scoring Rekomendasi Mingguan"),
        "run_alerts": (jalankan_monitoring, "Monitoring Alert & Fluktuasi Sentimen"),
    }

    if job_name not in valid_jobs:
        raise HTTPException(
            status_code=400,
            detail=f"Job name tidak valid. Pilih salah satu dari: {list(valid_jobs.keys())}"
        )

    job_func, label = valid_jobs[job_name]
    background_tasks.add_task(job_func)
    
    return {
        "status": "accepted",
        "message": f"Job '{label}' berhasil dipicu di background."
    }


# ============================================================
# Serve Static Frontend Dashboard
# ============================================================

# Endpoint utama untuk melayani index.html
@app.get("/")
async def get_index():
    return FileResponse("backend/static/index.html")

# Daftarkan directory static files untuk asset lainnya
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Catch-all endpoint untuk single page application routing
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    return FileResponse("backend/static/index.html")
