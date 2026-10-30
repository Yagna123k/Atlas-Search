"""
Microsecond-Level Query Execution Tracer & Latency Observatory
Records granular stage timings, candidate pipelines, and sliding-window p50/p95/p99 latencies.
"""

from typing import Dict, List, Any, Optional
import time
import uuid
import numpy as np


class QueryTrace:
    """Detailed microsecond-level trace for a single query execution."""
    def __init__(self, query_id: str, query: str):
        self.query_id = query_id
        self.query = query
        self.start_time = time.perf_counter()
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.total_latency_ms: float = 0.0
        self.metadata: Dict[str, Any] = {}

    def record_stage(self, stage_name: str, duration_ms: float, details: Optional[Dict[str, Any]] = None) -> None:
        self.stages[stage_name] = {
            "duration_ms": round(duration_ms, 3),
            "details": details or {}
        }

    def finish(self) -> Dict[str, Any]:
        self.total_latency_ms = round((time.perf_counter() - self.start_time) * 1000.0, 3)
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query,
            "total_latency_ms": self.total_latency_ms,
            "stages": self.stages,
            "metadata": self.metadata
        }


class SearchQualityObservatory:
    """
    Observatory tracking query traces, latency percentiles (p50, p95, p99),
    throughput, and regression alerts.
    """
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.traces: List[Dict[str, Any]] = []
        self.latencies: List[float] = []

    def start_trace(self, query: str) -> QueryTrace:
        qid = f"trace_{uuid.uuid4().hex[:8]}"
        return QueryTrace(query_id=qid, query=query)

    def log_trace(self, trace_dict: Dict[str, Any]) -> None:
        self.traces.append(trace_dict)
        self.latencies.append(trace_dict.get("total_latency_ms", 0.0))
        if len(self.traces) > self.max_history:
            self.traces.pop(0)
            self.latencies.pop(0)

    def get_latency_percentiles(self) -> Dict[str, float]:
        """Calculates p50, p95, p99, min, and max latencies in milliseconds."""
        if not self.latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "count": 0}
        
        arr = np.array(self.latencies)
        return {
            "p50": round(float(np.percentile(arr, 50)), 2),
            "p95": round(float(np.percentile(arr, 95)), 2),
            "p99": round(float(np.percentile(arr, 99)), 2),
            "avg": round(float(np.mean(arr)), 2),
            "count": len(self.latencies)
        }

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self.traces[-limit:]))
