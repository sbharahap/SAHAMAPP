"""
AI Saham Indonesia — Router RAG Triad Evaluation

Endpoint API untuk menjalankan evaluasi RAG Triad secara batch
dan melihat hasil evaluasi historis dari PostgreSQL.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.postgres import RAGEvaluation, async_session, get_db_session

router = APIRouter(
    prefix="/rag-eval",
    tags=["RAG Evaluation"],
)

_WIB = timezone(timedelta(hours=7))


class EvalTriggerRequest(BaseModel):
    limit: Optional[int] = Field(None, ge=1, le=50, description="Jumlah pertanyaan (None = semua)")
    batch_id: Optional[str] = Field(None, description="Custom batch ID")


class EvalTriggerResponse(BaseModel):
    status: str
    batch_id: str
    message: str


@router.post("/run", response_model=EvalTriggerResponse)
async def trigger_eval(request: EvalTriggerRequest, background_tasks: BackgroundTasks):
    """
    Trigger batch RAG Triad evaluation di background.
    Hasil akan disimpan ke tabel rag_evaluation.
    """
    batch_id = request.batch_id or f"eval-{datetime.now(_WIB).strftime('%Y%m%d-%H%M%S')}"

    async def _run():
        from backend.scripts.run_rag_eval import run_batch_evaluation
        await run_batch_evaluation(limit=request.limit, batch_id=batch_id)

    background_tasks.add_task(_run)

    return EvalTriggerResponse(
        status="accepted",
        batch_id=batch_id,
        message=f"Evaluasi batch '{batch_id}' sedang berjalan di background.",
    )


@router.get("/results")
async def get_eval_results(
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Ambil hasil evaluasi RAG Triad dari PostgreSQL.
    """
    stmt = select(RAGEvaluation).order_by(RAGEvaluation.created_at.desc())
    if batch_id:
        stmt = stmt.where(RAGEvaluation.batch_id == batch_id)
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "batch_id": r.batch_id,
            "query": r.query,
            "response_text": r.response_text[:200],
            "num_contexts": r.num_contexts,
            "context_relevance": r.context_relevance,
            "context_relevance_reason": r.context_relevance_reason,
            "groundedness": r.groundedness,
            "groundedness_reason": r.groundedness_reason,
            "answer_relevance": r.answer_relevance,
            "answer_relevance_reason": r.answer_relevance_reason,
            "avg_triad_score": r.avg_triad_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/summary")
async def get_eval_summary(
    batch_id: Optional[str] = Query(None, description="Filter by batch ID (None = semua)"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Ringkasan statistik agregat evaluasi RAG Triad.
    """
    base_filter = RAGEvaluation.batch_id == batch_id if batch_id else True

    stmt = select(
        func.count(RAGEvaluation.id).label("total"),
        func.avg(RAGEvaluation.context_relevance).label("avg_cr"),
        func.avg(RAGEvaluation.groundedness).label("avg_g"),
        func.avg(RAGEvaluation.answer_relevance).label("avg_ar"),
        func.avg(RAGEvaluation.avg_triad_score).label("avg_overall"),
        func.min(RAGEvaluation.avg_triad_score).label("min_overall"),
        func.max(RAGEvaluation.avg_triad_score).label("max_overall"),
    ).where(base_filter)

    result = await db.execute(stmt)
    row = result.one()

    if row.total == 0:
        return {"total": 0, "message": "Belum ada data evaluasi."}

    # Daftar batch yang tersedia
    stmt_batches = (
        select(
            RAGEvaluation.batch_id,
            func.count(RAGEvaluation.id).label("count"),
            func.avg(RAGEvaluation.avg_triad_score).label("avg_score"),
            func.min(RAGEvaluation.created_at).label("started_at"),
        )
        .group_by(RAGEvaluation.batch_id)
        .order_by(func.min(RAGEvaluation.created_at).desc())
        .limit(20)
    )
    batches_result = await db.execute(stmt_batches)
    batches = [
        {
            "batch_id": b.batch_id,
            "count": b.count,
            "avg_score": round(float(b.avg_score), 2) if b.avg_score else 0,
            "started_at": b.started_at.isoformat() if b.started_at else None,
        }
        for b in batches_result.all()
    ]

    return {
        "filter_batch_id": batch_id,
        "total": row.total,
        "avg_context_relevance": round(float(row.avg_cr), 2) if row.avg_cr else 0,
        "avg_groundedness": round(float(row.avg_g), 2) if row.avg_g else 0,
        "avg_answer_relevance": round(float(row.avg_ar), 2) if row.avg_ar else 0,
        "avg_overall": round(float(row.avg_overall), 2) if row.avg_overall else 0,
        "min_overall": round(float(row.min_overall), 2) if row.min_overall else 0,
        "max_overall": round(float(row.max_overall), 2) if row.max_overall else 0,
        "batches": batches,
    }
