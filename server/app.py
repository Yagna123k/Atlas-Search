"""
FastAPI Server for Atlas Search
Exposes endpoints for retrieval, search quality observatory, learning-to-rank experiments,
search failure autopsy, and cluster fault injection.
"""

from typing import Dict, List, Any, Optional
import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.tokenizer import Tokenizer
from core.index.manager import IndexManager
from core.retrieval.bm25 import BM25Retriever
from core.retrieval.dense import DenseRetriever
from core.retrieval.engine import HybridRetrievalEngine
from core.ranking.features import FeatureExtractor
from core.ranking.ltr import LinearLTRModel, GBDTLTRModel
from core.ranking.reranker import RerankingPipeline
from core.evaluation.dataset import BENCHMARK_QUERIES
from core.evaluation.experiment import ExperimentRunner
from core.observatory.tracer import SearchQualityObservatory
from core.observatory.autopsy import SearchFailureAutopsy
from core.distributed.fault_injection import FaultInjectionHarness
from server.schemas import SearchRequest, AutopsyRequest, TrainLTRRequest, DocumentIngestRequest
from server.demo_data import seed_database

# Setup application directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "data", "index_store")

app = FastAPI(
    title="Atlas Search Engine API",
    description="Search Retrieval, Ranking Laboratory, and Failure Autopsy Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Engine Components
tokenizer = Tokenizer()
index_manager = IndexManager(storage_dir=STORAGE_DIR, tokenizer=tokenizer)

# Seed documents if empty
if index_manager.manifest_manager.current_manifest.total_live_docs == 0:
    seed_database(index_manager)

bm25_retriever = BM25Retriever(index_manager)
dense_retriever = DenseRetriever(index_manager)
dense_retriever.sync_vectors()

hybrid_engine = HybridRetrievalEngine(
    index_manager=index_manager,
    bm25_retriever=bm25_retriever,
    dense_retriever=dense_retriever
)

feature_extractor = FeatureExtractor(tokenizer=tokenizer)
ltr_model = LinearLTRModel()
reranker = RerankingPipeline(ltr_model=ltr_model, feature_extractor=feature_extractor)

observatory = SearchQualityObservatory(max_history=500)
autopsy_engine = SearchFailureAutopsy(
    tokenizer=tokenizer,
    feature_extractor=feature_extractor,
    ltr_model=ltr_model
)
experiment_runner = ExperimentRunner(retrieval_engine=hybrid_engine, reranker=reranker)
fault_harness = FaultInjectionHarness(index_manager=index_manager)


@app.get("/api/health")
def get_health():
    stats = index_manager.get_statistics()
    return {
        "status": "healthy",
        "engine": "Atlas Search",
        "version": "1.0.0",
        "stats": stats,
        "observatory": observatory.get_latency_percentiles()
    }


@app.post("/api/search")
def search(req: SearchRequest):
    """
    Executes search with end-to-end tracing and candidate provenance.
    """
    trace = observatory.start_trace(req.query)
    t_start = time.perf_counter()

    # 1. Tokenization stage
    t0 = time.perf_counter()
    tokens = tokenizer.tokenize_with_positions(req.query)
    trace.record_stage("tokenization", (time.perf_counter() - t0) * 1000.0, {
        "tokens": [t for t, _ in tokens],
        "token_count": len(tokens)
    })

    # 2. Retrieval Stage (BM25, Dense, or Hybrid)
    retrieval_mode = req.mode if req.mode != "hybrid_ltr" else "hybrid"
    retrieval_out = hybrid_engine.retrieve(
        query=req.query,
        mode=retrieval_mode,
        top_k=req.top_k,
        alpha=req.alpha
    )
    
    trace.record_stage("retrieval", retrieval_out["latencies_ms"]["total"], {
        "mode": retrieval_mode,
        "counts": retrieval_out["counts"],
        "stage_breakdown_ms": retrieval_out["latencies_ms"]
    })

    candidates = retrieval_out["candidates"]

    # 3. Reranking Stage (if mode is hybrid_ltr)
    if req.mode == "hybrid_ltr":
        t_rerank = time.perf_counter()
        rerank_out = reranker.rerank(req.query, candidates, top_k=req.top_k)
        rerank_latency = (time.perf_counter() - t_rerank) * 1000.0
        final_results = rerank_out["reranked_results"]
        trace.record_stage("reranking", rerank_latency, {
            "model": rerank_out["model_type"],
            "reranked_count": len(final_results)
        })
    else:
        final_results = []
        for i, c in enumerate(candidates[:req.top_k], start=1):
            c_copy = c.copy()
            c_copy["final_rank"] = i
            c_copy["final_score"] = c.get("fusion_score") or c.get("score")
            c_copy["features"] = feature_extractor.extract_features(req.query, c)
            c_copy["rank_delta"] = 0
            final_results.append(c_copy)

    trace_summary = trace.finish()
    observatory.log_trace(trace_summary)

    # Check if there is an apparent relevance anomaly for quick warning pill
    autopsy_preview = None
    if len(final_results) >= 2:
        top_item = final_results[0]
        q_lang = feature_extractor.detect_query_language(req.query)
        if q_lang and top_item.get("language") != q_lang and any(r.get("language") == q_lang for r in final_results[1:]):
            autopsy_preview = {
                "detected": True,
                "reason": f"Top result is '{top_item.get('language')}' while query targeted '{q_lang}'."
            }

    return {
        "query": req.query,
        "mode": req.mode,
        "results": final_results,
        "total_results": len(final_results),
        "trace": trace_summary,
        "autopsy_preview": autopsy_preview
    }


@app.post("/api/autopsy")
def run_autopsy(req: AutopsyRequest):
    """
    Executes deep root-cause autopsy on search failure.
    """
    # Retrieve top results using BM25 baseline to show the original mistake
    retrieval_out = hybrid_engine.retrieve(req.query, mode="bm25", top_k=10)
    bm25_candidates = retrieval_out["candidates"]

    # Enrich candidates with features
    enriched = []
    for rank, c in enumerate(bm25_candidates, start=1):
        c_copy = c.copy()
        c_copy["lexical_rank"] = rank
        c_copy["features"] = feature_extractor.extract_features(req.query, c)
        enriched.append(c_copy)

    # Check ground truth if available in benchmark
    ground_truth = None
    for q_item in BENCHMARK_QUERIES:
        if q_item["query"].strip().lower() == req.query.strip().lower():
            ground_truth = q_item["ground_truth"]
            break

    report = autopsy_engine.diagnose_failure(
        query=req.query,
        retrieved_results=enriched,
        target_doc_id=req.target_doc_id,
        winner_rank=req.winner_rank,
        ground_truth=ground_truth
    )
    return report


@app.get("/api/laboratory/benchmarks")
def get_benchmark_experiments():
    """
    Runs controlled evaluation across all benchmark queries.
    """
    experiment_results = experiment_runner.run_benchmark(top_k=10)
    return experiment_results


@app.post("/api/laboratory/train-ltr")
def train_ltr_model(req: TrainLTRRequest):
    """
    Trains the LTR model on ground truth benchmark relevance judgments.
    """
    # Build training dataset from benchmark queries
    X_rows = []
    y_grades = []

    for q_item in BENCHMARK_QUERIES:
        q_text = q_item["query"]
        truth = q_item["ground_truth"]
        
        # Retrieve candidates
        cands = hybrid_engine.retrieve(q_text, mode="hybrid", top_k=15)["candidates"]
        for c in cands:
            did = c["doc_id"]
            if did in truth:
                feats = feature_extractor.extract_features(q_text, c)
                vec = feature_extractor.to_feature_vector(feats)
                X_rows.append(vec)
                y_grades.append(truth[did])

    if len(X_rows) >= 5:
        import numpy as np
        X = np.array(X_rows, dtype=np.float32)
        y = np.array(y_grades, dtype=np.float32)
        
        if req.model_type == "gbdt":
            global ltr_model, reranker
            gbdt = GBDTLTRModel()
            gbdt.fit(X, y)
            ltr_model = gbdt
            reranker = RerankingPipeline(ltr_model=gbdt, feature_extractor=feature_extractor)
        else:
            linear = LinearLTRModel()
            linear.fit(X, y, alpha=req.regularization)
            ltr_model = linear
            reranker = RerankingPipeline(ltr_model=linear, feature_extractor=feature_extractor)

    # Re-evaluate
    updated_benchmark = experiment_runner.run_benchmark(top_k=10)
    return {
        "status": "TRAINED",
        "model_type": req.model_type,
        "sample_count": len(X_rows),
        "feature_importances": ltr_model.get_feature_importances(),
        "new_ndcg@10": updated_benchmark["summary_metrics"]["hybrid_ltr"]["ndcg@10"],
        "improvements": updated_benchmark["relative_improvements_over_bm25"]
    }


@app.get("/api/cluster/status")
def get_cluster_status():
    manifest = index_manager.manifest_manager.current_manifest
    history = [m.to_dict() for m in index_manager.manifest_manager.history]
    
    segments_summary = []
    for s_id in manifest.active_segment_ids:
        seg = index_manager.segments.get(s_id)
        if seg:
            segments_summary.append(seg.serialize_metadata())

    return {
        "manifest": manifest.to_dict(),
        "segments": segments_summary,
        "tombstones": list(index_manager.tombstones),
        "history": history,
        "stats": index_manager.get_statistics()
    }


@app.post("/api/cluster/commit")
def commit_segment():
    new_manifest = index_manager.commit()
    dense_retriever.sync_vectors()
    return {
        "status": "COMMITTED",
        "new_generation": new_manifest.generation,
        "manifest_hash": new_manifest.manifest_hash,
        "total_live_docs": new_manifest.total_live_docs
    }


@app.post("/api/cluster/compact")
def compact_index():
    compact_manifest = index_manager.compact()
    dense_retriever.sync_vectors()
    return {
        "status": "COMPACTED",
        "new_manifest": compact_manifest.to_dict() if compact_manifest else None,
        "purged_tombstones": len(index_manager.tombstones) == 0
    }


@app.post("/api/cluster/rollback")
def rollback_index():
    rolled = index_manager.rollback_manifest()
    if not rolled:
        raise HTTPException(status_code=400, detail="Cannot rollback: already at generation 1")
    dense_retriever.sync_vectors()
    return {
        "status": "ROLLED_BACK",
        "current_generation": rolled.generation,
        "manifest": rolled.to_dict()
    }


@app.post("/api/cluster/fault-test")
def run_fault_tests():
    crash_res = fault_harness.test_worker_crash_and_recovery()
    corrupt_res = fault_harness.test_corrupted_segment_rejection()
    rollback_res = fault_harness.test_atomic_rollback()
    
    return {
        "timestamp": time.time(),
        "all_passed": crash_res["passed"] and corrupt_res["passed"] and rollback_res["passed"],
        "tests": [crash_res, corrupt_res, rollback_res]
    }


@app.post("/api/documents")
def add_document(doc: DocumentIngestRequest):
    index_manager.index_document(
        doc_id=doc.id,
        title=doc.title,
        body=doc.body,
        metadata={"language": doc.language, "tags": doc.tags}
    )
    dense_retriever.index_document_vector(doc.id, doc.title, doc.body)
    return {"status": "INDEXED", "doc_id": doc.id}


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int):
    deleted = index_manager.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found or already deleted")
    return {"status": "TOMBSTONED", "doc_id": doc_id}


@app.get("/api/observatory/stats")
def get_observatory_stats():
    percentiles = observatory.get_latency_percentiles()
    recent = observatory.get_recent_traces(limit=25)
    return {
        "latency_percentiles": percentiles,
        "recent_traces": recent
    }
