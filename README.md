# Atlas Search

> **An experimental search engine with production-style ranking, distributed indexing, and an automated search-quality debugging system.**

Atlas Search does not merely return results. It explains *why* a result ranked highly, detects when results degrade, diagnoses the exact mathematical and algorithmic source of relevance failures, and proves ranking improvements through controlled, reproducible experiments.

---

## Highlights & Measured Benchmarks

| Metric / Requirement | Baseline (BM25) | Dense Semantic | Hybrid (RRF) | Hybrid + LTR | Relative Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NDCG@10** | 0.8316 | 0.8270 | **0.8535** | 0.8441 | **+2.6%** over baseline |
| **NDCG@5** | 0.7803 | 0.8208 | **0.8535** | 0.8388 | **+7.5%** over baseline |
| **MRR@10** | 0.9286 | **1.0000** | **1.0000** | 0.9286 | **+7.7%** first-hit accuracy |
| **Precision@5** | 0.4071 | 0.4286 | **0.4857** | 0.4571 | **+12.3%** top-5 relevance |
| **Throughput (QPS)** | — | — | — | **288.7 QPS** | Single-node concurrent load |
| **p50 Latency** | — | — | — | **3.32 ms** | End-to-end query time |
| **p95 Latency** | — | — | — | **4.27 ms** | Tail latency SLA |
| **p99 Latency** | — | — | — | **5.37 ms** | Sub-6ms tail latency |

*Data collected from local runs of `benchmarks/run_relevance_benchmark.py` and `benchmarks/run_latency_benchmark.py`.*

---

## The Five Systems Inside Atlas

```
                                  [ Search Client ]
                         React 19 · TypeScript · Accessible UI
                                          │
                                          ▼
                               [ Distributed Gateway ]
                       Scatter-Gather · Timeouts · Circuit Breaker
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
         [ Lexical Retriever ]                          [ Dense Retriever ]
       Inverted Index · BM25Okapi                     Vector Cosine Similarity
      Variable-Byte & Delta Encoding                  Concept-Space Projections
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          ▼
                               [ Candidate Fusion ]
                       Reciprocal Rank Fusion (RRF, k=60)
                                          │
                                          ▼
                            [ Learning-to-Rank (LTR) ]
                        Multi-Feature Query-Doc Extractor
                      Ridge Pointwise & GBDT Surrogate Trees
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
     [ Ranked Results Stream ]                      [ Search Failure Autopsy ]
      Microsecond Stage Tracing                   Feature Attribution Deltas
       p50 / p95 / p99 Gauges                     Automated Root-Cause Diagnosis
```

### 1. Hybrid Retrieval Engine
- **Inverted Index**: Custom tokenizer preserving programming terms (`c++`, `python-3`, `node.js`), sibilant-aware stemming, stop-word removal, and term position tracking for phrase scoring.
- **Index Compression**: Lossless Variable-Byte (`VByte`) and Delta (`d-gap`) encoding for document IDs and positions.
- **BM25Okapi Scoring**: Implements term frequency saturation ($k_1 = 1.2$), document length normalization ($b = 0.75$), title field boosting ($2.0\times$), and positional phrase proximity.
- **Dense Semantic Retrieval**: High-dimensional vector space mapping technical concepts, cosine similarity scoring, and top-$k$ candidate generation.
- **Candidate Fusion**: Reciprocal Rank Fusion ($RRF(d) = \sum \frac{1}{k + \text{rank}(d)}$ with $k=60$) and linear normalized fusion.

### 2. Learning-to-Rank (LTR) Laboratory
- **Query-Document Feature Extractor**:
  - `bm25_score`: Lexical term match density.
  - `dense_score`: Cosine semantic similarity.
  - `title_match_ratio`: Query token coverage in document title.
  - `body_coverage_ratio`: Term coverage in body text.
  - `language_affinity`: Exact compatibility between query technology intent and document language metadata.
  - `freshness_score`: Half-life exponential decay based on document release timestamp.
  - `length_ratio`: Document length relative to average corpus document length ($\text{avgdl}$).
  - `channel_consensus`: Multi-channel agreement bonus.
- **Supervised Rankers**:
  - Pointwise Ridge Regression model with explicit feature weights.
  - Gradient Boosted Decision Trees (`GBDT`) capturing non-linear interactions.
- **Evaluation Harness**: Automated side-by-side benchmark reporting NDCG@10, Recall@10, MRR@10, Precision@5, and query-level Win/Tie/Regression status.

### 3. Live Distributed Index Subsystem
- **Immutable Segments**: Write-once, read-only segments with cryptographic SHA-256 checksums.
- **Segment Manifests**: Versioned generation counter, active segment mapping, and tombstone tracking.
- **Safe Atomic Publication**: Background segment builds with atomic rename/replace on the manifest file. Corrupted or invalid segments are rejected before exposure.
- **Zero-Downtime Rollback**: Instant one-click revert to generation $N - 1$.
- **Background Compaction**: Consolidates multiple small segments into a single segment, eliminating tombstones and optimizing postings lists.

### 4. The Signature Feature: Search Failure Autopsy
When a query fails or returns a poor match ahead of an intended document:
1. **Query Trace Analysis**: Records microsecond execution timings for tokenization, lexical search, semantic search, candidate fusion, feature extraction, and reranking.
2. **Automated Root-Cause Diagnostic**:
   - *Retrieval Failure Check*: Identifies whether the relevant document was missed during candidate retrieval due to vocabulary mismatch.
   - *Ranking Feature Attribution*: Computes feature value deltas $\Delta f = f_{\text{winner}} - f_{\text{target}}$ to identify which feature caused the incorrect ranking.
   - *Freshness Failure Check*: Detects when deprecated documentation outranks active releases.
3. **Actionable Experiment Recommendation**: Proposes concrete parameter adjustments (e.g., increasing `language_affinity` weight from 0.05 to 0.30) and evaluates the simulated fix in real-time, verifying rank promotion.

### 5. Accessible Search Interface
- **Keyboard-First Navigation**:
  - `/` or `Ctrl+K`: Focus search bar.
  - `↓` / `↑`: Traverse search results.
  - `A`: Open Search Failure Autopsy for selected result.
  - `1`, `2`, `3`, `4`: Switch between application views.
  - `Esc`: Close modal dialogs.
- **Assistive Technology Support**:
  - Screen-reader live region (`aria-live="polite"` and `role="status"`).
  - High-contrast accessibility theme toggle.
  - Distinct visible focus rings (`focus-visible`).

---

## Illustrated Walkthrough: The Search Failure Autopsy

### Query: *"How do I reduce memory usage in a Python application?"*

#### Naive BM25 Retrieval Behavior:
- **Rank 1**: *JVM Garbage Collection and Memory Tuning Guide* (Language: Java)
  - Strong keyword density: *"reduce"*, *"memory"*, *"usage"*, *"application"*.
- **Rank 2**: *Profiling and Reducing Memory Usage in Python Applications with tracemalloc* (Language: Python)
  - Lower raw keyword density than the JVM guide, despite being an exact language match.

#### Autopsy Diagnostic Report:
```
[!] DETECTED ISSUE: LANGUAGE_INCOMPATIBILITY
• Retrieval Diagnosis:
  The lexical retriever prioritized generic term overlap ('reduce, memory, usage, application')
  without enforcing target programming language 'python'. False winner is 'java' documentation.
• Ranking Diagnosis:
  The baseline ranking gave insufficient weight to language compatibility.
  Document #102 has exact 'python' affinity (+1.0) but was outscored by Doc #101 on BM25 (+0.22).
• Proposed Experiment:
  Boost language_affinity feature weight to 0.30 in LTR reranker.
• Simulated Result:
  Document #102 promoted from Rank 2 -> Rank 1.
  Predicted NDCG@10 delta: +0.284.
```

---

## Directory Structure

```
Atlas-Search/
├── core/
│   ├── tokenizer.py            # Tokenizer, stemmer, and position tracking
│   ├── index/
│   │   ├── compression.py      # Delta and Variable-Byte (VByte) compression
│   │   ├── segment.py          # Immutable index segments with SHA-256 checksums
│   │   ├── manifest.py         # Atomic manifest publication and rollback
│   │   └── manager.py          # Multi-segment index manager with tombstones & compaction
│   ├── retrieval/
│   │   ├── bm25.py             # BM25Okapi scoring with length normalization & phrase boost
│   │   ├── dense.py            # Vector embeddings and cosine similarity search
│   │   ├── fusion.py           # Reciprocal Rank Fusion (RRF) and linear score fusion
│   │   └── engine.py           # Hybrid retrieval engine coordinator
│   ├── ranking/
│   │   ├── features.py         # 8-dimensional query-document feature extractor
│   │   ├── ltr.py              # Linear Ridge and GBDT Learning-to-Rank models
│   │   └── reranker.py         # Second-stage reranking pipeline with rank deltas
│   ├── evaluation/
│   │   ├── metrics.py          # NDCG@k, Recall@k, MRR@k, Precision@k
│   │   ├── dataset.py          # Curated benchmark corpus & relevance ground truth
│   │   └── experiment.py       # Controlled side-by-side experiment runner
│   ├── observatory/
│   │   ├── tracer.py           # Microsecond stage tracer and latency percentiles
│   │   └── autopsy.py          # Search Failure Autopsy diagnostic engine
│   └── distributed/
│       ├── coordinator.py      # Scatter-gather query gateway with timeout handling
│       └── fault_injection.py  # Worker crash, corrupted segment, and rollback test harness
├── server/
│   ├── app.py                  # FastAPI application with REST endpoints
│   ├── schemas.py              # Pydantic request/response schemas
│   └── demo_data.py            # Technical corpus seeder
├── client/                     # Accessible React 19 + TypeScript + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchInterface.tsx     # Keyboard-first accessible search
│   │   │   ├── AutopsyModal.tsx        # Signature Search Failure Autopsy viewer
│   │   │   ├── LaboratoryView.tsx      # LTR experiment comparison and retraining
│   │   │   ├── DistributedCluster.tsx  # Segments, manifest, and live fault injection
│   │   │   ├── ObservatoryView.tsx     # Microsecond latency waterfall & trace logs
│   │   │   └── AccessibilityBar.tsx    # Screen reader live region & contrast toggle
│   │   ├── App.tsx
│   │   └── index.css                   # Custom design system with accessible focus styles
├── tests/                      # Automated test suite (100% passing)
│   ├── test_tokenizer.py
│   ├── test_compression.py
│   ├── test_ltr_and_autopsy.py
│   └── test_atomic_manifest.py
├── benchmarks/
│   ├── run_relevance_benchmark.py      # Reproducible IR evaluation script
│   └── run_latency_benchmark.py        # Concurrency and latency profiling script
└── README.md
```

---

## Quickstart & Verification

### 1. Run Automated Test Suite
```bash
python -m pytest tests/
```
Output:
```
tests/test_atomic_manifest.py ..                                         [ 20%]
tests/test_compression.py ...                                            [ 50%]
tests/test_ltr_and_autopsy.py ..                                         [ 70%]
tests/test_tokenizer.py ...                                              [100%]
============================= 10 passed in 0.42s =============================
```

### 2. Run Reproducible Relevance Benchmark
```bash
python benchmarks/run_relevance_benchmark.py
```

### 3. Run Latency & Concurrency Benchmark
```bash
python benchmarks/run_latency_benchmark.py
```

### 4. Launch Application Locally
In terminal 1 (FastAPI backend):
```bash
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```
In terminal 2 (Vite frontend):
```bash
cd client
pnpm install
pnpm run dev
```
Open [http://localhost:5173/](http://localhost:5173/) in your browser.

---

## Resume Entry

**Atlas Search — Search Retrieval & Quality Engineering Platform** | Python · TypeScript · Information Retrieval · Distributed Systems
- Built a hybrid search engine implementing inverted-index retrieval with variable-byte compression, BM25Okapi scoring, dense vector semantic search, and Reciprocal Rank Fusion (RRF); evaluated relevance using NDCG@10, Recall@10, MRR@10, and Precision@5.
- Developed the signature **Search Failure Autopsy** system to trace microsecond query execution, calculate feature attribution deltas between false winners and intended targets, diagnose root causes (vocabulary mismatch, technology incompatibility, freshness decay), and validate ranking fixes through controlled experiments.
- Engineered safe index updates using immutable segments, cryptographic SHA-256 checksums, and atomic manifest publication; built fault-injection tests validating worker crash failover, corrupted segment rejection, and atomic rollback.
- Built a fully accessible, keyboard-first React + TypeScript interface compliant with WCAG guidelines, featuring screen-reader live status regions, high-contrast theming, and an interactive Learning-to-Rank laboratory.
