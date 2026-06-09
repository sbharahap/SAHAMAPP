"""
AI Saham Indonesia — Unit Tests untuk Scoring Engine

Tes untuk memvalidasi:
1. Logika penyesuaian bobot adaptif saat musim laporan keuangan baru rilis.
2. Total bobot scoring selalu berjumlah 1.0 (100%).
3. Saham dengan tingkat utang (DER) tinggi menghasilkan skor risiko rendah (berisiko tinggi).
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.scoring_agent import (
    _skor_risiko,
    _skor_fundamental,
    analisis_kondisi_pasar,
    ScoringState,
)
from backend.config import settings


class TestScoringEngine(unittest.TestCase):
    """
    Kumpulan test case untuk menguji logika kalkulasi skor dan bobot adaptif.
    """

    def test_total_bobot_default(self):
        """
        Memastikan total bobot scoring default dari konfigurasi (.env/settings)
        selalu berjumlah 1.0 (100%).
        """
        weights = settings.default_scoring_weights
        total_weight = sum(weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)

    def test_skor_risiko_der_tinggi(self):
        """
        Memastikan saham dengan Debt to Equity Ratio (DER) sangat tinggi
        akan mendapatkan skor risiko yang RENDAH (skor rendah = berisiko tinggi).
        """
        # Case 1: DER aman (misal 0.4)
        data_aman = {"der": 0.4}
        skor_aman = _skor_risiko(data_aman, volume=1_000_000, ada_berita_negatif_besar=False)

        # Case 2: DER sangat tinggi (misal 4.0)
        data_berbahaya = {"der": 4.0}
        skor_berbahaya = _skor_risiko(data_berbahaya, volume=1_000_000, ada_berita_negatif_besar=False)

        # Case 3: DER sangat tinggi + ada berita negatif besar + volume tipis (tidak likuid)
        data_kritis = {"der": 3.5}
        skor_kritis = _skor_risiko(data_kritis, volume=50_000, ada_berita_negatif_besar=True)

        logger_msg = (
            f"Skor Aman (DER 0.4): {skor_aman} | "
            f"Skor Berbahaya (DER 4.0): {skor_berbahaya} | "
            f"Skor Kritis: {skor_kritis}"
        )
        print(logger_msg)

        # Skor aman harus lebih tinggi dari skor berbahaya
        self.assertTrue(skor_aman > skor_berbahaya)
        # Skor kritis harus sangat rendah karena menumpuk banyak faktor risiko
        self.assertTrue(skor_kritis < 30.0)

    @patch("backend.agents.scoring_agent.async_session")
    async def test_bobot_adaptif_musim_lapkeu_async(self, mock_session_cls):
        """
        Menguji secara asinkron bahwa logika bobot adaptif mendeteksi adanya
        laporan keuangan baru dan menaikkan bobot fundamental menjadi 40%.
        """
        # Mock session & database execution untuk menghitung berita laporan keuangan
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_cls.return_value = mock_session

        # Mock data makro agar tidak kosong (menghindari error kritis Kasus 4)
        from backend.db.postgres import Makro
        from datetime import date

        mock_bi_rate = Makro(indikator="bi_rate", nilai=6.0, tanggal=date.today(), satuan="%")
        mock_kurs = Makro(indikator="kurs_usd_idr", nilai=15500.0, tanggal=date.today(), satuan="IDR")
        mock_ihsg = Makro(indikator="ihsg", nilai=7200.0, tanggal=date.today(), satuan="pts")
        mock_inflasi = Makro(indikator="inflasi_yoy", nilai=3.0, tanggal=date.today(), satuan="%")

        mock_result_bi = MagicMock()
        mock_result_bi.scalars.return_value.all.return_value = [mock_bi_rate]
        
        mock_result_kurs = MagicMock()
        mock_result_kurs.scalars.return_value.all.return_value = [mock_kurs]

        mock_result_ihsg = MagicMock()
        mock_result_ihsg.scalars.return_value.all.return_value = [mock_ihsg]

        mock_result_inflasi = MagicMock()
        mock_result_inflasi.scalars.return_value.all.return_value = [mock_inflasi]

        mock_result_berita = MagicMock()
        mock_result_berita.scalar.return_value = 5

        # Setup side effect untuk execute query
        mock_session.execute.side_effect = [
            mock_result_bi,      # bi_rate
            mock_result_kurs,    # kurs
            mock_result_ihsg,    # ihsg
            mock_result_inflasi, # inflasi
            mock_result_berita,  # count berita lapkeu
        ]

        state: ScoringState = {
            "daftar_saham": ["BBCA"],
            "kondisi_pasar": {},
            "bobot": {},
            "skor_per_saham": [],
            "perlu_retry": [],
            "hasil_final": []
        }

        # Jalankan node analisis_kondisi_pasar
        result = await analisis_kondisi_pasar(state)

        # Verifikasi hasil
        bobot = result["bobot"]
        kondisi = result["kondisi_pasar"]

        self.assertTrue(kondisi["ada_lapkeu_baru"])
        self.assertEqual(bobot["fundamental"], 0.40)  # Fundamental naik ke 40%
        self.assertAlmostEqual(sum(bobot.values()), 1.0, places=2)

    def test_run_async_tests(self):
        """
        Helper untuk menjalankan test async di dalam class unittest standard.
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.test_bobot_adaptif_musim_lapkeu_async())
        loop.run_until_complete(self.test_empty_macro_halts_pipeline_async())
        loop.run_until_complete(self.test_empty_fundamental_triggers_realtime_scraping_and_fallback_async())
        loop.run_until_complete(self.test_empty_news_triggers_background_scraping_async())

    @patch("backend.agents.scoring_agent.async_session")
    async def test_empty_macro_halts_pipeline_async(self, mock_session_cls):
        """
        Menguji bahwa jika data makro kosong sama sekali di database,
        maka pipeline dihentikan dengan RuntimeError (Critical Error).
        """
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_cls.return_value = mock_session

        # Mock database returns empty list for all queries
        mock_result_empty = MagicMock()
        mock_result_empty.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_result_empty,  # bi_rate
            mock_result_empty,  # kurs
            mock_result_empty,  # ihsg
            mock_result_empty,  # inflasi
            mock_result_empty,  # count berita
        ]

        state: ScoringState = {
            "daftar_saham": ["BBCA"],
            "kondisi_pasar": {},
            "bobot": {},
            "skor_per_saham": [],
            "perlu_retry": [],
            "hasil_final": []
        }

        # Jalankan dan verifikasi raises RuntimeError
        with self.assertRaises(RuntimeError):
            await analisis_kondisi_pasar(state)

    @patch("backend.agents.scoring_agent.async_session")
    @patch("backend.agents.scoring_agent.scrape_and_save_fundamental_for_emiten")
    async def test_empty_fundamental_triggers_realtime_scraping_and_fallback_async(self, mock_scrape, mock_session_cls):
        """
        Menguji bahwa jika data fundamental kosong, sistem mencoba memicu real-time scraping.
        Jika scraping gagal, sistem tidak me-skip emiten melainkan fallback ke nilai netral agar tidak terdelist.
        """
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_cls.return_value = mock_session

        # Mock db fundamental query to return None (kosong)
        mock_result_fund = MagicMock()
        mock_result_fund.scalar_one_or_none.return_value = None

        mock_result_saham = MagicMock()
        mock_result_saham.scalar_one_or_none.return_value = None

        mock_result_berita = MagicMock()
        mock_result_berita.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_result_fund,   # fundamental
            mock_result_saham,  # saham (sektor)
            mock_result_berita, # berita
        ]

        # Mock real-time scraping to return None (simulasi gagal mengambil data baru)
        mock_scrape.return_value = None

        from backend.agents.scoring_agent import hitung_skor

        state: ScoringState = {
            "daftar_saham": ["BBCA"],
            "kondisi_pasar": {
                "makro_terbaru": {
                    "bi_rate": {"nilai": 6.0, "tanggal": "2026-06-05", "satuan": "%"},
                    "kurs_usd_idr": {"nilai": 15500.0, "tanggal": "2026-06-05", "satuan": "IDR"},
                    "ihsg": {"nilai": 7200.0, "tanggal": "2026-06-05", "satuan": "pts"},
                    "inflasi_yoy": {"nilai": 3.0, "tanggal": "2026-06-05", "satuan": "%"},
                }
            },
            "bobot": {
                "fundamental": 0.30,
                "sentimen": 0.25,
                "sektor": 0.20,
                "makro": 0.15,
                "risiko": 0.10,
            },
            "skor_per_saham": [],
            "perlu_retry": [],
            "hasil_final": []
        }

        result = await hitung_skor(state)
        # Emiten BBCA tidak boleh di-skip (tidak terdelist), panjang harus 1
        self.assertEqual(len(result["skor_per_saham"]), 1)
        # Skor fundamental harus netral (50.0) karena fallback desimal
        self.assertEqual(result["skor_per_saham"][0]["skor_fundamental"], 50.0)
        # Memastikan scrape_and_save_fundamental_for_emiten dipanggil
        mock_scrape.assert_called_once_with("BBCA")

    @patch("backend.agents.scoring_agent.async_session")
    @patch("backend.agents.scoring_agent.asyncio.create_task")
    async def test_empty_news_triggers_background_scraping_async(self, mock_create_task, mock_session_cls):
        """
        Menguji bahwa jika data berita kosong, maka scoring tetap jalan dengan skor netral (50)
        dan memicu background scraping task untuk emiten tersebut.
        """
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session_cls.return_value = mock_session

        # Mock db fundamental query to return valid data
        from backend.db.postgres import Fundamental, Saham
        from datetime import date
        mock_fund_obj = Fundamental(
            kode_saham="BBCA",
            tanggal=date.today(),
            roe=18.0,
            eps=450.0,
            pbv=4.5,
            der=0.2,
            harga_terakhir=10000.0,
            volume=2_000_000,
            market_cap=1_200_000_000_000,
            pe_ratio=22.0,
            dividend_yield=2.5
        )
        mock_saham_obj = Saham(kode="BBCA", sektor="Financials")

        mock_result_fund = MagicMock()
        mock_result_fund.scalar_one_or_none.return_value = mock_fund_obj

        mock_result_saham = MagicMock()
        mock_result_saham.scalar_one_or_none.return_value = mock_saham_obj

        # News query returns empty list
        mock_result_berita = MagicMock()
        mock_result_berita.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_result_fund,   # fundamental
            mock_result_saham,  # saham (sektor)
            mock_result_berita, # berita
        ]

        from backend.agents.scoring_agent import hitung_skor

        state: ScoringState = {
            "daftar_saham": ["BBCA"],
            "kondisi_pasar": {
                "makro_terbaru": {
                    "bi_rate": {"nilai": 6.0, "tanggal": "2026-06-05", "satuan": "%"},
                    "kurs_usd_idr": {"nilai": 15500.0, "tanggal": "2026-06-05", "satuan": "IDR"},
                    "ihsg": {"nilai": 7200.0, "tanggal": "2026-06-05", "satuan": "pts"},
                    "inflasi_yoy": {"nilai": 3.0, "tanggal": "2026-06-05", "satuan": "%"},
                }
            },
            "bobot": {
                "fundamental": 0.30,
                "sentimen": 0.25,
                "sektor": 0.20,
                "makro": 0.15,
                "risiko": 0.10,
            },
            "skor_per_saham": [],
            "perlu_retry": [],
            "hasil_final": []
        }

        result = await hitung_skor(state)
        
        # Harus ada 1 saham hasil scoring
        self.assertEqual(len(result["skor_per_saham"]), 1)
        # Sentimen harus netral (50)
        self.assertEqual(result["skor_per_saham"][0]["skor_sentimen"], 50.0)
        # Background task pencarian berita harus dipicu
        self.assertTrue(mock_create_task.called)
        any_news_scrape = any(
            "scrape_and_index_news_for_emiten" in str(arg)
            for call in mock_create_task.call_args_list
            for arg in call[0]
        )
        self.assertTrue(any_news_scrape, "scrape_and_index_news_for_emiten should have been called in create_task")


if __name__ == "__main__":
    unittest.main()
