"""
Reproducible Relevance Benchmark Runner
Evaluates BM25, Dense, Hybrid (RRF), and Hybrid + LTR Reranker
against standard information retrieval metrics: NDCG@10, Recall@10, MRR@10, Precision@5.
"""

import sys
import os
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tokenizer import Tokenizer
from core.index.manager import IndexManager
from core.retrieval.bm25 import BM25Retriever
from core.retrieval.dense import DenseRetriever
from core.retrieval.engine import HybridRetrievalEngine
from core.ranking.features import FeatureExtractor
from core.ranking.ltr import LinearLTRModel
from core.ranking.reranker import RerankingPipeline
from core.evaluation.experiment import ExperimentRunner
from server.demo_data import seed_database


def main():
    print("=" * 80)
    print("           ATLAS SEARCH - REPRODUCIBLE RELEVANCE BENCHMARK")
    print("=" * 80)
    
    storage_dir = os.path.join(os.path.dirname(__file__), ".benchmark_index")
    tokenizer = Tokenizer()
    index_manager = IndexManager(storage_dir=storage_dir, tokenizer=tokenizer)
    seed_database(index_manager)

    bm25 = BM25Retriever(index_manager)
    dense = DenseRetriever(index_manager)
    dense.sync_vectors()

    engine = HybridRetrievalEngine(index_manager, bm25_retriever=bm25, dense_retriever=dense)
    features = FeatureExtractor(tokenizer=tokenizer)
    ltr = LinearLTRModel()
    reranker = RerankingPipeline(ltr_model=ltr, feature_extractor=features)

    runner = ExperimentRunner(retrieval_engine=engine, reranker=reranker)
    
    t0 = time.time()
    results = runner.run_benchmark(top_k=10)
    elapsed = time.time() - t0

    metrics = ["ndcg@10", "ndcg@5", "recall@10", "mrr@10", "precision@5"]
    strategies = ["bm25", "dense", "hybrid", "hybrid_ltr"]
    headers = ["Strategy", "NDCG@10", "NDCG@5", "Recall@10", "MRR@10", "P@5"]

    print(f"\nEvaluated {results['num_queries']} benchmark queries across 4 pipeline configurations in {elapsed:.2f}s:\n")
    
    # Table header
    row_fmt = "{:<16} | {:<10} | {:<10} | {:<10} | {:<10} | {:<10}"
    print(row_fmt.format(*headers))
    print("-" * 75)

    for s in strategies:
        m = results["summary_metrics"][s]
        display_name = {
            "bm25": "1. BM25 Baseline",
            "dense": "2. Dense Semantic",
            "hybrid": "3. Hybrid (RRF)",
            "hybrid_ltr": "4. Hybrid + LTR"
        }[s]
        print(row_fmt.format(
            display_name,
            f"{m['ndcg@10']:.4f}",
            f"{m['ndcg@5']:.4f}",
            f"{m['recall@10']:.4f}",
            f"{m['mrr@10']:.4f}",
            f"{m['precision@5']:.4f}"
        ))

    print("-" * 75)
    print("\n[+] Relative Improvement of (Hybrid + LTR) over BM25 Baseline:")
    for k, v in results["relative_improvements_over_bm25"].items():
        print(f"    • {k.upper():<12}: {v}")

    print("\n[+] Query-Level Ranking Breakdown:")
    for qb in results["query_breakdown"]:
        delta_str = f"+{qb['delta_ndcg@10']:.4f}" if qb['delta_ndcg@10'] >= 0 else f"{qb['delta_ndcg@10']:.4f}"
        status = "WIN" if qb['delta_ndcg@10'] > 0 else ("TIE" if qb['delta_ndcg@10'] == 0 else "REGRESSION")
        print(f"    [{status:<10}] Query: \"{qb['query'][:45]}...\" | BM25 NDCG: {qb['bm25_ndcg@10']:.3f} -> LTR NDCG: {qb['hybrid_ltr_ndcg@10']:.3f} ({delta_str})")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
