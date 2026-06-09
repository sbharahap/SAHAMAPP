"""
AI Saham Indonesia — Batch RAG Triad Evaluation Runner

Script untuk menjalankan evaluasi RAG Triad secara batch terhadap
dataset pertanyaan uji. Mengirim setiap pertanyaan melalui full
chatbot pipeline (klasifikasi → retrieval → LLM) lalu mengevaluasi
kualitas jawaban menggunakan RAG Triad (LLM-as-a-Judge).

Hasil disimpan ke tabel rag_evaluation di PostgreSQL dan dicetak
sebagai laporan ringkasan di terminal.

Cara menjalankan:
    # Dari root proyek
    python -m backend.scripts.run_rag_eval

    # Hanya jalankan N pertanyaan pertama
    python -m backend.scripts.run_rag_eval --limit 5

    # Gunakan batch ID kustom
    python -m backend.scripts.run_rag_eval --batch-id eval-v2
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

# Konfigurasi logging
logger.remove()
logger.add(
    sys.stderr,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{message}</cyan>"
    ),
    level="INFO",
    colorize=True,
)

# ============================================================
# Test Dataset — Pertanyaan Evaluasi RAG
# ============================================================
# Mencakup berbagai jenis pertanyaan: spesifik, perbandingan, umum

TEST_QUESTIONS: list[dict[str, str]] = [
    # --- Pertanyaan spesifik per saham ---
    {
        "pertanyaan": "Bagaimana kinerja keuangan BBCA di kuartal terakhir?",
        "kategori": "spesifik",
    },
    {
        "pertanyaan": "Berapa ROE dan PBV saham TLKM saat ini?",
        "kategori": "spesifik",
    },
    {
        "pertanyaan": "Apa rekomendasi untuk saham BMRI minggu ini?",
        "kategori": "spesifik",
    },
    {
        "pertanyaan": "Bagaimana prospek saham ASII berdasarkan berita terbaru?",
        "kategori": "spesifik",
    },
    {
        "pertanyaan": "Apakah BBRI layak dibeli saat ini? Jelaskan alasannya.",
        "kategori": "spesifik",
    },
    {
        "pertanyaan": "Berapa skor scoring UNVR dan apa rekomendasinya?",
        "kategori": "spesifik",
    },

    # --- Pertanyaan perbandingan ---
    {
        "pertanyaan": "Bandingkan kinerja BBCA vs BMRI dari sisi fundamental.",
        "kategori": "perbandingan",
    },
    {
        "pertanyaan": "Antara TLKM dan ISAT, mana yang lebih menarik untuk investasi?",
        "kategori": "perbandingan",
    },
    {
        "pertanyaan": "Perbandingan ROE dan DER antara BBCA, BBRI, dan BBNI.",
        "kategori": "perbandingan",
    },

    # --- Pertanyaan umum (pasar/makro) ---
    {
        "pertanyaan": "Bagaimana kondisi pasar saham Indonesia saat ini?",
        "kategori": "umum",
    },
    {
        "pertanyaan": "Apa saja top 10 rekomendasi saham minggu ini?",
        "kategori": "umum",
    },
    {
        "pertanyaan": "Bagaimana pengaruh suku bunga BI terhadap saham perbankan?",
        "kategori": "umum",
    },
    {
        "pertanyaan": "Sektor apa yang paling menarik untuk investasi saat ini?",
        "kategori": "umum",
    },
    {
        "pertanyaan": "Bagaimana tren inflasi Indonesia dan dampaknya ke IHSG?",
        "kategori": "umum",
    },
    {
        "pertanyaan": "Apa sentimen pasar terhadap saham-saham bank besar?",
        "kategori": "umum",
    },
]


async def run_batch_evaluation(
    limit: int | None = None,
    batch_id: str | None = None,
) -> dict:
    """
    Jalankan evaluasi RAG Triad secara batch.

    Args:
        limit: Jumlah pertanyaan yang akan dievaluasi (None = semua).
        batch_id: ID batch kustom. Default: auto-generate berdasarkan timestamp.

    Returns:
        Dict ringkasan evaluasi.
    """
    from backend.agents.chatbot_agent import chat
    from backend.rag.evaluator import evaluasi_rag_triad
    from backend.db.postgres import async_session, RAGEvaluation

    _WIB = timezone(timedelta(hours=7))
    if not batch_id:
        batch_id = f"eval-{datetime.now(_WIB).strftime('%Y%m%d-%H%M%S')}"

    questions = TEST_QUESTIONS[:limit] if limit else TEST_QUESTIONS
    total = len(questions)

    logger.info(f"{'=' * 60}")
    logger.info(f"  RAG TRIAD BATCH EVALUATION")
    logger.info(f"  Batch ID : {batch_id}")
    logger.info(f"  Questions: {total}")
    logger.info(f"  Model    : {__import__('backend.config', fromlist=['settings']).settings.ollama_model}")
    logger.info(f"{'=' * 60}")

    results: list[dict] = []

    for i, q in enumerate(questions, 1):
        pertanyaan = q["pertanyaan"]
        kategori = q["kategori"]

        logger.info(f"\n[{i}/{total}] ({kategori}) {pertanyaan}")

        try:
            # Step 1: Jalankan chatbot pipeline lengkap
            chat_result = await chat(pertanyaan=pertanyaan)

            jawaban = chat_result.get("jawaban", "")
            confidence = chat_result.get("confidence", 0.0)
            sumber_data = chat_result.get("sumber_data", 0)

            logger.info(f"   Jawaban: {jawaban[:100]}...")
            logger.info(f"   Confidence: {confidence:.2f}, Sumber: {sumber_data} docs")

            # Step 2: Ambil konteks dari retrieval (jalankan ulang retrieval
            # untuk mendapatkan teks dokumen yang digunakan)
            from backend.rag.retriever import retrieve
            saham_list = chat_result.get("saham", [])
            kode_saham = saham_list[0] if saham_list else None
            docs = await retrieve(query=pertanyaan, kode_saham=kode_saham, top_k=5)
            contexts = [doc.get("teks", "") for doc in docs[:7]]

            # Step 3: Evaluasi RAG Triad
            eval_result = await evaluasi_rag_triad(
                query=pertanyaan,
                contexts=contexts,
                response_text=jawaban,
                batch_id=batch_id,
                simpan_ke_db=True,
            )

            cr = eval_result["context_relevance"]["score"]
            g = eval_result["groundedness"]["score"]
            ar = eval_result["answer_relevance"]["score"]
            avg = eval_result["avg_triad_score"]

            logger.info(
                f"   📊 CR={cr}/5 | G={g}/5 | AR={ar}/5 | Avg={avg}/5"
            )

            results.append({
                "pertanyaan": pertanyaan,
                "kategori": kategori,
                "jawaban": jawaban[:200],
                "confidence": confidence,
                "sumber_data": sumber_data,
                "context_relevance": cr,
                "groundedness": g,
                "answer_relevance": ar,
                "avg_triad_score": avg,
                "cr_reason": eval_result["context_relevance"].get("reason", ""),
                "g_reason": eval_result["groundedness"].get("reason", ""),
                "ar_reason": eval_result["answer_relevance"].get("reason", ""),
            })

        except Exception as e:
            logger.error(f"   ❌ Error: {type(e).__name__}: {e}")
            results.append({
                "pertanyaan": pertanyaan,
                "kategori": kategori,
                "jawaban": "",
                "confidence": 0.0,
                "sumber_data": 0,
                "context_relevance": 1.0,
                "groundedness": 1.0,
                "answer_relevance": 1.0,
                "avg_triad_score": 1.0,
                "error": str(e),
            })

    # ============================================================
    # Cetak Laporan Ringkasan
    # ============================================================
    summary = _generate_summary(batch_id, results)
    _print_report(summary, results)

    return summary


def _generate_summary(batch_id: str, results: list[dict]) -> dict:
    """Hitung statistik agregat dari hasil evaluasi."""
    if not results:
        return {"batch_id": batch_id, "total": 0}

    cr_scores = [r["context_relevance"] for r in results]
    g_scores = [r["groundedness"] for r in results]
    ar_scores = [r["answer_relevance"] for r in results]
    avg_scores = [r["avg_triad_score"] for r in results]

    def stats(scores: list[float]) -> dict:
        n = len(scores)
        mean = sum(scores) / n
        sorted_s = sorted(scores)
        median = sorted_s[n // 2] if n % 2 else (sorted_s[n // 2 - 1] + sorted_s[n // 2]) / 2
        return {
            "mean": round(mean, 2),
            "median": round(median, 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
        }

    # Per kategori
    per_kategori = {}
    for kat in ["spesifik", "perbandingan", "umum"]:
        kat_results = [r for r in results if r.get("kategori") == kat]
        if kat_results:
            per_kategori[kat] = {
                "count": len(kat_results),
                "avg_triad": round(sum(r["avg_triad_score"] for r in kat_results) / len(kat_results), 2),
                "avg_cr": round(sum(r["context_relevance"] for r in kat_results) / len(kat_results), 2),
                "avg_g": round(sum(r["groundedness"] for r in kat_results) / len(kat_results), 2),
                "avg_ar": round(sum(r["answer_relevance"] for r in kat_results) / len(kat_results), 2),
            }

    return {
        "batch_id": batch_id,
        "total": len(results),
        "errors": sum(1 for r in results if "error" in r),
        "context_relevance": stats(cr_scores),
        "groundedness": stats(g_scores),
        "answer_relevance": stats(ar_scores),
        "overall": stats(avg_scores),
        "per_kategori": per_kategori,
    }


def _print_report(summary: dict, results: list[dict]) -> None:
    """Cetak laporan evaluasi ke terminal."""
    print("\n")
    print("=" * 70)
    print("  RAG TRIAD EVALUATION REPORT")
    print(f"  Batch ID: {summary['batch_id']}")
    print(f"  Total Questions: {summary['total']} | Errors: {summary.get('errors', 0)}")
    print("=" * 70)

    if summary["total"] == 0:
        print("  Tidak ada hasil evaluasi.")
        return

    # Tabel ringkasan metrik
    print("\n  AGGREGATE SCORES (1-5 scale)")
    print("  " + "-" * 50)
    print(f"  {'Metric':<22} {'Mean':>6} {'Median':>8} {'Min':>6} {'Max':>6}")
    print("  " + "-" * 50)
    for metric, label in [
        ("context_relevance", "Context Relevance"),
        ("groundedness", "Groundedness"),
        ("answer_relevance", "Answer Relevance"),
        ("overall", "OVERALL (Avg Triad)"),
    ]:
        s = summary[metric]
        print(f"  {label:<22} {s['mean']:>6.2f} {s['median']:>8.2f} {s['min']:>6.2f} {s['max']:>6.2f}")
    print("  " + "-" * 50)

    # Per kategori
    per_kat = summary.get("per_kategori", {})
    if per_kat:
        print("\n  SCORES PER CATEGORY")
        print("  " + "-" * 60)
        print(f"  {'Category':<15} {'N':>3} {'Avg Triad':>10} {'CR':>6} {'G':>6} {'AR':>6}")
        print("  " + "-" * 60)
        for kat, data in per_kat.items():
            print(
                f"  {kat:<15} {data['count']:>3} {data['avg_triad']:>10.2f} "
                f"{data['avg_cr']:>6.2f} {data['avg_g']:>6.2f} {data['avg_ar']:>6.2f}"
            )
        print("  " + "-" * 60)

    # Detail per pertanyaan
    print("\n  DETAIL PER QUESTION")
    print("  " + "-" * 70)
    for i, r in enumerate(results, 1):
        status = "❌" if "error" in r else "✅"
        print(f"  {status} [{i}] {r['pertanyaan'][:60]}")
        if "error" in r:
            print(f"       Error: {r['error'][:80]}")
        else:
            print(
                f"       CR={r['context_relevance']:.1f} | "
                f"G={r['groundedness']:.1f} | "
                f"AR={r['answer_relevance']:.1f} | "
                f"Avg={r['avg_triad_score']:.2f} | "
                f"Conf={r['confidence']:.2f} | "
                f"Docs={r['sumber_data']}"
            )

    # Interpretasi
    overall_mean = summary["overall"]["mean"]
    print("\n  INTERPRETATION")
    print("  " + "-" * 50)
    if overall_mean >= 4.0:
        grade = "EXCELLENT"
        desc = "RAG pipeline berkualitas tinggi."
    elif overall_mean >= 3.0:
        grade = "GOOD"
        desc = "RAG pipeline cukup baik, ada ruang perbaikan."
    elif overall_mean >= 2.0:
        grade = "NEEDS IMPROVEMENT"
        desc = "RAG pipeline perlu diperbaiki secara signifikan."
    else:
        grade = "POOR"
        desc = "RAG pipeline bermasalah serius."

    print(f"  Overall Score: {overall_mean:.2f}/5.0 -> {grade}")
    print(f"  {desc}")

    # Saran spesifik berdasarkan skor terendah
    metrics = {
        "Context Relevance": summary["context_relevance"]["mean"],
        "Groundedness": summary["groundedness"]["mean"],
        "Answer Relevance": summary["answer_relevance"]["mean"],
    }
    weakest = min(metrics, key=metrics.get)
    weakest_score = metrics[weakest]

    if weakest_score < 3.5:
        suggestions = {
            "Context Relevance": (
                "Retriever perlu diperbaiki: coba tingkatkan top_k, "
                "perbaiki chunking strategy, atau gunakan hybrid search."
            ),
            "Groundedness": (
                "LLM terlalu banyak berhalusinasi: perkuat instruksi prompt "
                "agar hanya menggunakan informasi dari dokumen referensi."
            ),
            "Answer Relevance": (
                "Jawaban LLM kurang fokus: perbaiki system prompt agar "
                "jawaban lebih langsung dan relevan dengan pertanyaan."
            ),
        }
        print(f"\n  ⚠️  Metrik terlemah: {weakest} ({weakest_score:.2f}/5)")
        print(f"  💡 Saran: {suggestions[weakest]}")

    print("\n" + "=" * 70)


# ============================================================
# Entry point: python -m backend.scripts.run_rag_eval
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Triad Batch Evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--batch-id", type=str, default=None, help="Custom batch ID")
    args = parser.parse_args()

    asyncio.run(run_batch_evaluation(limit=args.limit, batch_id=args.batch_id))
