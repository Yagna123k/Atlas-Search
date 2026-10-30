"""
Hybrid Retrieval Engine
Coordinates BM25 lexical retriever, Dense semantic retriever, and candidate fusion.
"""

from typing import Dict, List, Any, Optional
import time
from core.index.manager import IndexManager
from core.retrieval.bm25 import BM25Retriever
from core.retrieval.dense import DenseRetriever
from core.retrieval.fusion import reciprocal_rank_fusion, linear_score_fusion


class HybridRetrievalEngine:
    """
    High-performance hybrid retrieval coordinating multi-index BM25 and dense embedding search.
    """
    def __init__(
        self,
        index_manager: IndexManager,
        bm25_retriever: Optional[BM25Retriever] = None,
        dense_retriever: Optional[DenseRetriever] = None
    ):
        self.index_manager = index_manager
        self.bm25 = bm25_retriever or BM25Retriever(index_manager)
        self.dense = dense_retriever or DenseRetriever(index_manager)

    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",  # "bm25", "dense", "hybrid", "linear"
        top_k: int = 50,
        fusion_k: int = 60,
        alpha: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes retrieval with granular stage latency tracking.
        """
        t0 = time.perf_counter()
        
        # 1. Lexical BM25 stage
        t_bm25_start = time.perf_counter()
        bm25_results = self.bm25.retrieve(query, top_k=top_k, explain=True) if mode in ("bm25", "hybrid", "linear") else []
        bm25_latency_ms = (time.perf_counter() - t_bm25_start) * 1000.0

        # 2. Dense Semantic stage
        t_dense_start = time.perf_counter()
        dense_results = self.dense.retrieve(query, top_k=top_k) if mode in ("dense", "hybrid", "linear") else []
        dense_latency_ms = (time.perf_counter() - t_dense_start) * 1000.0

        # 3. Candidate Fusion stage
        t_fusion_start = time.perf_counter()
        if mode == "bm25":
            final_candidates = bm25_results[:top_k]
        elif mode == "dense":
            final_candidates = dense_results[:top_k]
        elif mode == "linear":
            final_candidates = linear_score_fusion(bm25_results, dense_results, alpha=alpha, top_k=top_k)
        else:  # default "hybrid" (RRF)
            final_candidates = reciprocal_rank_fusion(bm25_results, dense_results, k=fusion_k, top_k=top_k)
        fusion_latency_ms = (time.perf_counter() - t_fusion_start) * 1000.0

        total_latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "query": query,
            "mode": mode,
            "candidates": final_candidates,
            "counts": {
                "lexical_candidates": len(bm25_results),
                "dense_candidates": len(dense_results),
                "fused_candidates": len(final_candidates)
            },
            "latencies_ms": {
                "bm25": round(bm25_latency_ms, 3),
                "dense": round(dense_latency_ms, 3),
                "fusion": round(fusion_latency_ms, 3),
                "total": round(total_latency_ms, 3)
            }
        }
