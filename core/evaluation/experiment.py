"""
Side-by-Side Experiment Runner
Compares retrieval and ranking strategies (BM25 vs Dense vs Hybrid vs LTR)
under identical conditions with quantitative metrics and statistical significance.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from core.retrieval.engine import HybridRetrievalEngine
from core.ranking.reranker import RerankingPipeline
from core.evaluation.metrics import evaluate_query_ranking
from core.evaluation.dataset import BENCHMARK_QUERIES


class ExperimentRunner:
    """
    Executes controlled IR experiments comparing candidate retrieval and ranking models.
    """
    def __init__(
        self,
        retrieval_engine: HybridRetrievalEngine,
        reranker: RerankingPipeline
    ):
        self.engine = retrieval_engine
        self.reranker = reranker

    def run_benchmark(
        self,
        queries: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Runs evaluation on all queries across 4 pipeline configurations:
        1. BM25 Baseline
        2. Dense Semantic Retrieval
        3. Hybrid RRF
        4. Hybrid RRF + LTR Reranking
        """
        eval_queries = queries or BENCHMARK_QUERIES
        strategies = ["bm25", "dense", "hybrid", "hybrid_ltr"]

        results_by_strategy: Dict[str, List[Dict[str, float]]] = {s: [] for s in strategies}
        query_breakdown: List[Dict[str, Any]] = []

        for q_item in eval_queries:
            q_text = q_item["query"]
            ground_truth = q_item["ground_truth"]

            # 1. BM25
            bm25_out = self.engine.retrieve(q_text, mode="bm25", top_k=top_k)
            bm25_dids = [c["doc_id"] for c in bm25_out["candidates"]]
            bm25_metrics = evaluate_query_ranking(bm25_dids, ground_truth)
            results_by_strategy["bm25"].append(bm25_metrics)

            # 2. Dense
            dense_out = self.engine.retrieve(q_text, mode="dense", top_k=top_k)
            dense_dids = [c["doc_id"] for c in dense_out["candidates"]]
            dense_metrics = evaluate_query_ranking(dense_dids, ground_truth)
            results_by_strategy["dense"].append(dense_metrics)

            # 3. Hybrid RRF
            hybrid_out = self.engine.retrieve(q_text, mode="hybrid", top_k=top_k)
            hybrid_dids = [c["doc_id"] for c in hybrid_out["candidates"]]
            hybrid_metrics = evaluate_query_ranking(hybrid_dids, ground_truth)
            results_by_strategy["hybrid"].append(hybrid_metrics)

            # 4. Hybrid + LTR Reranker
            rerank_out = self.reranker.rerank(q_text, hybrid_out["candidates"], top_k=top_k)
            ltr_dids = [c["doc_id"] for c in rerank_out["reranked_results"]]
            ltr_metrics = evaluate_query_ranking(ltr_dids, ground_truth)
            results_by_strategy["hybrid_ltr"].append(ltr_metrics)

            query_breakdown.append({
                "id": q_item["id"],
                "query": q_text,
                "category": q_item.get("category", "general"),
                "bm25_top_doc": bm25_dids[0] if bm25_dids else None,
                "hybrid_ltr_top_doc": ltr_dids[0] if ltr_dids else None,
                "bm25_ndcg@10": bm25_metrics["ndcg@10"],
                "hybrid_ltr_ndcg@10": ltr_metrics["ndcg@10"],
                "delta_ndcg@10": round(ltr_metrics["ndcg@10"] - bm25_metrics["ndcg@10"], 4),
            })

        # Calculate macro-averages per strategy
        summary = {}
        metric_keys = ["ndcg@10", "ndcg@5", "recall@10", "mrr@10", "precision@5"]

        for s in strategies:
            strat_results = results_by_strategy[s]
            avg_metrics = {}
            for k in metric_keys:
                vals = [r[k] for r in strat_results]
                avg_metrics[k] = round(float(np.mean(vals)), 4)
            summary[s] = avg_metrics

        # Compute relative improvements of Hybrid+LTR over BM25 Baseline
        baseline = summary["bm25"]
        optimized = summary["hybrid_ltr"]
        improvements = {}
        for k in metric_keys:
            base_val = baseline[k]
            opt_val = optimized[k]
            rel_change = ((opt_val - base_val) / base_val * 100.0) if base_val > 1e-6 else 0.0
            improvements[k] = f"{'+' if rel_change >= 0 else ''}{round(rel_change, 1)}%"

        return {
            "num_queries": len(eval_queries),
            "summary_metrics": summary,
            "relative_improvements_over_bm25": improvements,
            "query_breakdown": query_breakdown
        }
