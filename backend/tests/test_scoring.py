"""
AI Saham Indonesia — Unit Tests untuk Scoring Engine

Tes untuk memvalidasi:
1. Logika penyesuaian bobot adaptif saat musim laporan keuangan baru rilis.
2. Total bobot scoring selalu berjumlah 1.0 (100%).
3. Saham dengan tingkat utang (DER) tinggi menghasilkan skor risiko rendah (berisiko tinggi).
"""

import unittest
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
        mock_session_cls.return_value = mock_session

        # Mock query data makro (BI Rate, Kurs, dll) agar return kosong/normal
        # Mock query berita laporan keuangan -> return count = 5 (terdeteksi musim lapkeu)
        mock_result_makro = MagicMock()
        mock_result_makro.scalars.return_value.all.return_value = []
        
        mock_result_berita = MagicMock()
        mock_result_berita.scalar.return_value = 5

        # Setup side effect untuk execute query
        mock_session.execute.side_effect = [
            mock_result_makro,  # bi_rate
            mock_result_makro,  # kurs
            mock_result_makro,  # ihsg
            mock_result_makro,  # inflasi
            mock_result_berita, # count berita lapkeu
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


if __name__ == "__main__":
    unittest.main()
