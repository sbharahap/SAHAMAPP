"""
AI Saham Indonesia — Data Preprocessors Package

Modul preprocessing untuk membersihkan dan mempersiapkan data
sebelum disimpan ke database atau diproses oleh model AI:
- data_cleaner : normalisasi fundamental, cleaning berita, sentimen keyword
- embedder     : BGE-M3 embedding untuk teks (singleton, efisien RAM)
"""

from backend.data.preprocessors.data_cleaner import (
    clean_berita,
    hitung_sentimen_sederhana,
    hitung_sentimen_qwen,
    normalize_fundamental,
)
from backend.data.preprocessors.embedder import (
    embed_batch,
    embed_dokumen,
    get_embedder,
)

__all__ = [
    "normalize_fundamental",
    "clean_berita",
    "hitung_sentimen_sederhana",
    "hitung_sentimen_qwen",
    "embed_dokumen",
    "embed_batch",
    "get_embedder",
]
