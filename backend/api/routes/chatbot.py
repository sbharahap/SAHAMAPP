"""
AI Saham Indonesia — Router Chatbot (RAG)

Endpoint API untuk interaksi interaktif dengan chatbot RAG lokal (Qwen3 + BGE-M3 + ChromaDB).
Mendukung response streaming untuk animasi ketik (typing effect) pada client.
"""

import asyncio
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.agents.chatbot_agent import chat

router = APIRouter(
    tags=["Chatbot"],
)


class ChatPayload(BaseModel):
    pertanyaan: str = Field(..., description="Pertanyaan user dalam Bahasa Indonesia")
    riwayat: Optional[list[dict[str, str]]] = Field(default=[], description="Riwayat percakapan sebelumnya")


async def generate_response_stream(pertanyaan: str, riwayat: list[dict[str, str]]):
    """
    Generator asinkron untuk menyimulasikan/mengalirkan token jawaban RAG
    kata per kata dengan jeda waktu kecil untuk efek mengetik yang mulus.
    """
    try:
        # Panggil chatbot agent untuk memproses pertanyaan secara utuh (Klasifikasi + RAG + LLM)
        result = await chat(pertanyaan=pertanyaan, riwayat=riwayat)
        jawaban = result.get("jawaban", "Maaf, terjadi kesalahan saat memproses jawaban.")
        
        # Kirim data metadata di awal stream (opsional, sebagai baris tersembunyi atau terpisah)
        # Untuk kesederhanaan dan kehandalan streaming di SwiftUI, kita stream kata per kata
        kata_list = jawaban.split(" ")
        
        for i, kata in enumerate(kata_list):
            # Gabungkan kembali spasi
            chunk = kata + (" " if i < len(kata_list) - 1 else "")
            yield chunk
            # Jeda kecil (30 milidetik) agar iPhone client merender tulisan mengalir
            await asyncio.sleep(0.03)
            
    except Exception as e:
        yield f"\n⚠️ Error saat memproses jawaban streaming: {str(e)}"


@router.post("/chat")
@router.post("/chatbot/chat")
async def post_chat(payload: ChatPayload):
    """
    Endpoint Chatbot RAG. Menerima pertanyaan dan riwayat chat,
    mengembalikan StreamingResponse (jawaban mengalir kata per kata).
    """
    if not payload.pertanyaan.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    # Kembalikan response streaming
    return StreamingResponse(
        generate_response_stream(payload.pertanyaan, payload.riwayat),
        media_type="text/event-stream"
    )
