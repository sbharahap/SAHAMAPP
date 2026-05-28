"""
AI Saham Indonesia — Data Collectors Package

Kumpulan scraper untuk mengambil data dari berbagai sumber:
- fundamental_collector : harga & fundamental dari Yahoo Finance
- berita_collector      : berita dari Google News RSS & IDX News
- makro_collector       : data makroekonomi (BI rate, kurs, inflasi)
"""

from backend.data.collectors.berita_collector import collect_berita
from backend.data.collectors.fundamental_collector import collect_fundamental
from backend.data.collectors.makro_collector import collect_makro

__all__ = [
    "collect_fundamental",
    "collect_berita",
    "collect_makro",
]
