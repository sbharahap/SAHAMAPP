"""
AI Saham Indonesia — RAG Triad Evaluator

Modul ini mengimplementasikan evaluasi kualitas RAG (Retrieval-Augmented Generation)
menggunakan konsep RAG Triad dengan LLM Qwen3 sebagai juri (LLM-as-a-Judge).

Metrik yang diukur (skala 1-5):
1. Context Relevance  : Apakah dokumen referensi relevan dengan pertanyaan user?
2. Groundedness       : Apakah jawaban chatbot didukung penuh oleh dokumen referensi?
3. Answer Relevance   : Apakah jawaban chatbot menjawab inti pertanyaan user?
"""

import json
from loguru import logger
from backend.config import settings


async def evaluasi_rag_triad(
    query: str,
    contexts: list[str],
    response_text: str,
    batch_id: str | None = None,
    simpan_ke_db: bool = True,
) -> dict:
    """
    Menjalankan evaluasi RAG Triad dan opsional menyimpan hasilnya ke PostgreSQL.

    Args:
        query: Pertanyaan asli dari user.
        contexts: List teks dokumen konteks/referensi yang ditarik dari ChromaDB.
        response_text: Jawaban yang dihasilkan oleh chatbot.
        batch_id: ID batch evaluasi (untuk mengelompokkan satu run evaluasi).
        simpan_ke_db: Jika True, simpan hasil evaluasi ke tabel rag_evaluation.

    Returns:
        Dict hasil evaluasi dengan skor 1-5 dan alasan untuk masing-masing metrik.
    """
    if not contexts:
        logger.warning("⚠️ RAG Triad: Contexts kosong. Evaluasi dilewati.")
        return {
            "context_relevance": {"score": 1.0, "reason": "No contexts provided"},
            "groundedness": {"score": 1.0, "reason": "No contexts to check groundedness"},
            "answer_relevance": {"score": 1.0, "reason": "Unable to evaluate without context"},
            "avg_triad_score": 1.0
        }

    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.0,
            timeout=60,
        )

        context_str = "\n".join(f"Dokumen [{i}]: {ctx}" for i, ctx in enumerate(contexts, 1))

        prompt = f"""Kamu adalah evaluator kualitas AI profesional yang bertindak sebagai juri (LLM-as-a-Judge) untuk mengevaluasi sistem tanya jawab berbasis RAG.
Evaluasilah interaksi RAG berikut berdasarkan tiga metrik RAG Triad (Context Relevance, Groundedness, dan Answer Relevance) dengan skala nilai 1 sampai 5 (1 sangat buruk, 5 sangat baik).

DATA EVALUASI:
- Pertanyaan User: "{query}"
- Dokumen Referensi (Konteks):
{context_str}
- Jawaban Chatbot: "{response_text}"

METRIK PENILAIAN:
1. "context_relevance": Menilai apakah dokumen referensi yang ditarik relevan dengan pertanyaan user.
   - Skor 1: Dokumen sama sekali tidak berhubungan dengan pertanyaan.
   - Skor 5: Dokumen berisi informasi yang sangat tepat untuk menjawab pertanyaan.

2. "groundedness": Menilai apakah jawaban chatbot hanya bersumber dan didukung oleh dokumen referensi (tidak mengarang/halusinasi informasi baru).
   - Skor 1: Jawaban mengandung klaim/fakta yang tidak didukung atau bertentangan dengan dokumen referensi.
   - Skor 5: Setiap kalimat dalam jawaban didukung penuh oleh dokumen referensi.

3. "answer_relevance": Menilai apakah jawaban chatbot secara langsung menjawab esensi dari pertanyaan user (tidak bertele-tele atau melebar).
   - Skor 1: Jawaban tidak menjawab pertanyaan user sama sekali.
   - Skor 5: Jawaban menjawab pertanyaan dengan tuntas, padat, dan jelas.

Format output wajib JSON:
{{
  "context_relevance": {{"score": float, "reason": "alasan singkat 1 kalimat dalam Bahasa Indonesia"}},
  "groundedness": {{"score": float, "reason": "alasan singkat 1 kalimat dalam Bahasa Indonesia"}},
  "answer_relevance": {{"score": float, "reason": "alasan singkat 1 kalimat dalam Bahasa Indonesia"}}
}}
"""
        messages = [
            SystemMessage(content="Kamu adalah juri evaluator RAG profesional. Jawab hanya dengan format JSON valid. Jangan tambahkan teks apapun di luar JSON."),
            HumanMessage(content=prompt)
        ]

        response = await llm.ainvoke(messages)
        res_text = response.content.strip()

        # Strip <think>...</think> tags if present (Qwen3 reasoning mode)
        if "<think>" in res_text:
            res_text = res_text.split("</think>")[-1].strip()

        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].strip()

        data = json.loads(res_text.strip())

        cr_score = float(data.get("context_relevance", {}).get("score", 1.0))
        g_score = float(data.get("groundedness", {}).get("score", 1.0))
        ar_score = float(data.get("answer_relevance", {}).get("score", 1.0))

        # Clamp to valid range
        cr_score = max(1.0, min(5.0, cr_score))
        g_score = max(1.0, min(5.0, g_score))
        ar_score = max(1.0, min(5.0, ar_score))

        avg_score = round((cr_score + g_score + ar_score) / 3.0, 2)

        data["context_relevance"]["score"] = cr_score
        data["groundedness"]["score"] = g_score
        data["answer_relevance"]["score"] = ar_score
        data["avg_triad_score"] = avg_score

        logger.info(
            f"📊 RAG Triad Evaluation: "
            f"Context Relevance={cr_score}/5 | Groundedness={g_score}/5 | "
            f"Answer Relevance={ar_score}/5 -> Rata-rata={avg_score}/5"
        )

        # Save to DB if batch_id provided
        if simpan_ke_db and batch_id:
            await _simpan_ke_db(
                batch_id=batch_id,
                query=query,
                response_text=response_text,
                num_contexts=len(contexts),
                eval_data=data,
            )

        return data

    except Exception as e:
        logger.error(f"❌ RAG Triad Evaluator gagal: {e}")
        return {
            "context_relevance": {"score": 1.0, "reason": f"Evaluation error: {e}"},
            "groundedness": {"score": 1.0, "reason": f"Evaluation error: {e}"},
            "answer_relevance": {"score": 1.0, "reason": f"Evaluation error: {e}"},
            "avg_triad_score": 1.0
        }


async def _simpan_ke_db(
    batch_id: str,
    query: str,
    response_text: str,
    num_contexts: int,
    eval_data: dict,
) -> None:
    """Simpan satu hasil evaluasi ke tabel rag_evaluation di PostgreSQL."""
    try:
        from backend.db.postgres import async_session, RAGEvaluation

        async with async_session() as session:
            record = RAGEvaluation(
                batch_id=batch_id,
                query=query,
                response_text=response_text,
                num_contexts=num_contexts,
                context_relevance=eval_data["context_relevance"]["score"],
                context_relevance_reason=eval_data["context_relevance"].get("reason"),
                groundedness=eval_data["groundedness"]["score"],
                groundedness_reason=eval_data["groundedness"].get("reason"),
                answer_relevance=eval_data["answer_relevance"]["score"],
                answer_relevance_reason=eval_data["answer_relevance"].get("reason"),
                avg_triad_score=eval_data["avg_triad_score"],
            )
            session.add(record)
            await session.commit()
            logger.debug(f"💾 RAG eval disimpan ke DB (batch={batch_id})")

    except Exception as e:
        logger.error(f"❌ Gagal simpan RAG eval ke DB: {e}")
