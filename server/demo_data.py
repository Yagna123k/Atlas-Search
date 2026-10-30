"""
Initial Corpus and Multi-Segment Seeder for Atlas Search
Populates multiple immutable segments with realistic technical documentation.
"""

from typing import List, Dict, Any
from core.evaluation.dataset import BENCHMARK_DOCUMENTS
from core.index.manager import IndexManager

ADDITIONAL_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": 201,
        "title": "Understanding Python's Global Interpreter Lock (GIL) and Multiprocessing",
        "body": "The GIL prevents true multi-threaded CPU execution in CPython. Learn when to use multiprocessing, concurrent.futures.ProcessPoolExecutor, or native C-extensions.",
        "language": "python",
        "timestamp": 1714000000,
        "tags": ["python", "concurrency", "gil", "multiprocessing"]
    },
    {
        "id": 202,
        "title": "Asynchronous I/O Programming with Python asyncio and uvloop",
        "body": "Building high-concurrency event loops in Python with asyncio and libuv. Handling thousands of persistent WebSockets and HTTP requests with minimal thread overhead.",
        "language": "python",
        "timestamp": 1717000000,
        "tags": ["python", "asyncio", "uvloop", "networking"]
    },
    {
        "id": 203,
        "title": "Java Virtual Machine (JVM) JIT Compilation: C1, C2, and GraalVM",
        "body": "How OpenJDK HotSpot compiles bytecode to native assembly. Tiered compilation, loop unrolling, escape analysis, and GraalVM Ahead-Of-Time (AOT) native images.",
        "language": "java",
        "timestamp": 1705000000,
        "tags": ["java", "jvm", "jit", "graalvm"]
    },
    {
        "id": 204,
        "title": "Rust Async Runtime Architecture: Tokio Tasks, Epoll, and Work Stealing",
        "body": "Deep dive into Tokio's cooperative multi-threaded task scheduler, crossbeam queues, and non-blocking Linux epoll registration for high-performance network services.",
        "language": "rust",
        "timestamp": 1721000000,
        "tags": ["rust", "tokio", "async", "networking"]
    },
    {
        "id": 205,
        "title": "Go Channels, Select Multiplexing, and Goroutine Leak Prevention",
        "body": "Common patterns for Go concurrency: buffered channels, fan-out/fan-in workers, context.Context cancellation, and avoiding goroutine leaks in production services.",
        "language": "go",
        "timestamp": 1711000000,
        "tags": ["go", "golang", "concurrency", "channels"]
    },
    {
        "id": 206,
        "title": "Designing LSM-Tree Storage Engines for Write-Heavy Workloads",
        "body": "Architecture of Log-Structured Merge-trees (LSM): MemTable, Write-Ahead Log (WAL), SSTable flush, Bloom filters, and Size-Tiered vs Leveled compaction strategies.",
        "language": "systems",
        "timestamp": 1723000000,
        "tags": ["storage", "lsm", "database", "rocksdb"]
    },
    {
        "id": 207,
        "title": "Distributed Tracing and OpenTelemetry: Spans, Context Propagation, and Sampling",
        "body": "Implementing distributed context propagation using W3C TraceContext headers. Reducing storage cost with tail-based trace sampling and Jaeger visualization.",
        "language": "systems",
        "timestamp": 1719500000,
        "tags": ["observability", "opentelemetry", "tracing", "distributed"]
    },
    {
        "id": 208,
        "title": "C++ Memory Models and Lock-Free Queue Architectures",
        "body": "Exploring std::memory_order_relaxed, acquire, and release semantics. Designing single-producer single-consumer lock-free ring buffers using atomic cacheline-aligned pointers.",
        "language": "c++",
        "timestamp": 1725000000,
        "tags": ["c++", "concurrency", "lock-free", "memory-model"]
    },
    {
        "id": 209,
        "title": "Vector Embeddings and Approximate Nearest Neighbors: IVF-PQ Indexing",
        "body": "Inverted File with Product Quantization (IVF-PQ) for million-scale vector retrieval. Compressing 1536-dimensional vectors into compact byte codes for low-RAM search.",
        "language": "ir",
        "timestamp": 1727000000,
        "tags": ["vector-search", "embeddings", "compression", "ann"]
    },
    {
        "id": 210,
        "title": "Kubernetes Pod Scheduling, Affinity Rules, and Resource Limits",
        "body": "Configuring CPU and memory requests/limits in Kubernetes. How kube-scheduler scores nodes using inter-pod anti-affinity, taints, and cgroups v2 OOM killing.",
        "language": "devops",
        "timestamp": 1713000000,
        "tags": ["kubernetes", "devops", "cloud", "containers"]
    }
]


def seed_database(index_manager: IndexManager) -> None:
    """
    Seeds initial documents across 3 separate immutable segments
    to demonstrate multi-segment index architecture.
    """
    # Segment 1: Benchmark documents 101 to 108
    for doc in BENCHMARK_DOCUMENTS[:8]:
        meta = {k: v for k, v in doc.items() if k not in ("id", "title", "body")}
        index_manager.index_document(doc["id"], doc["title"], doc["body"], meta)
    index_manager.commit()

    # Segment 2: Benchmark documents 109 to 115
    for doc in BENCHMARK_DOCUMENTS[8:]:
        meta = {k: v for k, v in doc.items() if k not in ("id", "title", "body")}
        index_manager.index_document(doc["id"], doc["title"], doc["body"], meta)
    index_manager.commit()

    # Segment 3: Additional technical systems documents
    for doc in ADDITIONAL_DOCUMENTS:
        meta = {k: v for k, v in doc.items() if k not in ("id", "title", "body")}
        index_manager.index_document(doc["id"], doc["title"], doc["body"], meta)
    index_manager.commit()
