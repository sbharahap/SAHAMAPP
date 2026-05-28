"""
AI Saham Indonesia — RAG Package

Retrieval-Augmented Generation untuk chatbot saham Indonesia:
- indexer   : Chunking, embedding, dan penyimpanan dokumen ke ChromaDB
- retriever : Pencarian dokumen relevan berdasarkan query
"""

from backend.rag.indexer import index_batch_berita, index_dokumen
from backend.rag.retriever import retrieve, retrieve_multi_saham

__all__ = [
    "index_dokumen",
    "index_batch_berita",
    "retrieve",
    "retrieve_multi_saham",
]
