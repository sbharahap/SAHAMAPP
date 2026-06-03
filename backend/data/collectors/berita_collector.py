"""
AI Saham Indonesia — Berita Collector

Mengambil berita terkait saham Indonesia dari berbagai sumber RSS:
- Google News RSS: pencarian per kode emiten + berita pasar umum
- Kontan RSS: berita ekonomi dan pasar modal

Data berita disimpan sebagai metadata di PostgreSQL. Teks lengkap
akan di-embed ke ChromaDB oleh modul terpisah (indexer).

Penggunaan:
    from backend.data.collectors.berita_collector import (
        collect_berita,
        collect_berita_batch,
        collect_berita_pasar,
    )

    # Berita untuk satu saham
    berita = await collect_berita("BBCA", hari_terakhir=7)

    # Berita untuk banyak saham sekaligus
    berita = await collect_berita_batch(["BBCA", "TLKM"], hari_terakhir=7)

    # Berita pasar umum
    berita = await collect_berita_pasar(hari_terakhir=3)

Catatan:
    - Deduplikasi otomatis berdasarkan URL
    - Berita yang lebih tua dari `hari_terakhir` akan difilter
    - Error pada satu sumber TIDAK menghentikan sumber lainnya
"""

import asyncio
from datetime import datetime, timedelta, timezone
import re
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
import feedparser
import httpx
from loguru import logger

from backend.config import settings

# Timezone WIB (UTC+7) untuk parsing tanggal berita Indonesia
_WIB = timezone(timedelta(hours=7))

# Timeout untuk HTTP requests (detik)
_HTTP_TIMEOUT = 30.0

# Delay antar request RSS untuk menghindari rate limiting
_REQUEST_DELAY_SECONDS: float = 2.0

# User agent agar tidak diblokir oleh server
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Apple Silicon Mac OS X) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

async def fetch_article_content(url: str) -> str:
    """
    Mengambil isi berita lengkap secara async dari URL sumber, membersihkan HTML tag,
    dan mengekstrak teks berita utama.
    """
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Bersihkan elemen yang tidak penting
        for element in soup(["script", "style", "nav", "header", "footer", "form", "aside", "iframe", "noscript"]):
            element.decompose()
            
        # Cari div konten berita berdasarkan class/tag umum portal berita Indonesia
        content_div = None
        for selector in [
            "article", 
            ".read__content", 
            ".detail__body-text", 
            ".post-content", 
            ".entry-content", 
            ".post-body",
            ".article-content",
            ".detail-text",
            ".news-content"
        ]:
            content_div = soup.select_one(selector)
            if content_div:
                break
                
        if content_div:
            paragraphs = content_div.find_all("p")
        else:
            paragraphs = soup.find_all("p")
            
        text_parts = []
        for p in paragraphs:
            text = p.get_text().strip()
            # Filter baris/paragraf boilerplate umum
            if len(text) > 30 and not any(skip in text.lower() for skip in [
                "baca juga:", "download aplikasi", "simak breaking news", "follow instagram", "klik di sini",
                "halaman selanjutnya", "selengkapnya di"
            ]):
                text_parts.append(text)
                
        content = "\n\n".join(text_parts)
        return content[:10000].strip()  # Batasi max 10.000 karakter
    except Exception as e:
        logger.warning(f"⚠️ Gagal mengambil isi berita dari {url}: {e}")
        return ""

def is_news_relevant(title: str, content: str = "") -> bool:
    """
    Reranking/filtering berita untuk menyaring berita tidak relevan (promo, diskon, dll).
    Mengembalikan True jika berita dinilai relevan dengan investasi/emiten/pasar modal.
    """
    title_lower = title.lower()
    content_lower = content.lower()
    
    # Kata kunci penanda berita spam, gaya hidup, atau non-investasi (negatif/noise filter)
    noise_keywords = [
        "promo", "diskon", "voucher", "katalog belanja", "undian", 
        "mudik", "lebaran", "ramadan", "ramadhan", "giveaway", 
        "csr", "donasi", "bantuan sosial", "bansos", "beasiswa",
        "lowongan kerja", "loker", "magang", "rekrutmen", "karir",
        "olahraga", "sepak bola", "klasemen", "skor liga", "resep", 
        "kuliner", "makanan", "wisata", "liburan", "traveling", 
        "konser", "festival", "film", "sinopsis", "drama", "artis", 
        "gosip", "bencana alam", "gempa", "kecelakaan maut", "kebakaran",
        "tawuran", "kriminal", "pembunuhan", "perampokan", "mudik gratis",
        "tips diet", "kecantikan", "makeup", "fashion", "zodiak"
    ]
    
    for kw in noise_keywords:
        if kw in title_lower:
            return False
            
    # Kata kunci penanda berita finansial/investasi (positif filter)
    finance_keywords = [
        "saham", "emiten", "laba", "rugi", "rupiah", "dolar", "investasi", 
        "ihsg", "bursa", "idx", "bei", "ipo", "rups", "dividen", "obligasi", 
        "reksadana", "sukuk", "gdp", "bi rate", "inflasi", "suku bunga", 
        "fomc", "fed", "keuangan", "akuisisi", "merger", "kinerja", 
        "kuartal", "q1", "q2", "q3", "q4", "fy", "semester", "revenue",
        "pendapatan", "omzet", "ekspansi", "utang", "obligasi", "korporasi",
        "harga saham", "rebound", "bullish", "bearish", "sideways", "kapitalisasi"
    ]
    
    has_finance = any(kw in title_lower for kw in finance_keywords) or \
                  (content_lower and any(kw in content_lower for kw in finance_keywords))
                  
    return has_finance


def _parse_published_date(entry: dict[str, Any]) -> datetime | None:
    """
    Parse tanggal publish dari entry RSS feed.

    RSS feeds menggunakan berbagai format tanggal. feedparser
    menormalisasi ke struct_time di field `published_parsed`,
    tapi kadang field ini tidak tersedia.

    Args:
        entry: Satu entry dari feedparser

    Returns:
        datetime dengan timezone, atau None jika gagal parse
    """
    # Coba dari published_parsed (sudah di-parse oleh feedparser)
    parsed = entry.get("published_parsed")
    if parsed:
        try:
            dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            pass

    # Coba dari updated_parsed sebagai fallback
    updated = entry.get("updated_parsed")
    if updated:
        try:
            dt = datetime(*updated[:6], tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            pass

    # Fallback: gunakan waktu sekarang
    logger.debug(
        f"⚠️  Tidak bisa parse tanggal untuk: {entry.get('title', 'unknown')}"
    )
    return None


def _normalize_berita_entry(
    entry: dict[str, Any],
    kode_saham: str | None,
    sumber: str,
) -> dict[str, Any] | None:
    """
    Normalisasi satu entry RSS menjadi format dict yang sesuai model Berita.

    Args:
        entry: Satu entry dari feedparser
        kode_saham: Kode saham terkait (None untuk berita pasar umum)
        sumber: Nama sumber berita

    Returns:
        Dict siap simpan ke PostgreSQL, atau None jika data tidak valid
    """
    judul = entry.get("title", "").strip()
    url = entry.get("link", "").strip()

    # Validasi minimal: judul dan URL harus ada
    if not judul or not url:
        return None

    tanggal_publish = _parse_published_date(entry)
    if tanggal_publish is None:
        return None

    return {
        "kode_saham": kode_saham,
        "judul": judul[:500],  # Batasi panjang judul sesuai model (VARCHAR 500)
        "url": url[:1000],     # Batasi panjang URL sesuai model (VARCHAR 1000)
        "sumber": sumber,
        "tanggal_publish": tanggal_publish,
        "skor_sentimen": None,        # Akan diisi oleh sentiment analyzer
        "sudah_diembedding": False,   # Belum di-embed ke ChromaDB
    }


async def _fetch_rss_feed(url: str) -> list[dict[str, Any]]:
    """
    Fetch dan parse RSS feed dari URL menggunakan httpx (async) + feedparser.

    Args:
        url: URL RSS feed

    Returns:
        List of entries dari RSS feed (bisa kosong jika gagal)
    """
    try:
        async with httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        # Bersihkan karakter ampersand yang tidak valid (&) agar XML feedparser tidak error
        import re
        cleaned_text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#[0-9]+;)', '&amp;', response.text)

        # feedparser bisa parse string XML langsung
        feed = await asyncio.to_thread(feedparser.parse, cleaned_text)

        if feed.bozo and not feed.entries:
            # bozo = feed tidak valid, tapi kadang masih punya entries
            logger.warning(
                f"⚠️  RSS feed mungkin tidak valid: {url} "
                f"(bozo_exception: {feed.get('bozo_exception', 'unknown')})"
            )
            return []

        logger.debug(f"📰 Ditemukan {len(feed.entries)} entries dari {url}")
        return feed.entries

    except httpx.TimeoutException:
        logger.error(f"⏱️  Timeout saat mengambil RSS: {url}")
        return []
    except httpx.HTTPStatusError as e:
        logger.error(f"🚫 HTTP {e.response.status_code} dari RSS: {url}")
        return []
    except Exception as e:
        logger.error(f"❌ Gagal fetch RSS {url}: {type(e).__name__}: {e}")
        return []


async def _collect_from_google_news(
    kode_saham: str | None,
    query: str,
    hari_terakhir: int,
) -> list[dict[str, Any]]:
    """
    Ambil berita dari Google News RSS berdasarkan query pencarian.

    Args:
        kode_saham: Kode saham terkait (atau None untuk berita umum)
        query: Query pencarian Google News
        hari_terakhir: Hanya ambil berita dalam N hari terakhir

    Returns:
        List of dict berita yang sudah dinormalisasi
    """
    # Encode query untuk URL
    encoded_query = quote_plus(query)
    url = (
        f"https://news.google.com/rss/search"
        f"?q={encoded_query}+when:{hari_terakhir}d"
        f"&hl=id&gl=ID&ceid=ID:id"
    )

    logger.debug(f"🔍 Google News query: '{query}' ({hari_terakhir} hari)")

    entries = await _fetch_rss_feed(url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=hari_terakhir)

    results: list[dict[str, Any]] = []
    for entry in entries:
        berita = _normalize_berita_entry(entry, kode_saham, "google_news")
        if berita is None:
            continue

        # Filter: hanya berita dalam rentang waktu yang diminta
        if berita["tanggal_publish"] < cutoff:
            continue

        results.append(berita)

    return results


async def _collect_from_kontan(
    hari_terakhir: int,
) -> list[dict[str, Any]]:
    """
    Ambil berita dari Kontan RSS feed.

    Kontan adalah salah satu portal berita ekonomi terbesar di Indonesia.
    Feed RSS-nya berisi berita pasar modal, makroekonomi, dan emiten.

    Args:
        hari_terakhir: Hanya ambil berita dalam N hari terakhir

    Returns:
        List of dict berita yang sudah dinormalisasi
    """
    logger.debug(f"📰 Mengambil berita dari Kontan RSS...")

    entries = await _fetch_rss_feed(settings.kontan_rss_url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=hari_terakhir)

    results: list[dict[str, Any]] = []
    for entry in entries:
        # Berita Kontan bersifat umum, kode_saham = None
        berita = _normalize_berita_entry(entry, None, "kontan")
        if berita is None:
            continue

        if berita["tanggal_publish"] < cutoff:
            continue

        results.append(berita)

    return results


def _deduplikasi_berita(berita_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Hapus berita duplikat berdasarkan URL.

    Berita dari berbagai sumber bisa memiliki URL yang sama
    (misalnya Google News mengarahkan ke Kontan). Fungsi ini
    memastikan setiap URL hanya muncul sekali.

    Args:
        berita_list: List berita yang mungkin mengandung duplikat

    Returns:
        List berita tanpa duplikat (URL pertama yang muncul dipertahankan)
    """
    seen_urls: set[str] = set()
    unique: list[dict[str, Any]] = []

    for berita in berita_list:
        url = berita["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique.append(berita)

    jumlah_duplikat = len(berita_list) - len(unique)
    if jumlah_duplikat > 0:
        logger.info(f"🔄 Dihapus {jumlah_duplikat} berita duplikat (berdasarkan URL)")

    return unique


async def collect_berita(
    kode_saham: str,
    hari_terakhir: int = 7,
) -> list[dict[str, Any]]:
    """
    Ambil berita terkait satu saham dari semua sumber RSS.

    Mencari berita dari Google News dengan query spesifik per emiten,
    lalu menggabungkan dan mendeduplikasi hasilnya.

    Args:
        kode_saham: Kode saham IDX (contoh: "BBCA")
        hari_terakhir: Hanya ambil berita dalam N hari terakhir (default: 7)

    Returns:
        List of dict berita yang sudah dinormalisasi dan dideduplikasi

    Example:
        >>> berita = await collect_berita("BBCA", hari_terakhir=7)
        >>> print(berita[0])
        {
            "kode_saham": "BBCA",
            "judul": "BBCA Cetak Laba Bersih Rp 10 Triliun di Q1 2024",
            "url": "https://...",
            "sumber": "google_news",
            "tanggal_publish": datetime(...),
            "skor_sentimen": None,
            "sudah_diembedding": False,
        }
    """
    kode = kode_saham.strip().upper()
    logger.info(f"📰 Mengumpulkan berita untuk {kode} ({hari_terakhir} hari)...")

    all_berita: list[dict[str, Any]] = []

    # Sumber 1: Google News — query spesifik per emiten
    # Menggunakan beberapa variasi query untuk coverage yang lebih baik
    queries = [
        f"saham {kode} IDX",
        f"{kode} emiten bursa",
    ]

    for query in queries:
        try:
            berita = await _collect_from_google_news(kode, query, hari_terakhir)
            all_berita.extend(berita)
        except Exception as e:
            logger.error(
                f"❌ Gagal ambil Google News untuk query '{query}': "
                f"{type(e).__name__}: {e}"
            )

        # Delay antar query
        await asyncio.sleep(_REQUEST_DELAY_SECONDS)

    # Deduplikasi
    unique_berita = _deduplikasi_berita(all_berita)

    # Batasi ke top 8 berita terbaru untuk menghindari rate limit saat mengambil isi penuh
    unique_berita = unique_berita[:8]

    relevant_berita: list[dict[str, Any]] = []
    for berita in unique_berita:
        title = berita["judul"]
        if is_news_relevant(title):
            url = berita["url"]
            logger.info(f"📰 Mengambil isi berita: {title[:50]}...")
            content = await fetch_article_content(url)
            
            # Verifikasi lagi relevansi dengan isi berita
            if is_news_relevant(title, content):
                berita["isi_berita"] = content
                relevant_berita.append(berita)
            else:
                logger.info(f"🗑️ Membuang berita tidak relevan setelah cek isi: {title[:50]}")
            
            # Delay kecil agar sopan ke server news
            await asyncio.sleep(1.0)
        else:
            logger.info(f"🗑️ Membuang berita tidak relevan berdasarkan judul: {title[:50]}")

    logger.info(
        f"📰 {kode}: ditemukan {len(relevant_berita)} berita relevan dari {len(unique_berita)} total unik"
    )

    return relevant_berita


async def collect_berita_batch(
    kode_saham_list: list[str],
    hari_terakhir: int = 7,
) -> list[dict[str, Any]]:
    """
    Ambil berita untuk banyak saham sekaligus.

    Proses berjalan sequential per saham dengan delay antar request
    untuk menghindari rate limiting.

    Args:
        kode_saham_list: List kode saham (contoh: ["BBCA", "TLKM", "ASII"])
        hari_terakhir: Hanya ambil berita dalam N hari terakhir

    Returns:
        List gabungan berita dari semua saham (sudah dideduplikasi)
    """
    logger.info(
        f"📰 Batch berita: {len(kode_saham_list)} saham, "
        f"{hari_terakhir} hari terakhir"
    )

    all_berita: list[dict[str, Any]] = []

    for i, kode in enumerate(kode_saham_list):
        try:
            berita = await collect_berita(kode, hari_terakhir)
            all_berita.extend(berita)
        except Exception as e:
            logger.error(
                f"❌ Gagal batch berita untuk {kode}: "
                f"{type(e).__name__}: {e}"
            )

        # Delay antar saham (kecuali yang terakhir)
        if i < len(kode_saham_list) - 1:
            await asyncio.sleep(_REQUEST_DELAY_SECONDS)

    # Deduplikasi final (berita tentang satu emiten bisa muncul di query lain)
    unique_berita = _deduplikasi_berita(all_berita)

    logger.info(
        f"📰 Batch selesai: {len(unique_berita)} berita unik "
        f"untuk {len(kode_saham_list)} saham"
    )

    return unique_berita


async def collect_berita_pasar(
    hari_terakhir: int = 3,
) -> list[dict[str, Any]]:
    """
    Ambil berita pasar modal umum (tidak spesifik ke satu saham).

    Mengambil dari Google News (query umum) dan Kontan RSS.
    Berita ini berguna untuk analisis sentimen pasar secara keseluruhan.

    Args:
        hari_terakhir: Hanya ambil berita dalam N hari terakhir (default: 3)

    Returns:
        List of dict berita pasar umum (kode_saham = None)
    """
    logger.info(f"🌐 Mengumpulkan berita pasar umum ({hari_terakhir} hari)...")

    all_berita: list[dict[str, Any]] = []

    # Sumber 1: Google News — berita pasar umum
    queries_pasar = [
        "IHSG bursa efek indonesia",
        "pasar modal indonesia saham",
    ]

    for query in queries_pasar:
        try:
            berita = await _collect_from_google_news(None, query, hari_terakhir)
            all_berita.extend(berita)
        except Exception as e:
            logger.error(f"❌ Gagal Google News pasar '{query}': {e}")

        await asyncio.sleep(_REQUEST_DELAY_SECONDS)

    # Sumber 2: Kontan RSS — berita ekonomi
    try:
        berita_kontan = await _collect_from_kontan(hari_terakhir)
        all_berita.extend(berita_kontan)
    except Exception as e:
        logger.error(f"❌ Gagal ambil Kontan RSS: {e}")

    # Deduplikasi
    unique_berita = _deduplikasi_berita(all_berita)

    # Batasi ke top 8 berita terbaru
    unique_berita = unique_berita[:8]

    relevant_berita: list[dict[str, Any]] = []
    for berita in unique_berita:
        title = berita["judul"]
        if is_news_relevant(title):
            url = berita["url"]
            logger.info(f"🌐 Mengambil isi berita pasar: {title[:50]}...")
            content = await fetch_article_content(url)
            
            # Verifikasi lagi relevansi dengan isi berita
            if is_news_relevant(title, content):
                berita["isi_berita"] = content
                relevant_berita.append(berita)
            else:
                logger.info(f"🗑️ Membuang berita pasar tidak relevan setelah cek isi: {title[:50]}")
            
            # Delay kecil agar sopan ke server news
            await asyncio.sleep(1.0)
        else:
            logger.info(f"🗑️ Membuang berita pasar tidak relevan berdasarkan judul: {title[:50]}")

    logger.info(
        f"🌐 Berita pasar: ditemukan {len(relevant_berita)} berita relevan dari {len(unique_berita)} total unik"
    )

    return relevant_berita
