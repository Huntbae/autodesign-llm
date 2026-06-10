"""Phase 3 — 지식(RAG) 골격.

표준·설계규칙·재료물성을 출처 메타와 함께 인덱싱하고, 설계명세에 맞는 근거를
검색해 '사전 검토 리포트'에 인용한다. 의존성 없는 TF-IDF 검색기로 시작
(추후 임베딩+벡터DB로 교체: docs/04-VARIANT-HYBRID §4).
"""
from .base import Chunk, Retriever
from .store import KnowledgeBase
from .prereview import build_prereview

__all__ = ["Chunk", "Retriever", "KnowledgeBase", "build_prereview"]
