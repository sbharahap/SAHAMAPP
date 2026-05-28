"""
AI Saham Indonesia — Router Data Saham & Makro

Endpoint API untuk mengambil metadata saham, data fundamental harian,
dan indikator makroekonomi terupdate dari database.
"""

from datetime import date
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.postgres import get_db_session, Saham, Fundamental, Makro

router = APIRouter(
    tags=["Data Keuangan & Makro"],
)


@router.get("/saham/list")
@router.get("/data/saham/list")
async def get_saham_list(db: AsyncSession = Depends(get_db_session)):
    """
    Mengambil seluruh kode emiten saham beserta nama perusahaan dan sektornya.
    """
    try:
        stmt = select(Saham).order_by(Saham.kode)
        result = await db.execute(stmt)
        saham_list = result.scalars().all()
        
        return [
            {
                "kode": s.kode,
                "nama_perusahaan": s.nama_perusahaan,
                "sektor": s.sektor,
                "sub_sektor": s.sub_sektor
            }
            for s in saham_list
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil daftar saham: {str(e)}"
        )


@router.get("/saham/{kode}/fundamental")
@router.get("/data/saham/{kode}/fundamental")
async def get_fundamental_saham(
    kode: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mengambil data snapshot fundamental keuangan terbaru untuk saham tertentu.
    """
    kode_upper = kode.strip().upper()
    try:
        # Cek saham
        stmt_saham = select(Saham).where(Saham.kode == kode_upper)
        res_saham = await db.execute(stmt_saham)
        saham_obj = res_saham.scalar_one_or_none()

        if not saham_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Saham dengan kode '{kode_upper}' tidak terdaftar."
            )

        # Query fundamental terbaru
        stmt_fund = (
            select(Fundamental)
            .where(Fundamental.kode_saham == kode_upper)
            .order_by(Fundamental.tanggal.desc())
            .limit(1)
        )
        res_fund = await db.execute(stmt_fund)
        fund = res_fund.scalar_one_or_none()

        if not fund:
            raise HTTPException(
                status_code=404,
                detail=f"Saham '{kode_upper}' belum memiliki data fundamental harian."
            )

        return {
            "kode_saham": fund.kode_saham,
            "nama_perusahaan": saham_obj.nama_perusahaan,
            "tanggal_update": fund.tanggal.isoformat(),
            "harga_terakhir": fund.harga_terakhir,
            "volume": fund.volume,
            "roe": fund.roe,
            "eps": fund.eps,
            "pbv": fund.pbv,
            "der": fund.der,
            "market_cap": fund.market_cap,
            "pe_ratio": fund.pe_ratio,
            "dividend_yield": fund.dividend_yield,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil fundamental saham {kode_upper}: {str(e)}"
        )


@router.get("/makro/terbaru")
@router.get("/data/makro/terbaru")
async def get_makro_terbaru(db: AsyncSession = Depends(get_db_session)):
    """
    Mengambil snapshot kondisi indikator makroekonomi terkini (BI rate, inflasi, kurs, IHSG).
    """
    indikator_list = ["bi_rate", "kurs_usd_idr", "ihsg", "inflasi_yoy"]
    makro_data = {}

    try:
        for ind in indikator_list:
            stmt = (
                select(Makro)
                .where(Makro.indikator == ind)
                .order_by(Makro.tanggal.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            obj = result.scalar_one_or_none()

            if obj:
                makro_data[ind] = {
                    "nilai": obj.nilai,
                    "satuan": obj.satuan,
                    "tanggal": obj.tanggal.isoformat(),
                    "sumber": obj.sumber
                }
            else:
                makro_data[ind] = None

        return {
            "tanggal_fetch": date.today().isoformat(),
            "indikator": makro_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil data makroekonomi terbaru: {str(e)}"
        )
