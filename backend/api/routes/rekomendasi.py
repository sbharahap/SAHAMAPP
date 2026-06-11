"""
AI Saham Indonesia — Router Rekomendasi

Endpoint API untuk mengambil hasil scoring mingguan (top 10) dan detail scoring
untuk masing-masing saham secara spesifik.
"""

from datetime import date
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.postgres import get_db_session, ScoringMingguan, Saham
from backend.config import settings
from backend.api.routes.data import get_single_stock_price_stats

def clean_alasan_text(text: str) -> str:
    if not text:
        return ""
    import re
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        # Hapus header bracket seperti [RISIKO], [RECOMMENDASI], [ANALISIS], [REKOMENDASI]
        if line_stripped.startswith("[") and line_stripped.endswith("]"):
            continue
        # Hapus baris yang hanya berisi kata rekomendasi
        if line_stripped.upper() in ["RECOMMENDED", "NEUTRAL", "NEGATIVE", "RECOMMENDATION", "REKOMENDASI", "BUY", "SELL", "HOLD"]:
            continue
        cleaned_lines.append(line_stripped)
    # Join dengan spasi agar menjadi satu paragraf mengalir
    joined = " ".join(cleaned_lines).strip()
    # Hapus catatan berita kurang secara dinamis
    joined = re.sub(r'⚠️\s*Catatan:\s*berita kurang[^\.]*\.?', '', joined)
    joined = re.sub(r'⚠️\s*Catatan:[^\.]*\.?', '', joined)
    # Hapus spasi ganda dan rapikan
    joined = re.sub(r'\s+', ' ', joined).strip()
    return joined



router = APIRouter(
    prefix="/rekomendasi",
    tags=["Rekomendasi"],
)


@router.get("/mingguan")
async def get_rekomendasi_mingguan(
    tanggal: Optional[date] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mengambil daftar top 10 rekomendasi saham hasil scoring mingguan terbaru
    (atau berdasarkan parameter tanggal tertentu jika disediakan).
    """
    try:
        # Jika tanggal tidak diberikan, cari tanggal scoring terakhir di DB
        if not tanggal:
            stmt_date = (
                select(ScoringMingguan.tanggal_scoring)
                .order_by(ScoringMingguan.tanggal_scoring.desc())
                .limit(1)
            )
            res_date = await db.execute(stmt_date)
            tanggal = res_date.scalar_one_or_none()

            if not tanggal:
                return {
                    "tanggal": None,
                    "rekomendasi": [],
                    "message": "Belum ada hasil scoring mingguan di database."
                }

        # Query saham teratas di tanggal scoring tersebut
        stmt = (
            select(ScoringMingguan, Saham.nama_perusahaan, Saham.sektor)
            .join(Saham, ScoringMingguan.kode_saham == Saham.kode)
            .where(ScoringMingguan.tanggal_scoring == tanggal)
            .order_by(ScoringMingguan.skor_total.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        rekomendasi_list = []
        for i, row in enumerate(rows, 1):
            scoring_obj, nama_pt, sektor = row
            rekomendasi_list.append({
                "rank": i,
                "kode_saham": scoring_obj.kode_saham,
                "nama_perusahaan": nama_pt,
                "sektor": sektor,
                "skor_total": scoring_obj.skor_total,
                "skor_fundamental": scoring_obj.skor_fundamental,
                "skor_sentimen": scoring_obj.skor_sentimen,
                "skor_sektor": scoring_obj.skor_sektor,
                "skor_makro": scoring_obj.skor_makro,
                "skor_risiko": scoring_obj.skor_risiko,
                "rekomendasi": scoring_obj.rekomendasi.value,
                "confidence": scoring_obj.confidence,
                "alasan": clean_alasan_text(scoring_obj.alasan),
            })

        return {
            "tanggal": tanggal.isoformat(),
            "rekomendasi": rekomendasi_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil rekomendasi mingguan: {str(e)}"
        )


@router.get("/saham/{kode}")
async def get_rekomendasi_saham(
    kode: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mengambil data detail scoring dan analisis AI terbaru untuk satu saham tertentu berdasarkan kode.
    """
    kode_upper = kode.strip().upper()
    try:
        # Check apakah saham terdaftar
        stmt_saham = select(Saham).where(Saham.kode == kode_upper)
        res_saham = await db.execute(stmt_saham)
        saham_obj = res_saham.scalar_one_or_none()

        if not saham_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Saham dengan kode '{kode_upper}' tidak ditemukan dalam database."
            )

        # Ambil scoring terbaru
        stmt_scoring = (
            select(ScoringMingguan)
            .where(ScoringMingguan.kode_saham == kode_upper)
            .order_by(ScoringMingguan.tanggal_scoring.desc())
            .limit(1)
        )
        res_scoring = await db.execute(stmt_scoring)
        scoring_obj = res_scoring.scalar_one_or_none()

        if not scoring_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Saham '{kode_upper}' belum memiliki data hasil scoring."
            )

        # Ambil harga dan perubahan harga
        price, change, pct_change = await get_single_stock_price_stats(kode_upper, db)

        return {
            "kode_saham": scoring_obj.kode_saham,
            "nama_perusahaan": saham_obj.nama_perusahaan,
            "sektor": saham_obj.sektor,
            "sub_sektor": saham_obj.sub_sektor,
            "tanggal_scoring": scoring_obj.tanggal_scoring.isoformat(),
            "skor_total": scoring_obj.skor_total,
            "skor_fundamental": scoring_obj.skor_fundamental,
            "skor_sentimen": scoring_obj.skor_sentimen,
            "skor_sektor": scoring_obj.skor_sektor,
            "skor_makro": scoring_obj.skor_makro,
            "skor_risiko": scoring_obj.skor_risiko,
            "bobot": {
                "fundamental": scoring_obj.bobot_fundamental,
                "sentimen": scoring_obj.bobot_sentimen,
                "sektor": scoring_obj.bobot_sektor,
                "makro": scoring_obj.bobot_makro,
                "risiko": scoring_obj.bobot_risiko,
            },
            "rekomendasi": scoring_obj.rekomendasi.value,
            "confidence": scoring_obj.confidence,
            "alasan": clean_alasan_text(scoring_obj.alasan),
            "data_terbatas": scoring_obj.confidence < 0.4,
            "catatan_data": "Data fundamental atau berita pendukung kurang lengkap di database." if scoring_obj.confidence < 0.4 else "",
            "price": price,
            "change": change,
            "pct_change": pct_change,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil detail scoring saham {kode_upper}: {str(e)}"
        )
