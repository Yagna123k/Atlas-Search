"""
Curated Benchmark Dataset and Relevance Judgments
Contains realistic engineering documents and labelled test queries
with multi-grade relevance judgments (0 = irrelevant, 1 = marginal, 2 = relevant, 3 = perfect match).
"""

from typing import Dict, List, Any


BENCHMARK_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": 101,
        "title": "JVM Garbage Collection and Memory Tuning Guide",
        "body": "Techniques for tuning JVM heap memory, Young generation allocations, G1GC tuning flags, and reducing memory usage in large Java microservices applications.",
        "language": "java",
        "timestamp": 1700000000,
        "tags": ["java", "jvm", "gc", "memory", "performance"]
    },
    {
        "id": 102,
        "title": "Profiling and Reducing Memory Usage in Python Applications with tracemalloc",
        "body": "Comprehensive guide to reducing memory usage in Python applications. Learn how to profile object allocations, track memory leaks using tracemalloc and memory_profiler, and reduce heap footprints.",
        "language": "python",
        "timestamp": 1720000000,
        "tags": ["python", "memory", "profiling", "tracemalloc", "optimization"]
    },
    {
        "id": 103,
        "title": "Rust Memory Safety: Ownership, Borrowing, and Lifetimes",
        "body": "How Rust eliminates garbage collection overhead and data races using zero-cost abstractions, deterministic destructor calls, and strict compile-time borrow checking.",
        "language": "rust",
        "timestamp": 1715000000,
        "tags": ["rust", "memory", "ownership", "concurrency"]
    },
    {
        "id": 104,
        "title": "Go Memory Allocator and Garbage Collector Internals",
        "body": "In-depth breakdown of Go TCMalloc-based memory allocator, mcache, mcentral, mheap arenas, and the tri-color mark-sweep concurrent collector.",
        "language": "go",
        "timestamp": 1710000000,
        "tags": ["go", "golang", "gc", "memory", "runtime"]
    },
    {
        "id": 105,
        "title": "Distributed Consensus: Raft Protocol Implementation and Leader Election",
        "body": "Practical implementation of the Raft distributed consensus algorithm. Details on randomized election timeouts, log replication, commit indexes, and handling network partitions in distributed clusters.",
        "language": "distributed",
        "timestamp": 1718000000,
        "tags": ["distributed", "consensus", "raft", "fault-tolerance"]
    },
    {
        "id": 106,
        "title": "Paxos Made Live: Engineering State Machine Replication at Scale",
        "body": "Case study on implementing multi-Paxos for high-availability distributed storage, master leases, disk corruption recovery, and active replication.",
        "language": "distributed",
        "timestamp": 1695000000,
        "tags": ["distributed", "consensus", "paxos", "replication"]
    },
    {
        "id": 107,
        "title": "Building Fast Inverted Indexes with Elias-Fano and Variable-Byte Compression",
        "body": "Algorithms for postings list compression in search retrieval engines. Explores Variable-Byte encoding, d-gaps, Elias-Fano quasi-succinct structures, and SIMD integer decoding.",
        "language": "ir",
        "timestamp": 1722000000,
        "tags": ["search", "indexing", "compression", "algorithms", "c++"]
    },
    {
        "id": 108,
        "title": "Modern BM25 Retrieval and Lucene Score Saturation Parameters",
        "body": "Mathematical breakdown of BM25Okapi scoring function. Tuning term frequency saturation k1 and document length normalization parameter b for enterprise search.",
        "language": "ir",
        "timestamp": 1712000000,
        "tags": ["search", "bm25", "retrieval", "scoring", "information-retrieval"]
    },
    {
        "id": 109,
        "title": "PostgreSQL B-Tree and GIN Indexing for High-Throughput Search",
        "body": "Optimizing relational database search using PostgreSQL Generalized Inverted Indexes (GIN), tsvector full-text search, and query plan execution tuning.",
        "language": "sql",
        "timestamp": 1708000000,
        "tags": ["postgres", "sql", "indexing", "database"]
    },
    {
        "id": 110,
        "title": "Python 3.13 Free-Threaded CPython Build and Sub-Interpreter Guide",
        "body": "Recent release features in Python 3.13: disabling the Global Interpreter Lock (no-GIL), multi-core CPU scaling for parallel Python applications, and memory management updates.",
        "language": "python",
        "timestamp": 1728000000,  # Recent / fresh
        "tags": ["python", "cpython", "gil", "threading", "performance", "fresh"]
    },
    {
        "id": 111,
        "title": "Python 2.7 Memory Leak Debugging Guide (Deprecated)",
        "body": "Legacy troubleshooting for memory leaks in old Python 2.7 services using objgraph and heapy. Note: Python 2.7 reached End-of-Life in 2020.",
        "language": "python",
        "timestamp": 1500000000,  # Very old / outdated
        "tags": ["python", "legacy", "deprecated", "memory"]
    },
    {
        "id": 112,
        "title": "Learning-to-Rank for Search Engines: LambdaMART and GBDT Reranking",
        "body": "Applying supervised machine learning to search ranking. Train gradient boosted decision trees (GBDT) and pairwise RankNet algorithms using query-document feature vectors.",
        "language": "ir",
        "timestamp": 1719000000,
        "tags": ["search", "ranking", "ltr", "machine-learning"]
    },
    {
        "id": 113,
        "title": "Fast Vector Search and Approximate Nearest Neighbors with HNSW",
        "body": "Hierarchical Navigable Small World (HNSW) graphs for dense vector retrieval. Trade-offs between search latency, recall accuracy, and memory consumption in semantic search.",
        "language": "ir",
        "timestamp": 1724000000,
        "tags": ["vector-search", "embeddings", "hnsw", "semantic-search"]
    },
    {
        "id": 114,
        "title": "Diagnosing High Latency Spikes and p99 Tail Latency in Distributed Systems",
        "body": "Techniques for tracking p95 and p99 tail latency in distributed microservices: queue queuing delay, thread starvation, GC pauses, and kernel page allocation bottlenecks.",
        "language": "systems",
        "timestamp": 1716000000,
        "tags": ["systems", "latency", "observability", "distributed"]
    },
    {
        "id": 115,
        "title": "Zero-Downtime Database Migrations and Atomic Schema Updates",
        "body": "Pattern for safe online schema evolution in high-traffic applications. Expand-and-contract pattern, dual writes, backwards-compatible columns, and rollback plans.",
        "language": "systems",
        "timestamp": 1709000000,
        "tags": ["database", "migrations", "reliability", "architecture"]
    }
]


BENCHMARK_QUERIES: List[Dict[str, Any]] = [
    {
        "id": "q1_python_memory",
        "query": "How do I reduce memory usage in a Python application?",
        "category": "language_relevance_disambiguation",
        "description": "Crucial autopsy test: Naive BM25 ranks JVM doc #1 due to term density. LTR promotes Python doc to #1.",
        "ground_truth": {
            102: 3.0,  # Profiling and Reducing Memory Usage in Python Applications
            110: 2.0,  # Python 3.13 Free-threaded and memory updates
            101: 0.0,  # JVM tuning guide (irrelevant language)
            111: 1.0,  # Old Python 2.7 guide
            104: 0.0,
        }
    },
    {
        "id": "q2_python_ram_paraphrased",
        "query": "investigate high RAM consumption in Python scripts",
        "category": "semantic_paraphrasing",
        "description": "Paraphrased query: 'RAM consumption' vs 'memory usage'. Dense/hybrid excels.",
        "ground_truth": {
            102: 3.0,
            110: 2.0,
            101: 0.0,
            111: 1.0,
        }
    },
    {
        "id": "q3_distributed_consensus",
        "query": "Distributed consensus algorithms and leader election",
        "category": "domain_systems",
        "description": "Retrieves Raft and Paxos implementations with high relevance.",
        "ground_truth": {
            105: 3.0,  # Raft Protocol
            106: 3.0,  # Paxos Made Live
            114: 1.0,  # Distributed systems tail latency
            107: 0.0,
        }
    },
    {
        "id": "q4_index_compression",
        "query": "Fast inverted index compression variable-byte and postings lists",
        "category": "information_retrieval_specific",
        "description": "Exact IR terms. Tests BM25 and keyword precision.",
        "ground_truth": {
            107: 3.0,  # Elias-Fano and Variable-Byte
            108: 2.0,  # Modern BM25 retrieval
            112: 1.0,  # LTR for search
            109: 1.0,  # Postgres GIN
        }
    },
    {
        "id": "q5_python_freshness",
        "query": "recent Python performance updates and free threading",
        "category": "freshness_sensitive",
        "description": "Tests freshness signal: Python 3.13 (recent) must score higher than legacy 2.7 doc.",
        "ground_truth": {
            110: 3.0,  # Python 3.13 (Fresh)
            102: 2.0,  # Python memory profiling
            111: 0.0,  # Python 2.7 (Old)
        }
    },
    {
        "id": "q6_vector_similarity",
        "query": "Approximate nearest neighbors and HNSW vector search",
        "category": "semantic_ir",
        "description": "Dense search methods and graph ANN algorithms.",
        "ground_truth": {
            113: 3.0,  # Fast Vector Search HNSW
            112: 1.0,  # LTR
            107: 1.0,  # Inverted index
        }
    },
    {
        "id": "q7_p99_tail_latency",
        "query": "measuring and debugging p99 tail latency spikes",
        "category": "systems_observability",
        "description": "Systems engineering latency profiling.",
        "ground_truth": {
            114: 3.0,  # Diagnosing High Latency Spikes and p99
            105: 1.0,  # Distributed consensus
            101: 1.0,  # JVM GC pauses
        }
    }
]
