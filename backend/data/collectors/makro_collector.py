"""
AI Saham Indonesia — Makro Collector

Mengambil data makroekonomi Indonesia dari berbagai sumber:
- BI Rate: dari halaman publik Bank Indonesia (scraping) + fallback cache
- Kurs USD/IDR: dari Yahoo Finance (ticker USDIDR=X)
- Inflasi: dari halaman publik Bank Indonesia

Data ini digunakan oleh scoring engine untuk komponen makroekonomi (15%).

Penggunaan:
    from backend.data.collectors.makro_collector import collect_makro

    # Ambil semua indikator makro
    data = await collect_makro()

    # Ambil indikator spesifik
    kurs = await collect_kurs_usd_idr()
    bi_rate = await collect_bi_rate()

Catatan:
    - BI tidak menyediakan API publik yang stabil, jadi kita scrape
      halaman web dan menyediakan fallback manual
    - Kurs USD/IDR diambil dari Yahoo Finance (reliable, real-time)
    - Error pada satu indikator TIDAK menghentikan indikator lainnya
"""

import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import yfinance as yf
from bs4 import BeautifulSoup
from loguru import logger

from backend.config import settings

# Timeout untuk HTTP requests (detik)
_HTTP_TIMEOUT = 30.0

# User agent untuk scraping
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Apple Silicon Mac OS X) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Timezone WIB
_WIB = timezone(timedelta(hours=7))


# ============================================================
# Kurs USD/IDR (dari Yahoo Finance)
# ============================================================

async def collect_kurs_usd_idr() -> dict[str, Any] | None:
    """
    Ambil kurs USD/IDR terkini dari Yahoo Finance.

    Menggunakan ticker USDIDR=X yang memberikan data real-time.
    Dijalankan di thread pool karena yfinance bersifat synchronous.

    Returns:
        Dict dengan format model Makro, atau None jika gagal

    Example:
        >>> data = await collect_kurs_usd_idr()
        >>> print(data)
        {
            "tanggal": date(2024, 1, 15),
            "indikator": "kurs_usd_idr",
            "nilai": 15485.0,
            "satuan": "IDR",
            "sumber": "yahoo_finance",
        }
    """
    try:
        logger.debug("💱 Mengambil kurs USD/IDR dari Yahoo Finance...")

        def _fetch_kurs() -> dict[str, Any] | None:
            ticker = yf.Ticker("USDIDR=X")
            info = ticker.info

            # Coba ambil harga dari berbagai field
            kurs = info.get("regularMarketPrice")
            if kurs is None:
                kurs = info.get("previousClose")
            if kurs is None:
                # Fallback: ambil dari history 1 hari terakhir
                try:
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        kurs = float(hist["Close"].iloc[-1])
                except Exception:
                    pass

            if kurs is None:
                return None

            return {
                "tanggal": date.today(),
                "indikator": "kurs_usd_idr",
                "nilai": round(float(kurs), 2),
                "satuan": "IDR",
                "sumber": "yahoo_finance",
            }

        result = await asyncio.to_thread(_fetch_kurs)

        if result:
            logger.info(f"💱 Kurs USD/IDR: Rp {result['nilai']:,.2f}")
        else:
            logger.warning("⚠️  Gagal mendapatkan kurs USD/IDR")

        return result

    except Exception as e:
        logger.error(f"❌ Error ambil kurs USD/IDR: {type(e).__name__}: {e}")
        return None


# ============================================================
# BI Rate (dari scraping halaman Bank Indonesia)
# ============================================================

async def collect_bi_rate() -> dict[str, Any] | None:
    """
    Ambil BI Rate (BI-7 Day Reverse Repo Rate) terkini.

    Strategi pengambilan data (berurutan):
    1. Scrape halaman publik Bank Indonesia
    2. Jika gagal, coba dari halaman data moneter BI
    3. Jika gagal, ambil nilai terbaru yang ada di database PostgreSQL (cache)
    4. Jika semua gagal, return None (caller bisa gunakan cache)

    Returns:
        Dict dengan format model Makro, atau None jika gagal
    """
    logger.debug("🏦 Mengambil BI Rate...")

    # Strategi 1: Scrape halaman suku bunga BI
    result = await _scrape_bi_rate_from_website()
    if result:
        return result

    # Strategi 2: Coba dari halaman data moneter
    result = await _scrape_bi_rate_from_moneter()
    if result:
        return result

    # Strategi 3: Fallback ke cache database
    try:
        logger.info("🏦 Scraping BI Rate gagal. Mencoba mengambil data historis terakhir dari database...")
        from backend.db.postgres import async_session, Makro
        from sqlalchemy import select
        
        async with async_session() as session:
            stmt = (
                select(Makro)
                .where(Makro.indikator == "bi_rate")
                .order_by(Makro.tanggal.desc())
                .limit(1)
            )
            db_res = await session.execute(stmt)
            latest_bi = db_res.scalar_one_or_none()
            if latest_bi:
                logger.info(f"🏦 Menggunakan BI Rate terakhir dari database: {latest_bi.nilai}% (tanggal: {latest_bi.tanggal})")
                return {
                    "tanggal": date.today(),
                    "indikator": "bi_rate",
                    "nilai": latest_bi.nilai,
                    "satuan": latest_bi.satuan,
                    "sumber": "database_cache",
                }
    except Exception as e:
        logger.error(f"❌ Gagal memuat cache BI Rate dari DB: {e}")

    logger.warning(
        "⚠️  Gagal mengambil BI Rate dari semua sumber. "
        "Data mungkin perlu diinput manual atau gunakan cache terakhir."
    )
    return None


async def _scrape_bi_rate_from_website() -> dict[str, Any] | None:
    """
    Scrape BI Rate dari halaman utama Bank Indonesia.

    Halaman BI menampilkan BI-7DRR di bagian statistik.
    Kita parse HTML dan cari angka persentase yang sesuai.
    """
    url = "https://www.bi.go.id/id/statistik/indikator/bi-7day-rr.aspx"

    try:
        async with httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = await asyncio.to_thread(BeautifulSoup, response.text, "html.parser")

        # Cari elemen yang berisi BI-7DRR
        # Struktur halaman BI bisa berubah, jadi kita cari dengan beberapa pola
        # Pola 1: Cari tabel dengan data BI rate
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                for cell in cells:
                    text = cell.get_text(strip=True)
                    # Cari pola angka persentase (contoh: "6.25%", "6,25%")
                    match = re.search(r"(\d{1,2}[.,]\d{1,2})\s*%", text)
                    if match:
                        rate_str = match.group(1).replace(",", ".")
                        rate = float(rate_str)
                        # BI Rate biasanya antara 3% dan 12%
                        if 3.0 <= rate <= 12.0:
                            result = {
                                "tanggal": date.today(),
                                "indikator": "bi_rate",
                                "nilai": rate,
                                "satuan": "persen",
                                "sumber": "bank_indonesia",
                            }
                            logger.info(f"🏦 BI Rate: {rate}%")
                            return result

        # Pola 2: Cari di teks halaman langsung
        page_text = soup.get_text()
        # Cari pola seperti "BI-7DRR ... 6.25%" atau "BI 7-Day ... 5,75%"
        patterns = [
            r"BI[- ]?7[- ]?D(?:ay)?(?:[- ]?R(?:everse)?)?[- ]?R(?:epo)?[- ]?R(?:ate)?\s*[:=]?\s*(\d{1,2}[.,]\d{1,2})\s*%",
            r"suku\s+bunga\s+acuan\s*[:=]?\s*(\d{1,2}[.,]\d{1,2})\s*%",
            r"BI\s*Rate\s*[:=]?\s*(\d{1,2}[.,]\d{1,2})\s*%",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                rate_str = match.group(1).replace(",", ".")
                rate = float(rate_str)
                if 3.0 <= rate <= 12.0:
                    result = {
                        "tanggal": date.today(),
                        "indikator": "bi_rate",
                        "nilai": rate,
                        "satuan": "persen",
                        "sumber": "bank_indonesia",
                    }
                    logger.info(f"🏦 BI Rate (dari teks): {rate}%")
                    return result

        logger.debug("⚠️  BI Rate tidak ditemukan di halaman utama BI")
        return None

    except httpx.TimeoutException:
        logger.warning(f"⏱️  Timeout saat scraping BI Rate dari {url}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"🚫 HTTP {e.response.status_code} dari BI: {url}")
        return None
    except Exception as e:
        logger.error(f"❌ Error scraping BI Rate: {type(e).__name__}: {e}")
        return None


async def _scrape_bi_rate_from_moneter() -> dict[str, Any] | None:
    """
    Fallback: Scrape BI Rate dari halaman data moneter Bank Indonesia.

    Halaman ini biasanya menampilkan data suku bunga dalam tabel
    yang lebih terstruktur.
    """
    url = "https://www.bi.go.id/id/statistik/indikator/data-kurs.aspx"

    try:
        async with httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = await asyncio.to_thread(BeautifulSoup, response.text, "html.parser")

        # Cari semua teks yang mengandung angka persentase dalam konteks BI Rate
        page_text = soup.get_text()
        match = re.search(
            r"(?:BI|suku\s+bunga).*?(\d{1,2}[.,]\d{1,2})\s*%",
            page_text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            rate_str = match.group(1).replace(",", ".")
            rate = float(rate_str)
            if 3.0 <= rate <= 12.0:
                result = {
                    "tanggal": date.today(),
                    "indikator": "bi_rate",
                    "nilai": rate,
                    "satuan": "persen",
                    "sumber": "bank_indonesia",
                }
                logger.info(f"🏦 BI Rate (fallback moneter): {rate}%")
                return result

        return None

    except Exception as e:
        logger.debug(f"⚠️  Fallback BI Rate gagal: {type(e).__name__}: {e}")
        return None


# ============================================================
# Inflasi (dari scraping halaman Bank Indonesia)
# ============================================================

async def collect_inflasi() -> dict[str, Any] | None:
    """
    Ambil data inflasi YoY (Year-on-Year) terkini dari Bank Indonesia.

    Returns:
        Dict dengan format model Makro, atau None jika gagal
    """
    url = "https://www.bi.go.id/id/statistik/indikator/data-inflasi.aspx"

    try:
        logger.debug("📈 Mengambil data inflasi dari Bank Indonesia...")

        async with httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = await asyncio.to_thread(BeautifulSoup, response.text, "html.parser")

        # Cari tabel inflasi — biasanya berisi data bulanan
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                texts = [cell.get_text(strip=True) for cell in cells]

                # Cari baris yang berisi kata "inflasi" dan angka persentase
                row_text = " ".join(texts).lower()
                if "inflasi" in row_text or "yoy" in row_text:
                    for text in texts:
                        match = re.search(r"(\d{1,2}[.,]\d{1,2})", text)
                        if match:
                            inflasi_str = match.group(1).replace(",", ".")
                            inflasi = float(inflasi_str)
                            # Inflasi Indonesia biasanya 1% - 15%
                            if 0.0 <= inflasi <= 15.0:
                                result = {
                                    "tanggal": date.today(),
                                    "indikator": "inflasi_yoy",
                                    "nilai": inflasi,
                                    "satuan": "persen",
                                    "sumber": "bank_indonesia",
                                }
                                logger.info(f"📈 Inflasi YoY: {inflasi}%")
                                return result

        # Fallback: cari di seluruh teks halaman
        page_text = soup.get_text()
        match = re.search(
            r"inflasi.*?(\d{1,2}[.,]\d{1,2})\s*%",
            page_text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            inflasi_str = match.group(1).replace(",", ".")
            inflasi = float(inflasi_str)
            if 0.0 <= inflasi <= 15.0:
                result = {
                    "tanggal": date.today(),
                    "indikator": "inflasi_yoy",
                    "nilai": inflasi,
                    "satuan": "persen",
                    "sumber": "bank_indonesia",
                }
                logger.info(f"📈 Inflasi YoY (teks): {inflasi}%")
                return result

        logger.warning("⚠️  Data inflasi tidak ditemukan di halaman BI")
        return None

    except Exception as e:
        logger.error(f"❌ Error ambil inflasi: {type(e).__name__}: {e}")
        return None


# ============================================================
# IHSG (dari Yahoo Finance)
# ============================================================

async def collect_ihsg() -> dict[str, Any] | None:
    """
    Ambil data IHSG (Indeks Harga Saham Gabungan) dari Yahoo Finance.

    Ticker: ^JKSE (Jakarta Stock Exchange Composite Index)

    Returns:
        Dict dengan format model Makro, atau None jika gagal
    """
    try:
        logger.debug("📊 Mengambil data IHSG dari Yahoo Finance...")

        def _fetch_ihsg() -> dict[str, Any] | None:
            ticker = yf.Ticker("^JKSE")
            info = ticker.info

            ihsg = info.get("regularMarketPrice")
            if ihsg is None:
                ihsg = info.get("previousClose")
            if ihsg is None:
                try:
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        ihsg = float(hist["Close"].iloc[-1])
                except Exception:
                    pass

            if ihsg is None:
                return None

            return {
                "tanggal": date.today(),
                "indikator": "ihsg",
                "nilai": round(float(ihsg), 2),
                "satuan": "poin",
                "sumber": "yahoo_finance",
            }

        result = await asyncio.to_thread(_fetch_ihsg)

        if result:
            logger.info(f"📊 IHSG: {result['nilai']:,.2f} poin")
        else:
            logger.warning("⚠️  Gagal mendapatkan data IHSG")

        return result

    except Exception as e:
        logger.error(f"❌ Error ambil IHSG: {type(e).__name__}: {e}")
        return None


# ============================================================
# Fungsi Utama: Kumpulkan Semua Data Makro
# ============================================================

async def collect_makro() -> list[dict[str, Any]]:
    """
    Ambil semua indikator makroekonomi yang tersedia.

    Mengumpulkan data dari berbagai sumber secara parallel:
    1. Kurs USD/IDR (Yahoo Finance)
    2. BI Rate (Bank Indonesia website)
    3. Inflasi YoY (Bank Indonesia website)
    4. IHSG (Yahoo Finance)

    Error pada satu indikator TIDAK menghentikan pengambilan
    indikator lainnya. Indikator yang gagal akan di-skip.

    Returns:
        List of dict, setiap dict berisi satu indikator makro.
        List bisa kosong jika semua sumber gagal.

    Example:
        >>> data = await collect_makro()
        >>> for d in data:
        ...     print(f"{d['indikator']}: {d['nilai']} {d['satuan']}")
        kurs_usd_idr: 15485.0 IDR
        bi_rate: 6.25 persen
        inflasi_yoy: 3.05 persen
        ihsg: 7245.50 poin
    """
    logger.info("🌍 Mulai mengumpulkan data makroekonomi...")

    # Jalankan semua collector secara parallel dengan asyncio.gather
    # return_exceptions=True agar satu error tidak menghentikan yang lain
    results = await asyncio.gather(
        collect_kurs_usd_idr(),
        collect_bi_rate(),
        collect_inflasi(),
        collect_ihsg(),
        return_exceptions=True,
    )

    # Filter: hanya ambil hasil yang berhasil (bukan None dan bukan Exception)
    makro_data: list[dict[str, Any]] = []
    indikator_names = ["kurs_usd_idr", "bi_rate", "inflasi_yoy", "ihsg"]

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                f"❌ Exception pada {indikator_names[i]}: "
                f"{type(result).__name__}: {result}"
            )
        elif result is not None:
            makro_data.append(result)
        else:
            logger.warning(f"⚠️  {indikator_names[i]}: data tidak tersedia")

    logger.info(
        f"🌍 Selesai mengumpulkan makro: "
        f"{len(makro_data)}/{len(indikator_names)} indikator berhasil"
    )

    # Ringkasan data yang berhasil dikumpulkan
    for data in makro_data:
        logger.info(
            f"   • {data['indikator']}: {data['nilai']} {data['satuan']} "
            f"(sumber: {data['sumber']})"
        )

    return makro_data
