import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings

async def test_prompt(prompt_text):
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,
        timeout=30
    )
    messages = [
        SystemMessage(content="Kamu adalah asisten keuangan yang mengekstrak data numerik secara akurat dalam format JSON. Jawab hanya dengan JSON valid."),
        HumanMessage(content=prompt_text)
    ]
    resp = await llm.ainvoke(messages)
    print("Response:", resp.content)

async def main():
    titles_bi = """- Dampak Kenaikan BI Rate Jadi 5,25% bagi Masyarakat dan Dunia Usaha - Pajakku
- BI Rate naik 50 bps jadi 5,25% demi jaga rupiah dari gejolak global - IDNFinancials
- Suku bunga acuan naik: Cicilan akan naik, kelas menengah bersiap turun kelas - BBC
- BI Rate Hari Ini Naik Jadi 5,25 Persen, Apa Dampaknya? - Kompas.com
- BI Diperkirakan Naikkan Suku Bunga ke 5% di RDG Mei 2026 - Bareksa.com"""
    
    titles_inf = """- Inflasi year-on-year (y-on-y) pada Desember 2025 sebesar 2,92 persen - Badan Pusat Statistik Indonesia
- Inflasi year-on-year (y-on-y) pada Maret 2026 sebesar 3,48 persen. - Badan Pusat Statistik Indonesia
- Inflasi Tahunan RI Tembus 3,55% di Januari, Kena Efek Diskon Listrik! - CNBC Indonesia
- Inflasi Tertinggi 3 Tahun Terakhir, Harga Pangan Melonjak - KONTAN
- Inflasi year-on-year (y-on-y) pada Februari 2026 sebesar 4,76 persen. - Badan Pusat Statistik Indonesia"""

    prompt_bi = f"""Ekstrak angka persentase BI Rate (suku bunga acuan Bank Indonesia) terbaru yang disebutkan dalam judul-judul berita berikut.

Berita:
{titles_bi}

Instruksi:
1. Temukan angka persentase suku bunga acuan terbaru (misalnya: 5.25 atau 6.00). Jangan sertakan simbol % dalam nilai JSON.
2. Jika ada koma, ganti dengan titik (contoh: 5,25 menjadi 5.25).
3. Kembalikan hasilnya HANYA dalam format JSON seperti ini:
{{"nilai": <float_angka>}}
4. Jika tidak ada informasi suku bunga yang jelas, kembalikan {{"nilai": null}}.
"""

    prompt_inf = f"""Ekstrak angka persentase Inflasi YoY (Year-on-Year) terbaru yang disebutkan dalam judul-judul berita berikut.

Berita:
{titles_inf}

Instruksi:
1. Temukan angka persentase inflasi tahunan terbaru (misalnya: 3.48 atau 4.76). Jangan sertakan simbol % dalam nilai JSON.
2. Jika ada koma, ganti dengan titik (contoh: 3,48 menjadi 3.48).
3. Kembalikan hasilnya HANYA dalam format JSON seperti ini:
{{"nilai": <float_angka>}}
4. Jika tidak ada informasi inflasi yang jelas, kembalikan {{"nilai": null}}.
"""

    print("BI Rate extraction:")
    await test_prompt(prompt_bi)
    print("\nInflation extraction:")
    await test_prompt(prompt_inf)

if __name__ == "__main__":
    asyncio.run(main())
