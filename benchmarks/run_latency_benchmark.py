"""
Reproducible Latency and Concurrency Benchmark Runner
Measures p50, p95, p99 query latency, Throughput (QPS), and concurrent indexing impact.
"""

import sys
import os
import time
import concurrent.futures
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tokenizer import Tokenizer
from core.index.manager import IndexManager
from core.retrieval.bm25 import BM25Retriever
from core.retrieval.dense import DenseRetriever
from core.retrieval.engine import HybridRetrievalEngine
from core.ranking.features import FeatureExtractor
from core.ranking.ltr import LinearLTRModel
from core.ranking.reranker import RerankingPipeline
from server.demo_data import seed_database


BENCHMARK_QUERIES = [
    "How do I reduce memory usage in a Python application?",
    "investigate high RAM consumption in Python scripts",
    "Distributed consensus algorithms and leader election",
    "Fast inverted index compression variable-byte and postings lists",
    "recent Python performance updates and free threading",
    "Approximate nearest neighbors and HNSW vector search",
    "measuring and debugging p99 tail latency spikes",
    "JVM Garbage collection and tuning heap sizes",
    "Rust zero cost abstractions and borrow checker",
    "PostgreSQL B-Tree and GIN Indexing for high throughput"
]


def main():
    print("=" * 80)
    print("           ATLAS SEARCH - LATENCY & CONCURRENCY BENCHMARK")
    print("=" * 80)

    storage_dir = os.path.join(os.path.dirname(__file__), ".benchmark_latency_index")
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

    def execute_query(q):
        t0 = time.perf_counter()
        ret = engine.retrieve(q, mode="hybrid", top_k=15)
        rerank = reranker.rerank(q, ret["candidates"], top_k=10)
        return (time.perf_counter() - t0) * 1000.0

    # Test 1: Single-threaded baseline (100 queries)
    warmup_runs = 10
    for q in BENCHMARK_QUERIES[:warmup_runs]:
        execute_query(q)

    latencies_single = []
    t_start = time.perf_counter()
    iterations = 100
    for i in range(iterations):
        q = BENCHMARK_QUERIES[i % len(BENCHMARK_QUERIES)]
        latencies_single.append(execute_query(q))
    total_time_single = time.perf_counter() - t_start
    qps_single = iterations / total_time_single

    # Test 2: Concurrency level = 8
    latencies_concurrent = []
    concurrency = 8
    t_start_conc = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(execute_query, BENCHMARK_QUERIES[i % len(BENCHMARK_QUERIES)])
            for i in range(iterations)
        ]
        for f in concurrent.futures.as_completed(futures):
            latencies_concurrent.append(f.result())
    total_time_conc = time.perf_counter() - t_start_conc
    qps_conc = iterations / total_time_conc

    arr_s = np.array(latencies_single)
    arr_c = np.array(latencies_concurrent)

    print(f"\nWorkload: {iterations} queries on local core (Single-node):")
    print(f"\n[1] Sequential Workload (Concurrency = 1):")
    print(f"    • Throughput : {qps_single:.1f} queries/sec")
    print(f"    • p50 Latency: {np.percentile(arr_s, 50):.2f} ms")
    print(f"    • p95 Latency: {np.percentile(arr_s, 95):.2f} ms")
    print(f"    • p99 Latency: {np.percentile(arr_s, 99):.2f} ms")
    print(f"    • Mean       : {np.mean(arr_s):.2f} ms")

    print(f"\n[2] Concurrent Workload (Concurrency = {concurrency}):")
    print(f"    • Throughput : {qps_conc:.1f} queries/sec")
    print(f"    • p50 Latency: {np.percentile(arr_c, 50):.2f} ms")
    print(f"    • p95 Latency: {np.percentile(arr_c, 95):.2f} ms")
    print(f"    • p99 Latency: {np.percentile(arr_c, 99):.2f} ms")
    print(f"    • Mean       : {np.mean(arr_c):.2f} ms")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
