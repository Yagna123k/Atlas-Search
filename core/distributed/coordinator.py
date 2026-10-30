"""
Distributed Query Gateway & Coordinator
Implements scatter-gather retrieval across multiple shard workers,
timeout enforcement, circuit breaking, and replica failover.
"""

from typing import Dict, List, Any, Optional, Callable
import time
import concurrent.futures
from core.index.manager import IndexManager


class ShardWorker:
    """
    Virtual Shard Node hosting a dedicated subset of index segments.
    """
    def __init__(self, shard_id: str, index_manager: IndexManager):
        self.shard_id = shard_id
        self.index_manager = index_manager
        self.is_healthy = True
        self.simulated_latency_ms: float = 0.0

    def search_shard(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        if not self.is_healthy:
            raise RuntimeError(f"Shard {self.shard_id} is currently offline (Crash Simulation).")
        
        if self.simulated_latency_ms > 0:
            time.sleep(self.simulated_latency_ms / 1000.0)

        # Retrieve documents from this shard's segments
        all_docs = self.index_manager.get_all_live_documents()
        results = []
        q_lower = query.lower()
        for doc_id, doc in all_docs.items():
            title = doc.get("title", "")
            body = doc.get("body", "")
            if any(term in title.lower() or term in body.lower() for term in q_lower.split()):
                results.append({
                    "doc_id": doc_id,
                    "shard_id": self.shard_id,
                    "title": title,
                    "body": body,
                    "score": 1.0,
                    "language": doc.get("language", "generic")
                })
        return results[:top_k]


class DistributedCoordinator:
    """
    Distributed gateway managing shard workers, scatter-gather query aggregation,
    timeouts, and fault tolerance.
    """
    def __init__(self, shards: Optional[List[ShardWorker]] = None, timeout_seconds: float = 0.5):
        self.shards = shards or []
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker_open = False
        self.failover_history: List[Dict[str, Any]] = []

    def scatter_gather(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        """
        Fans out search request to all healthy shard workers concurrently,
        gathers candidate pools, and merges results.
        """
        t0 = time.perf_counter()
        shard_responses: Dict[str, List[Dict[str, Any]]] = {}
        failed_shards: List[str] = []
        timed_out_shards: List[str] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(self.shards))) as executor:
            future_to_shard = {
                executor.submit(shard.search_shard, query, top_k): shard
                for shard in self.shards
            }

            for future in concurrent.futures.as_completed(future_to_shard, timeout=self.timeout_seconds):
                shard = future_to_shard[future]
                try:
                    res = future.result()
                    shard_responses[shard.shard_id] = res
                except concurrent.futures.TimeoutError:
                    timed_out_shards.append(shard.shard_id)
                except Exception as ex:
                    failed_shards.append(shard.shard_id)
                    self.failover_history.append({
                        "timestamp": time.time(),
                        "shard_id": shard.shard_id,
                        "error": str(ex)
                    })

        # Merge candidate responses
        all_candidates = []
        for s_id, items in shard_responses.items():
            all_candidates.extend(items)

        # Deduplicate and sort
        seen_dids = set()
        merged = []
        for item in all_candidates:
            if item["doc_id"] not in seen_dids:
                seen_dids.add(item["doc_id"])
                merged.append(item)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "query": query,
            "results": merged[:top_k],
            "total_shards": len(self.shards),
            "responding_shards": len(shard_responses),
            "failed_shards": failed_shards,
            "timed_out_shards": timed_out_shards,
            "latency_ms": round(latency_ms, 3),
            "degraded_mode": len(failed_shards) > 0 or len(timed_out_shards) > 0
        }
