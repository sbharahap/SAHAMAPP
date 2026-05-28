"""
AI Saham Indonesia — Fundamental Collector

Mengambil data harga dan fundamental saham dari Yahoo Finance menggunakan
library yfinance. Karena yfinance bersifat synchronous, semua panggilan
dijalankan di thread pool agar tidak memblokir event loop async.

Data yang dikumpulkan per saham:
    - Harga penutupan terakhir & volume
    - ROE, EPS, PBV, DER, Market Cap, PE Ratio, Dividend Yield

Penggunaan:
    from backend.data.collectors.fundamental_collector import collect_fundamental

    # Ambil data untuk beberapa saham
    results = await collect_fundamental(["BBCA", "TLKM", "ASII"])

    # Ambil data untuk satu saham
    results = await collect_fundamental(["BBCA"])

Catatan:
    - Yahoo Finance menggunakan format ticker "BBCA.JK" untuk saham IDX
    - Rate limiting diterapkan (delay antar request) untuk menghindari ban
    - Error pada satu saham TIDAK menghentikan proses saham lainnya
"""

import asyncio
from datetime import date, datetime
from typing import Any

import yfinance as yf
from loguru import logger

from backend.config import settings

# Delay antar request ke Yahoo Finance (dalam detik)
# Terlalu cepat bisa menyebabkan rate limiting / IP ban
_REQUEST_DELAY_SECONDS: float = 1.5


def _extract_info_value(info: dict[str, Any], key: str) -> float | None:
    """
    Ambil nilai dari dict info yfinance dengan aman.

    Yahoo Finance kadang mengembalikan 'None', 'Infinity', atau NaN
    untuk beberapa field. Fungsi ini menangani semua kasus tersebut.

    Args:
        info: Dictionary info dari yfinance Ticker
        key: Nama field yang ingin diambil

    Returns:
        Nilai float jika valid, None jika tidak tersedia atau invalid
    """
    value = info.get(key)

    if value is None:
        return None

    try:
        result = float(value)
        # Cek apakah nilai valid (bukan NaN atau Infinity)
        if result != result or result == float("inf") or result == float("-inf"):
            return None
        return result
    except (ValueError, TypeError):
        return None


def _fetch_single_stock(kode_saham: str) -> dict[str, Any] | None:
    """
    Ambil data fundamental satu saham dari Yahoo Finance (synchronous).

    Fungsi ini berjalan di thread pool via asyncio.to_thread() agar
    tidak memblokir event loop. Jangan panggil langsung dari kode async.

    Args:
        kode_saham: Kode saham IDX tanpa suffix (contoh: "BBCA")

    Returns:
        Dictionary data fundamental, atau None jika gagal
    """
    # Format ticker untuk Yahoo Finance: BBCA -> BBCA.JK
    ticker_symbol = f"{kode_saham}{settings.yfinance_market_suffix}"

    try:
        logger.debug(f"📊 Mengambil data fundamental: {ticker_symbol}")

        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Validasi: pastikan data yang dikembalikan valid
        # Yahoo Finance kadang mengembalikan dict kosong atau hanya metadata
        if not info or info.get("regularMarketPrice") is None:
            # Fallback: coba ambil dari fast_info jika info kosong
            try:
                fast = ticker.fast_info
                harga = float(fast.get("lastPrice", 0)) or None
                volume = int(fast.get("lastVolume", 0)) or None
                market_cap_val = float(fast.get("marketCap", 0)) or None
            except Exception:
                logger.warning(
                    f"⚠️  Data tidak tersedia untuk {ticker_symbol}, "
                    f"kemungkinan ticker salah atau delisted"
                )
                return None

            # Minimal return harga dan volume dari fast_info
            return {
                "kode_saham": kode_saham,
                "tanggal": date.today(),
                "harga_terakhir": harga,
                "volume": volume,
                "roe": None,
                "eps": None,
                "pbv": None,
                "der": None,
                "market_cap": (
                    market_cap_val / 1_000_000_000 if market_cap_val else None
                ),
                "pe_ratio": None,
                "dividend_yield": None,
            }

        # Ekstrak data harga
        harga_terakhir = _extract_info_value(info, "regularMarketPrice")
        if harga_terakhir is None:
            harga_terakhir = _extract_info_value(info, "currentPrice")

        volume_raw = _extract_info_value(info, "regularMarketVolume")
        volume = int(volume_raw) if volume_raw is not None else None

        # Ekstrak rasio fundamental
        roe = _extract_info_value(info, "returnOnEquity")
        eps = _extract_info_value(info, "trailingEps")
        pbv = _extract_info_value(info, "priceToBook")
        pe_ratio = _extract_info_value(info, "trailingPE")
        dividend_yield = _extract_info_value(info, "dividendYield")

        # Market cap dalam miliar IDR
        market_cap_raw = _extract_info_value(info, "marketCap")
        market_cap = market_cap_raw / 1_000_000_000 if market_cap_raw else None

        # DER (Debt to Equity Ratio) — Yahoo Finance menyimpan sebagai debtToEquity
        # yang sudah dalam bentuk persentase (x100), jadi kita bagi 100
        der_raw = _extract_info_value(info, "debtToEquity")
        der = der_raw / 100.0 if der_raw is not None else None

        # ROE dari Yahoo Finance sudah dalam bentuk desimal (0.15 = 15%)
        # Kita simpan dalam persen agar konsisten
        if roe is not None:
            roe = roe * 100.0

        # Dividend yield juga dalam desimal, konversi ke persen
        if dividend_yield is not None:
            dividend_yield = dividend_yield * 100.0

        result = {
            "kode_saham": kode_saham,
            "tanggal": date.today(),
            "harga_terakhir": harga_terakhir,
            "volume": volume,
            "roe": round(roe, 2) if roe is not None else None,
            "eps": round(eps, 2) if eps is not None else None,
            "pbv": round(pbv, 2) if pbv is not None else None,
            "der": round(der, 2) if der is not None else None,
            "market_cap": round(market_cap, 2) if market_cap is not None else None,
            "pe_ratio": round(pe_ratio, 2) if pe_ratio is not None else None,
            "dividend_yield": (
                round(dividend_yield, 2) if dividend_yield is not None else None
            ),
        }

        logger.info(
            f"✅ {kode_saham}: Harga={harga_terakhir}, "
            f"ROE={result['roe']}%, PBV={result['pbv']}x, "
            f"DER={result['der']}x"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Gagal ambil data {ticker_symbol}: {type(e).__name__}: {e}")
        return None


async def collect_fundamental(
    kode_saham_list: list[str],
    delay: float = _REQUEST_DELAY_SECONDS,
) -> list[dict[str, Any]]:
    """
    Ambil data fundamental untuk sekumpulan saham IDX dari Yahoo Finance.

    Proses berjalan secara sequential (bukan parallel) dengan delay antar
    request untuk menghindari rate limiting dari Yahoo Finance.

    Args:
        kode_saham_list: List kode saham tanpa suffix (contoh: ["BBCA", "TLKM"])
        delay: Delay antar request dalam detik (default: 1.5s)

    Returns:
        List of dict, setiap dict berisi data fundamental satu saham.
        Saham yang gagal diambil datanya akan di-skip (tidak termasuk dalam list).

    Example:
        >>> results = await collect_fundamental(["BBCA", "TLKM", "ASII"])
        >>> print(results[0])
        {
            "kode_saham": "BBCA",
            "tanggal": date(2024, 1, 15),
            "harga_terakhir": 9875.0,
            "volume": 15234000,
            "roe": 18.5,
            "eps": 1234.0,
            ...
        }
    """
    logger.info(
        f"📊 Mulai mengumpulkan data fundamental "
        f"untuk {len(kode_saham_list)} saham..."
    )

    results: list[dict[str, Any]] = []
    berhasil = 0
    gagal = 0

    for i, kode in enumerate(kode_saham_list):
        # Normalisasi kode saham: uppercase, strip whitespace
        kode_clean = kode.strip().upper()

        # Jalankan fungsi sync di thread pool agar tidak blokir event loop
        try:
            data = await asyncio.to_thread(_fetch_single_stock, kode_clean)

            if data is not None:
                results.append(data)
                berhasil += 1
            else:
                gagal += 1

        except Exception as e:
            logger.error(
                f"❌ Exception tak terduga untuk {kode_clean}: "
                f"{type(e).__name__}: {e}"
            )
            gagal += 1

        # Rate limiting: delay antar request (kecuali untuk saham terakhir)
        if i < len(kode_saham_list) - 1:
            logger.debug(f"⏳ Delay {delay}s sebelum request berikutnya...")
            await asyncio.sleep(delay)

    logger.info(
        f"📊 Selesai mengumpulkan fundamental: "
        f"✅ {berhasil} berhasil, ❌ {gagal} gagal, "
        f"dari total {len(kode_saham_list)} saham"
    )

    return results


async def collect_fundamental_batch(
    kode_saham_list: list[str],
    batch_size: int = 10,
    delay_antar_batch: float = 5.0,
) -> list[dict[str, Any]]:
    """
    Versi batch dari collect_fundamental untuk jumlah saham yang banyak.

    Membagi list saham menjadi batch-batch kecil untuk menghindari
    timeout dan rate limiting saat mengambil data ratusan saham.

    Args:
        kode_saham_list: List kode saham
        batch_size: Jumlah saham per batch (default: 10)
        delay_antar_batch: Delay antar batch dalam detik (default: 5.0s)

    Returns:
        List gabungan dari semua batch
    """
    logger.info(
        f"📦 Batch collection: {len(kode_saham_list)} saham, "
        f"batch_size={batch_size}"
    )

    all_results: list[dict[str, Any]] = []

    # Bagi list menjadi batch
    for batch_num in range(0, len(kode_saham_list), batch_size):
        batch = kode_saham_list[batch_num : batch_num + batch_size]
        batch_index = batch_num // batch_size + 1
        total_batches = (len(kode_saham_list) + batch_size - 1) // batch_size

        logger.info(
            f"📦 Batch {batch_index}/{total_batches}: "
            f"memproses {len(batch)} saham ({batch[0]}...{batch[-1]})"
        )

        batch_results = await collect_fundamental(batch)
        all_results.extend(batch_results)

        # Delay antar batch (kecuali batch terakhir)
        if batch_num + batch_size < len(kode_saham_list):
            logger.info(f"⏳ Delay {delay_antar_batch}s antar batch...")
            await asyncio.sleep(delay_antar_batch)

    logger.info(
        f"📦 Batch collection selesai: "
        f"total {len(all_results)} data berhasil dikumpulkan"
    )

    return all_results
