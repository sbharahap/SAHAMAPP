"""
AI Saham Indonesia — Data Cleaner & Preprocessor

Modul ini berisi fungsi-fungsi untuk membersihkan dan menormalisasi
data mentah dari berbagai collector sebelum disimpan ke database.

Tiga fungsi utama:
    1. normalize_fundamental() : Normalisasi angka dari Yahoo Finance
    2. clean_berita()          : Bersihkan teks berita (HTML, whitespace, dll)
    3. hitung_sentimen_sederhana() : Scoring sentimen berbasis keyword

Penggunaan:
    from backend.data.preprocessors.data_cleaner import (
        normalize_fundamental,
        clean_berita,
        hitung_sentimen_sederhana,
    )

    # Normalisasi data fundamental
    clean_data = normalize_fundamental(raw_data)

    # Bersihkan berita
    clean_news = clean_berita(raw_berita)

    # Hitung sentimen
    skor = hitung_sentimen_sederhana("BBCA cetak laba bersih naik 15%")
    # skor ≈ +0.6 (positif)

Catatan:
    hitung_sentimen_sederhana() adalah PLACEHOLDER sebelum LLM-based
    sentiment analysis diimplementasikan. Akurasinya terbatas karena
    hanya mengandalkan keyword matching tanpa pemahaman konteks.
"""

import math
import re
from typing import Any

from loguru import logger


# ============================================================
# 1. Normalisasi Data Fundamental
# ============================================================

def _parse_numeric(value: Any) -> float | None:
    """
    Konversi berbagai format angka ke float.

    Handle format Indonesia ("Rp 1.234.567,89") dan format standar
    ("1,234,567.89"), serta kasus None, NaN, Infinity.

    Args:
        value: Nilai yang akan dikonversi (bisa str, int, float, None)

    Returns:
        float jika berhasil, None jika tidak valid
    """
    if value is None:
        return None

    # Jika sudah float/int, cek apakah valid
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)

    if not isinstance(value, str):
        return None

    # Bersihkan string
    text = value.strip()
    if not text or text.lower() in ("none", "null", "nan", "n/a", "-", ""):
        return None

    # Hapus simbol mata uang dan whitespace
    text = re.sub(r"[Rr][Pp]\.?\s*", "", text)  # Hapus "Rp", "Rp.", "rp "
    text = re.sub(r"[%$€¥£]", "", text)           # Hapus simbol mata uang/persen
    text = text.strip()

    if not text:
        return None

    # Deteksi format angka:
    # Format Indonesia: 1.234.567,89 (titik sebagai ribuan, koma sebagai desimal)
    # Format standar:   1,234,567.89 (koma sebagai ribuan, titik sebagai desimal)
    try:
        # Hitung jumlah titik dan koma untuk menentukan format
        dot_count = text.count(".")
        comma_count = text.count(",")

        if comma_count == 1 and dot_count >= 1:
            # Kemungkinan format Indonesia: 1.234.567,89
            # Cek apakah koma ada di posisi desimal (dekat akhir)
            comma_pos = text.index(",")
            after_comma = text[comma_pos + 1:]
            if len(after_comma) <= 2:
                # Format Indonesia: hapus titik (ribuan), ganti koma jadi titik
                text = text.replace(".", "").replace(",", ".")
            else:
                # Format standar: hapus koma (ribuan)
                text = text.replace(",", "")

        elif comma_count >= 2:
            # Banyak koma = koma sebagai ribuan (format standar)
            text = text.replace(",", "")

        elif comma_count == 1 and dot_count == 0:
            # Satu koma tanpa titik: bisa desimal Indonesia
            # Cek posisi koma
            comma_pos = text.index(",")
            after_comma = text[comma_pos + 1:]
            if len(after_comma) <= 2:
                # Koma sebagai desimal
                text = text.replace(",", ".")
            else:
                # Koma sebagai ribuan
                text = text.replace(",", "")

        elif dot_count >= 2:
            # Banyak titik = titik sebagai ribuan (format Indonesia)
            text = text.replace(".", "")

        # Hapus karakter non-numerik kecuali titik dan minus
        text = re.sub(r"[^\d.\-+eE]", "", text)

        if not text:
            return None

        result = float(text)
        if math.isnan(result) or math.isinf(result):
            return None

        return result

    except (ValueError, TypeError):
        return None


def normalize_fundamental(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Normalisasi data fundamental mentah ke format bersih untuk database.

    Operasi yang dilakukan:
    - Konversi semua angka ke float (handle format "Rp", ".", ",")
    - Handle None/NaN → None
    - Pastikan kode_saham uppercase
    - Volume dibulatkan ke integer
    - Rasio keuangan dibulatkan ke 2 desimal

    Args:
        raw: Dict data mentah dari fundamental_collector

    Returns:
        Dict data bersih siap simpan ke tabel `fundamental`

    Example:
        >>> raw = {"kode_saham": "bbca", "harga_terakhir": "Rp 9.875", "roe": 18.5}
        >>> normalize_fundamental(raw)
        {"kode_saham": "BBCA", "harga_terakhir": 9875.0, "roe": 18.5, ...}
    """
    logger.debug(f"🔧 Normalisasi fundamental: {raw.get('kode_saham', '?')}")

    # Kolom yang berisi angka dan perlu dinormalisasi
    numeric_fields = [
        "harga_terakhir", "roe", "eps", "pbv", "der",
        "market_cap", "pe_ratio", "dividend_yield",
    ]

    result: dict[str, Any] = {}

    # Salin kolom non-numerik apa adanya
    result["kode_saham"] = raw.get("kode_saham", "").strip().upper()
    result["tanggal"] = raw.get("tanggal")

    # Normalisasi kolom numerik
    for field in numeric_fields:
        value = raw.get(field)
        parsed = _parse_numeric(value)

        # Bulatkan rasio keuangan ke 2 desimal
        if parsed is not None:
            result[field] = round(parsed, 2)
        else:
            result[field] = None

    # Volume: konversi ke integer (tidak ada volume pecahan)
    volume_raw = raw.get("volume")
    volume_parsed = _parse_numeric(volume_raw)
    result["volume"] = int(volume_parsed) if volume_parsed is not None else None

    # Validasi dasar: harga tidak boleh negatif
    if result.get("harga_terakhir") is not None and result["harga_terakhir"] < 0:
        logger.warning(
            f"⚠️  Harga negatif untuk {result['kode_saham']}: "
            f"{result['harga_terakhir']} → diset None"
        )
        result["harga_terakhir"] = None

    return result


# ============================================================
# 2. Cleaning Berita
# ============================================================

# Regex patterns yang di-compile sekali untuk performa
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_HTML_ENTITY_PATTERN = re.compile(r"&[a-zA-Z]+;|&#\d+;")
_MULTI_WHITESPACE_PATTERN = re.compile(r"\s+")
_URL_PATTERN = re.compile(r"https?://\S+")

# Kata-kata umum Bahasa Indonesia untuk deteksi bahasa
_KATA_INDONESIA: frozenset[str] = frozenset({
    "dan", "yang", "di", "dari", "untuk", "dengan", "pada", "ke",
    "ini", "itu", "adalah", "akan", "sudah", "telah", "atau",
    "juga", "tidak", "bisa", "dapat", "oleh", "lebih", "karena",
    "saham", "harga", "naik", "turun", "pasar", "bursa", "emiten",
    "laba", "rugi", "persen", "miliar", "triliun", "rupiah",
    "sementara", "namun", "sedangkan", "sehingga", "meskipun",
    "dalam", "antara", "terhadap", "menjadi", "sebagai", "hingga",
    "tersebut", "terjadi", "mencapai", "meningkat", "menurun",
})


def _hapus_html_tags(teks: str) -> str:
    """Hapus semua HTML tags dari teks."""
    teks = _HTML_TAG_PATTERN.sub(" ", teks)
    teks = _HTML_ENTITY_PATTERN.sub(" ", teks)
    return teks


def _normalisasi_whitespace(teks: str) -> str:
    """Ganti semua whitespace berlebih menjadi satu spasi."""
    return _MULTI_WHITESPACE_PATTERN.sub(" ", teks).strip()


def _deteksi_bahasa(teks: str) -> str:
    """
    Deteksi bahasa teks secara sederhana (ID atau EN).

    Menggunakan metode frekuensi kata umum Bahasa Indonesia.
    Jika ≥ 15% kata dalam teks adalah kata umum Indonesia,
    dianggap Bahasa Indonesia.

    Args:
        teks: Teks yang akan dideteksi bahasanya

    Returns:
        "id" untuk Bahasa Indonesia, "en" untuk Bahasa Inggris
    """
    kata_list = teks.lower().split()
    if not kata_list:
        return "id"  # Default ke Indonesia

    jumlah_kata_id = sum(1 for kata in kata_list if kata in _KATA_INDONESIA)
    rasio = jumlah_kata_id / len(kata_list)

    # Threshold 15% — cukup rendah karena teks berita campuran
    return "id" if rasio >= 0.15 else "en"


def clean_berita(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Bersihkan dan normalisasi data berita mentah.

    Operasi yang dilakukan:
    - Hapus HTML tags dari judul
    - Normalisasi whitespace (tab, newline, spasi ganda)
    - Hapus URL dari judul (kadang RSS menyisipkan URL)
    - Deteksi bahasa (ID/EN)
    - Potong judul jika terlalu panjang (max 500 karakter)

    Args:
        raw: Dict data mentah dari berita_collector

    Returns:
        Dict data bersih dengan tambahan field 'bahasa'

    Example:
        >>> raw = {"judul": "<b>BBCA</b> cetak laba    bersih", ...}
        >>> clean_berita(raw)
        {"judul": "BBCA cetak laba bersih", "bahasa": "id", ...}
    """
    result = dict(raw)  # Shallow copy

    # Bersihkan judul
    judul = result.get("judul", "")
    judul = _hapus_html_tags(judul)
    judul = _URL_PATTERN.sub("", judul)
    judul = _normalisasi_whitespace(judul)

    # Potong jika terlalu panjang
    if len(judul) > 500:
        judul = judul[:497] + "..."

    result["judul"] = judul

    # Bersihkan isi berita jika ada
    isi_berita = result.get("isi_berita")
    if isi_berita:
        isi_berita = _hapus_html_tags(isi_berita)
        isi_berita = _normalisasi_whitespace(isi_berita)
        result["isi_berita"] = isi_berita
    else:
        result["isi_berita"] = None

    # Deteksi bahasa (gunakan isi_berita jika ada agar lebih akurat)
    result["bahasa"] = _deteksi_bahasa(isi_berita or judul)

    # Bersihkan URL (normalisasi)
    url = result.get("url", "").strip()
    result["url"] = url[:1000]  # Sesuai limit model

    # Normalisasi sumber
    sumber = result.get("sumber", "unknown").strip().lower()
    result["sumber"] = sumber

    logger.debug(
        f"🧹 Berita dibersihkan: [{result['bahasa'].upper()}] "
        f"{judul[:80]}{'...' if len(judul) > 80 else ''}"
    )

    return result


# ============================================================
# 3. Sentimen Sederhana Berbasis Keyword
# ============================================================

# Kata-kata positif dalam konteks saham Indonesia
# Bobot: 1 = positif biasa, 2 = sangat positif
_KATA_POSITIF: dict[str, int] = {
    # Pergerakan harga positif
    "naik": 1, "meningkat": 1, "menguat": 1, "melonjak": 2,
    "rally": 2, "bullish": 2, "rebound": 1, "breakout": 2,
    "meroket": 2, "melejit": 2, "menanjak": 1, "terapresiasi": 1,
    "menggembirakan": 2, "melesat": 2, "terdongkrak": 1,

    # Kinerja keuangan positif
    "laba": 1, "untung": 1, "profit": 1, "surplus": 1,
    "pertumbuhan": 1, "growth": 1, "bertumbuh": 1, "tumbuh": 1,
    "melampaui": 1, "melebihi": 1, "mencatatkan": 1,
    "solid": 1, "kuat": 1, "sehat": 1, "efisien": 1,

    # Dividen & return
    "dividen": 1, "dividend": 1, "yield": 1, "buyback": 1,
    "right issue": 1,

    # Rekomendasi positif
    "beli": 1, "buy": 1, "overweight": 1, "outperform": 1,
    "upgrade": 2, "target naik": 2, "prospek cerah": 2,
    "rekomendasi beli": 2, "potensi": 1, "peluang": 1,
    "optimis": 1, "optimistis": 1, "positif": 1,

    # Aksi korporasi positif
    "akuisisi": 1, "ekspansi": 1, "kontrak baru": 2,
    "kerjasama": 1, "partnership": 1, "kolaborasi": 1,
    "inovasi": 1, "transformasi": 1, "diversifikasi": 1,

    # Makroekonomi positif
    "stimulus": 1, "pemulihan": 1, "recovery": 1,
    "stabil": 1, "terkendali": 1, "perbaikan": 1,
}

# Kata-kata negatif dalam konteks saham Indonesia
# Bobot: 1 = negatif biasa, 2 = sangat negatif
_KATA_NEGATIF: dict[str, int] = {
    # Pergerakan harga negatif
    "turun": 1, "melemah": 1, "anjlok": 2, "jatuh": 2,
    "bearish": 2, "koreksi": 1, "tertekan": 1, "terpuruk": 2,
    "terkoreksi": 1, "terdepresiasi": 1, "merosot": 2,
    "ambles": 2, "terjun": 2, "longsor": 2, "tumbang": 2,
    "tergelincir": 1, "melorot": 1,

    # Kinerja keuangan negatif
    "rugi": 2, "merugi": 2, "kerugian": 2, "loss": 2,
    "defisit": 1, "penurunan": 1, "menyusut": 1, "kontraksi": 1,
    "terkontraksi": 1, "menurun": 1, "menciut": 1,
    "membengkak": 1, "overvalued": 1,

    # Risiko & masalah
    "gagal bayar": 2, "default": 2, "bangkrut": 2, "pailit": 2,
    "fraud": 2, "korupsi": 2, "skandal": 2, "investigasi": 1,
    "gugatan": 1, "sengketa": 1, "denda": 1, "sanksi": 1,
    "pelanggaran": 1, "manipulasi": 2, "penipuan": 2,

    # Rekomendasi negatif
    "jual": 1, "sell": 1, "underweight": 1, "underperform": 1,
    "downgrade": 2, "target turun": 2, "waspadai": 1,
    "rekomendasi jual": 2, "hindari": 1, "risiko tinggi": 2,
    "pesimis": 1, "pesimistis": 1, "negatif": 1, "khawatir": 1,

    # Aksi korporasi negatif
    "phk": 2, "restrukturisasi": 1, "delisting": 2,
    "suspensi": 2, "moratorium": 1,

    # Makroekonomi negatif
    "resesi": 2, "inflasi tinggi": 2, "suku bunga naik": 1,
    "pelemahan": 1, "ketidakpastian": 1, "volatilitas": 1,
    "krisis": 2, "gejolak": 1, "tekanan": 1,
}

# Kata penguat (intensifier) yang melipatgandakan skor
_KATA_PENGUAT: frozenset[str] = frozenset({
    "sangat", "amat", "luar biasa", "signifikan", "drastis",
    "tajam", "hebat", "dahsyat", "besar", "masif", "jumbo",
    "tertinggi", "terendah", "rekor", "historis",
})

# Kata negasi yang membalik sentimen
_KATA_NEGASI: frozenset[str] = frozenset({
    "tidak", "bukan", "belum", "tanpa", "gagal", "tak",
    "jangan", "mustahil", "sulit",
})


async def hitung_sentimen_qwen(teks: str) -> float:
    """
    Hitung skor sentimen menggunakan model LLM Qwen dengan metode Multi-Head Attention.

    Heads:
    1. Financial Impact: dampak pada pendapatan/laba emiten.
    2. Market Sentiment: persepsi pelaku pasar/investor.
    3. Macro & Regulatory: pengaruh kondisi makroekonomi/industri/regulasi.
    """
    if not teks or not teks.strip():
        return 0.0

    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import SystemMessage, HumanMessage
        import json
        from backend.config import settings

        llm = ChatOllama(
            model="qwen2.5:3b",
            base_url=settings.ollama_base_url,
            temperature=0.0,
            timeout=30,
        )

        prompt = f"""Tolong lakukan analisis sentimen finansial terhadap berita/teks berikut menggunakan metode Multi-Head Attention.

Teks Berita:
"{teks}"

Instruksi:
Evaluasi teks di atas berdasarkan 3 aspek (Attention Heads) berikut:
1. "financial_impact": Sejauh mana berita berdampak positif atau negatif pada pendapatan, laba, arus kas, atau aset emiten (-1.0 sangat negatif, 1.0 sangat positif).
2. "market_sentiment": Bagaimana berita ini mempengaruhi reputasi emiten dan persepsi psikologis pelaku pasar/investor ritel (-1.0 sangat negatif, 1.0 sangat positif).
3. "macro_industry": Dampak kondisi ekonomi makro, industri, dan regulasi pemerintah terhadap emiten ini (-1.0 sangat negatif, 1.0 sangat positif).

Untuk masing-masing aspek di atas:
- Tentukan skor (score) antara -1.0 dan 1.0.
- Tentukan bobot perhatian (weight) antara 0.0 dan 1.0 yang mencerminkan tingkat kepentingan aspek tersebut dalam berita ini.
- Total semua bobot (weight) harus berjumlah 1.0. Jika total tidak 1.0, tolong normalisasikan.

Format output wajib JSON:
{{
  "financial_impact": {{"score": float, "weight": float}},
  "market_sentiment": {{"score": float, "weight": float}},
  "macro_industry": {{"score": float, "weight": float}}
}}
"""
        messages = [
            SystemMessage(content="Kamu adalah analis sentimen finansial profesional. Jawab hanya dengan format JSON valid."),
            HumanMessage(content=prompt)
        ]

        response = await llm.ainvoke(messages)
        res_text = response.content.strip()

        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].strip()

        data = json.loads(res_text.strip())

        # Hitung weighted score untuk memastikan validitas matematis
        fi = data.get("financial_impact", {})
        ms = data.get("market_sentiment", {})
        mi = data.get("macro_industry", {})

        fi_score = float(fi.get("score", 0.0))
        fi_weight = float(fi.get("weight", 0.0))

        ms_score = float(ms.get("score", 0.0))
        ms_weight = float(ms.get("weight", 0.0))

        mi_score = float(mi.get("score", 0.0))
        mi_weight = float(mi.get("weight", 0.0))

        total_weight = fi_weight + ms_weight + mi_weight
        if total_weight == 0:
            total_weight = 1.0
            fi_weight, ms_weight, mi_weight = 0.33, 0.33, 0.34

        final_score = (
            (fi_score * fi_weight + ms_score * ms_weight + mi_score * mi_weight)
            / total_weight
        )

        logger.info(
            f"🧠 Multi-Head Attention Qwen: FI={fi_score:.2f}(w={fi_weight:.2f}), "
            f"MS={ms_score:.2f}(w={ms_weight:.2f}), MI={mi_score:.2f}(w={mi_weight:.2f}) -> "
            f"Final={final_score:.4f}"
        )
        return round(final_score, 4)

    except Exception as e:
        logger.warning(
            f"⚠️ Gagal menghitung sentimen menggunakan Qwen ({e}). "
            f"Fallback ke sentimen sederhana."
        )
        return hitung_sentimen_sederhana(teks)


def hitung_sentimen_sederhana(teks: str) -> float:
    """
    Hitung skor sentimen teks menggunakan keyword matching sederhana.

    Metode:
    1. Tokenisasi teks menjadi kata-kata
    2. Cocokkan dengan dictionary kata positif dan negatif
    3. Hitung skor berdasarkan bobot kata yang ditemukan
    4. Terapkan modifier (penguat dan negasi)
    5. Normalisasi ke range [-1.0, +1.0]

    PENTING: Ini adalah PLACEHOLDER sebelum LLM-based sentiment.
    Akurasi terbatas karena:
    - Tidak memahami konteks kalimat
    - Tidak menangani sarkasme atau ironi
    - Dictionary terbatas pada kata-kata yang sudah didefinisikan

    Args:
        teks: Teks berita atau komentar yang akan dianalisis

    Returns:
        Skor sentimen: -1.0 (sangat negatif) sampai +1.0 (sangat positif)
        0.0 = netral (tidak ada kata positif/negatif, atau seimbang)

    Example:
        >>> hitung_sentimen_sederhana("BBCA cetak laba bersih naik 15%")
        0.5   # Positif (ada "laba" dan "naik")

        >>> hitung_sentimen_sederhana("Saham GOTO anjlok 10% karena rugi")
        -0.8  # Sangat negatif (ada "anjlok" dan "rugi")

        >>> hitung_sentimen_sederhana("IHSG bergerak sideways")
        0.0   # Netral
    """
    if not teks or not teks.strip():
        return 0.0

    # Preprocessing: lowercase, hapus punctuation kecuali spasi
    teks_clean = teks.lower().strip()
    teks_clean = re.sub(r"[^\w\s]", " ", teks_clean)
    kata_list = teks_clean.split()

    if not kata_list:
        return 0.0

    skor_positif = 0.0
    skor_negatif = 0.0
    jumlah_match = 0

    # Cek frasa multi-kata terlebih dahulu (bigram dan trigram)
    teks_gabung = " ".join(kata_list)

    # Cek frasa multi-kata positif
    for frasa, bobot in _KATA_POSITIF.items():
        if " " in frasa and frasa in teks_gabung:
            skor_positif += bobot
            jumlah_match += 1

    # Cek frasa multi-kata negatif
    for frasa, bobot in _KATA_NEGATIF.items():
        if " " in frasa and frasa in teks_gabung:
            skor_negatif += bobot
            jumlah_match += 1

    # Cek kata tunggal dengan konteks (window-based)
    for i, kata in enumerate(kata_list):
        # Cek apakah kata sebelumnya adalah negasi
        ada_negasi = False
        if i > 0 and kata_list[i - 1] in _KATA_NEGASI:
            ada_negasi = True

        # Cek apakah ada penguat di sekitar kata (window ±2)
        ada_penguat = False
        window_start = max(0, i - 2)
        window_end = min(len(kata_list), i + 3)
        for j in range(window_start, window_end):
            if j != i and kata_list[j] in _KATA_PENGUAT:
                ada_penguat = True
                break

        # Hitung multiplier
        multiplier = 1.5 if ada_penguat else 1.0

        # Cek kata positif (hanya kata tunggal)
        if kata in _KATA_POSITIF and " " not in kata:
            bobot = _KATA_POSITIF[kata] * multiplier
            if ada_negasi:
                # Negasi membalik sentimen: "tidak naik" → negatif
                skor_negatif += bobot * 0.7  # Efek negasi sedikit lebih lemah
            else:
                skor_positif += bobot
            jumlah_match += 1

        # Cek kata negatif (hanya kata tunggal)
        elif kata in _KATA_NEGATIF and " " not in kata:
            bobot = _KATA_NEGATIF[kata] * multiplier
            if ada_negasi:
                # Negasi membalik sentimen: "tidak rugi" → positif
                skor_positif += bobot * 0.7
            else:
                skor_negatif += bobot
            jumlah_match += 1

    # Jika tidak ada keyword yang cocok → netral
    if jumlah_match == 0:
        return 0.0

    # Hitung skor mentah: positif - negatif
    skor_mentah = skor_positif - skor_negatif

    # Normalisasi ke range [-1, 1] menggunakan tanh-like scaling
    # Semakin banyak keyword yang cocok, semakin kuat sinyal sentimen
    # Divisor berdasarkan jumlah match agar proporsional
    divisor = max(skor_positif + skor_negatif, 1.0)
    skor_normal = skor_mentah / divisor

    # Clamp ke [-1.0, 1.0]
    skor_final = max(-1.0, min(1.0, skor_normal))

    logger.debug(
        f"💭 Sentimen: {skor_final:+.2f} "
        f"(pos={skor_positif:.1f}, neg={skor_negatif:.1f}, "
        f"match={jumlah_match}) — {teks[:60]}..."
    )

    return round(skor_final, 4)
