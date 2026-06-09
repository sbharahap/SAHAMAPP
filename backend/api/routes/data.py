"""
AI Saham Indonesia — Router Data Saham & Makro

Endpoint API untuk mengambil metadata saham, data fundamental harian,
dan indikator makroekonomi terupdate dari database.
"""

import asyncio
from collections import defaultdict
from datetime import date
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
import pandas as pd
import pytz
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
import yfinance as yf

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


def fetch_yf_single(symbol: str) -> tuple[float, float, float]:
    """
    Mengambil data harga penutupan terakhir dan perubahan harga dari yfinance (synchronous).
    """
    try:
        ticker = yf.Ticker(f"{symbol}.JK")
        hist = ticker.history(period="2d")
        if not hist.empty:
            if len(hist) >= 2:
                price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2])
                change = price - prev_close
                pct_change = (change / prev_close) * 100.0 if prev_close > 0 else 0.0
                return round(price, 2), round(change, 2), round(pct_change, 2)
            else:
                price = float(hist['Close'].iloc[-1])
                return round(price, 2), 0.0, 0.0
    except Exception as e:
        logger.error(f"Gagal mengambil fallback yfinance untuk {symbol}: {e}")
    return 0.0, 0.0, 0.0


async def get_single_stock_price_stats(symbol: str, db: AsyncSession) -> tuple[float, float, float]:
    """
    Mengambil data harga penutupan terakhir, nominal perubahan, dan persentase perubahan untuk satu saham.
    """
    symbol_upper = symbol.strip().upper()
    try:
        stmt_fund = (
            select(Fundamental)
            .where(Fundamental.kode_saham == symbol_upper)
            .order_by(Fundamental.tanggal.desc())
            .limit(2)
        )
        res_fund = await db.execute(stmt_fund)
        funds = res_fund.scalars().all()
        if len(funds) >= 2 and funds[0].harga_terakhir is not None and funds[1].harga_terakhir is not None:
            price = float(funds[0].harga_terakhir)
            prev_price = float(funds[1].harga_terakhir)
            change = price - prev_price
            pct_change = (change / prev_price) * 100.0 if prev_price > 0 else 0.0
            return round(price, 2), round(change, 2), round(pct_change, 2)
    except Exception as e:
        logger.warning(f"Gagal query DB fundamental untuk {symbol_upper}: {e}")
        
    # Fallback ke yfinance
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_yf_single, symbol_upper)


def fetch_candles_yf(symbol: str, range_val: str) -> list[dict]:
    """
    Mengambil data chart candles menggunakan yfinance (synchronous).
    """
    symbol_upper = symbol.strip().upper()
    ticker_symbol = f"{symbol_upper}.JK"
    
    # Map range to period and interval
    range_map = {
        "1D": ("1d", "5m"),
        "1W": ("5d", "15m"),
        "1M": ("1mo", "1d"),
        "3M": ("3mo", "1d"),
        "YTD": ("ytd", "1d"),
        "1Y": ("1y", "1d"),
        "5Y": ("5y", "1wk"),
    }
    
    period, interval = range_map.get(range_val.upper(), ("1d", "5m"))
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period, interval=interval)
    
    candles = []
    if df.empty:
        return candles
        
    for ts, row in df.iterrows():
        # Pastikan timezone WIB/Asia/Jakarta
        if ts.tzinfo is None:
            jkt_tz = pytz.timezone("Asia/Jakarta")
            ts_aware = jkt_tz.localize(ts)
        else:
            jkt_tz = pytz.timezone("Asia/Jakarta")
            ts_aware = ts.astimezone(jkt_tz)
            
        candles.append({
            "ts": ts_aware.isoformat(),
            "open": float(row["Open"]) if not pd.isna(row["Open"]) else None,
            "high": float(row["High"]) if not pd.isna(row["High"]) else None,
            "low": float(row["Low"]) if not pd.isna(row["Low"]) else None,
            "close": float(row["Close"]),
            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
        })
        
    return candles


@router.get("/stocks")
@router.get("/data/stocks")
async def get_stocks_prices(db: AsyncSession = Depends(get_db_session)):
    """
    Mengambil daftar seluruh saham LQ45 beserta data harga penutupan terakhir,
    nominal perubahan harga, dan persentase perubahan harga.
    Mendahulukan data dari database 'fundamental' (2 tanggal terbaru),
    dan menggunakan yfinance sebagai fallback.
    """
    try:
        # 1. Ambil semua saham
        stmt_saham = select(Saham).order_by(Saham.kode)
        res_saham = await db.execute(stmt_saham)
        saham_list = res_saham.scalars().all()
        
        # 2. Ambil data fundamental terbaru (maks 2 per saham)
        subq = (
            select(
                Fundamental,
                func.row_number().over(
                    partition_by=Fundamental.kode_saham,
                    order_by=Fundamental.tanggal.desc()
                ).label("rn")
            )
        ).subquery()
        
        fund_alias = aliased(Fundamental, subq)
        stmt_funds = select(fund_alias).where(subq.c.rn <= 2)
        res_funds = await db.execute(stmt_funds)
        funds_list = res_funds.scalars().all()
        
        db_funds = defaultdict(list)
        for f in funds_list:
            db_funds[f.kode_saham].append(f)
            
        # 3. Proses masing-masing saham
        results = []
        fallback_symbols = []
        fallback_indexes = []
        
        for idx, s in enumerate(saham_list):
            stock_funds = db_funds[s.kode]
            stock_funds.sort(key=lambda x: x.tanggal, reverse=True)
            
            price, change, pct_change = None, None, None
            if len(stock_funds) >= 2 and stock_funds[0].harga_terakhir is not None and stock_funds[1].harga_terakhir is not None:
                price = float(stock_funds[0].harga_terakhir)
                prev_price = float(stock_funds[1].harga_terakhir)
                change = price - prev_price
                pct_change = (change / prev_price) * 100.0 if prev_price > 0 else 0.0
                price = round(price, 2)
                change = round(change, 2)
                pct_change = round(pct_change, 2)
                
            if price is None:
                fallback_symbols.append(s.kode)
                fallback_indexes.append(idx)
                
            results.append({
                "symbol": s.kode,
                "name": s.nama_perusahaan,
                "price": price,
                "change": change,
                "pct_change": pct_change
            })
            
        # 4. Ambil fallback data secara paralel jika ada
        if fallback_symbols:
            logger.info(f"Mengambil fallback yfinance untuk {len(fallback_symbols)} saham: {fallback_symbols}")
            loop = asyncio.get_running_loop()
            
            tasks = [
                loop.run_in_executor(None, fetch_yf_single, sym)
                for sym in fallback_symbols
            ]
            yf_results = await asyncio.gather(*tasks)
            
            for yf_idx, res in enumerate(yf_results):
                orig_idx = fallback_indexes[yf_idx]
                price, change, pct_change = res
                results[orig_idx]["price"] = price
                results[orig_idx]["change"] = change
                results[orig_idx]["pct_change"] = pct_change
                
        return results
    except Exception as e:
        logger.error(f"Gagal mengambil daftar stocks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil daftar saham beserta harga: {str(e)}"
        )


@router.get("/stocks/{symbol}/candles")
@router.get("/data/stocks/{symbol}/candles")
async def get_stock_candles(
    symbol: str,
    range: str = "1D",
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mengambil data candlestick/history chart untuk saham tertentu.
    Parameter range: 1D, 1W, 1M, 3M, YTD, 1Y, 5Y.
    """
    symbol_upper = symbol.strip().upper()
    range_upper = range.strip().upper()
    
    valid_ranges = {"1D", "1W", "1M", "3M", "YTD", "1Y", "5Y"}
    if range_upper not in valid_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"Range tidak valid. Pilih salah satu dari: {list(valid_ranges)}"
        )
        
    try:
        stmt_saham = select(Saham).where(Saham.kode == symbol_upper)
        res_saham = await db.execute(stmt_saham)
        saham_obj = res_saham.scalar_one_or_none()
        if not saham_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Saham dengan kode '{symbol_upper}' tidak terdaftar."
            )
            
        loop = asyncio.get_running_loop()
        candles = await loop.run_in_executor(None, fetch_candles_yf, symbol_upper, range_upper)
        return candles
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gagal mengambil candles untuk {symbol_upper}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil riwayat harga saham {symbol_upper}: {str(e)}"
        )


@router.get("/stocks/{symbol}")
@router.get("/data/stocks/{symbol}")
async def get_single_stock_price(
    symbol: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mengambil data harga penutupan terakhir, nominal perubahan, dan persentase perubahan
    untuk satu saham tertentu.
    """
    symbol_upper = symbol.strip().upper()
    try:
        # Cek apakah saham terdaftar
        stmt_saham = select(Saham).where(Saham.kode == symbol_upper)
        res_saham = await db.execute(stmt_saham)
        saham_obj = res_saham.scalar_one_or_none()
        if not saham_obj:
            raise HTTPException(
                status_code=404,
                detail=f"Saham dengan kode '{symbol_upper}' tidak terdaftar."
            )
            
        price, change, pct_change = await get_single_stock_price_stats(symbol_upper, db)
        return {
            "symbol": symbol_upper,
            "name": saham_obj.nama_perusahaan,
            "price": price,
            "change": change,
            "pct_change": pct_change
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gagal mengambil harga stock {symbol_upper}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mengambil detail harga saham {symbol_upper}: {str(e)}"
        )
