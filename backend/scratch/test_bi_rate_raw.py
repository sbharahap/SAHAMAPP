import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings

async def main():
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.0,
        timeout=30
    )
    titles_str = """- Dampak Kenaikan BI Rate Jadi 5,25% bagi Masyarakat dan Dunia Usaha - Pajakku
- BI Rate naik 50 bps jadi 5,25% demi jaga rupiah dari gejolak global - IDNFinancials
- Suku bunga acuan naik: Cicilan akan naik, kelas menengah bersiap turun kelas - BBC
- BI Rate Hari Ini Naik Jadi 5,25 Persen, Apa Dampaknya? - Kompas.com
- BI Diperkirakan Naikkan Suku Bunga ke 5% di RDG Mei 2026 - Bareksa.com"""
    
    prompt = f"""Tolong baca judul-judul berita tentang suku bunga acuan Bank Indonesia (BI Rate / BI-7Day RR) berikut dan temukan persentase suku bunga acuan terbaru yang berlaku saat ini.

Berita:
{titles_str}

Instruksi:
1. Temukan angka suku bunga acuan terbaru (misalnya: 6.00% atau 6,25%).
2. Kembalikan angka tersebut sebagai nilai float murni dalam format JSON.
3. Jika terdapat koma, ganti dengan titik (contoh: 6,25 menjadi 6.25).
4. Jika tidak ada informasi suku bunga yang jelas di judul-judul tersebut, kembalikan null.

Format output wajib JSON:
{{"nilai": float | null}}
"""
    messages = [
        SystemMessage(content="Kamu adalah asisten keuangan yang mengekstrak data numerik secara akurat dalam format JSON. Jawab hanya dengan JSON valid."),
        HumanMessage(content=prompt)
    ]
    resp = await llm.ainvoke(messages)
    print("Raw response content:")
    print(resp.content)

if __name__ == "__main__":
    asyncio.run(main())
