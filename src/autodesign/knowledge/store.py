"""KnowledgeBase — JSON 지식 로드 + 의존성 없는 TF-IDF 검색.

추후 임베딩+벡터DB(Qdrant/Chroma)로 교체해도 Retriever 계약은 동일.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
from collections import Counter
from typing import Dict, List, Tuple

from .base import Chunk

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_TOKEN = re.compile(r"[0-9A-Za-z가-힣]+")


def _tokens(text: str) -> List[str]:
    toks = [t.lower() for t in _TOKEN.findall(text)]
    # 한글 매칭 보강: 2글자 이상 한글 토큰의 bigram 추가
    extra = []
    for t in toks:
        if len(t) >= 3 and re.match(r"[가-힣]+$", t):
            extra += [t[i:i+2] for i in range(len(t) - 1)]
    return toks + extra


class KnowledgeBase:
    def __init__(self, chunks: List[Chunk] | None = None):
        self.chunks: List[Chunk] = chunks or []
        self._tf: List[Counter] = []
        self._idf: Dict[str, float] = {}
        if self.chunks:
            self._build_index()

    # ---- 로드 ----
    @classmethod
    def load_default(cls) -> "KnowledgeBase":
        chunks: List[Chunk] = []
        for path in sorted(glob.glob(os.path.join(_DATA_DIR, "*.json"))):
            with open(path, encoding="utf-8") as f:
                for i, rec in enumerate(json.load(f)):
                    chunks.append(Chunk(
                        id=rec.get("id", f"{os.path.basename(path)}#{i}"),
                        text=rec["text"], source=rec.get("source", "출처 미상(검증 필요)"),
                        category=rec.get("category", "general"), meta=rec.get("meta", {}),
                    ))
        return cls(chunks)

    # ---- 인덱스 ----
    def _build_index(self) -> None:
        self._tf = [Counter(_tokens(c.text)) for c in self.chunks]
        df: Counter = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.chunks)
        self._idf = {term: math.log((1 + n) / (1 + d)) + 1.0 for term, d in df.items()}

    def _vec(self, tf: Counter) -> Dict[str, float]:
        return {t: f * self._idf.get(t, 0.0) for t, f in tf.items()}

    @staticmethod
    def _cos(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    # ---- 검색 (Retriever 계약) ----
    def search(self, query: str, k: int = 5) -> List[Tuple[Chunk, float]]:
        if not self.chunks:
            return []
        qv = self._vec(Counter(_tokens(query)))
        scored = [(c, self._cos(qv, self._vec(tf)))
                  for c, tf in zip(self.chunks, self._tf)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scored[:k] if s > 0.0]
