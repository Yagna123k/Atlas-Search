"""Tests for Learning-to-Rank and Search Failure Autopsy"""
import pytest
from core.tokenizer import Tokenizer
from core.ranking.features import FeatureExtractor
from core.ranking.ltr import LinearLTRModel
from core.observatory.autopsy import SearchFailureAutopsy


def test_language_affinity_feature():
    extractor = FeatureExtractor()
    query = "How do I reduce memory usage in a Python application?"

    python_doc = {
        "title": "Profiling and Reducing Memory Usage in Python Applications",
        "body": "Guide to tracemalloc and memory profiler in Python.",
        "language": "python",
        "lexical_score": 14.5,
        "dense_score": 0.88
    }

    jvm_doc = {
        "title": "JVM Garbage Collection and Memory Tuning Guide",
        "body": "Techniques for tuning JVM heap memory and G1GC in Java applications.",
        "language": "java",
        "lexical_score": 15.2,  # Higher lexical score due to keyword overlap!
        "dense_score": 0.65
    }

    feats_python = extractor.extract_features(query, python_doc)
    feats_jvm = extractor.extract_features(query, jvm_doc)

    assert feats_python["language_affinity"] == 1.0
    assert feats_jvm["language_affinity"] == -1.0


def test_search_failure_autopsy_diagnosis():
    query = "How do I reduce memory usage in a Python application?"
    extractor = FeatureExtractor()
    ltr = LinearLTRModel()
    autopsy = SearchFailureAutopsy(feature_extractor=extractor, ltr_model=ltr)

    winner_jvm = {
        "doc_id": 101,
        "title": "JVM Garbage Collection and Memory Tuning Guide",
        "body": "Techniques for tuning JVM heap memory in Java microservices.",
        "language": "java",
        "lexical_score": 16.0,
        "final_rank": 1
    }

    target_python = {
        "doc_id": 102,
        "title": "Profiling and Reducing Memory Usage in Python Applications",
        "body": "Comprehensive guide to reducing memory usage in Python applications.",
        "language": "python",
        "lexical_score": 15.1,
        "final_rank": 2
    }

    report = autopsy.diagnose_failure(
        query=query,
        retrieved_results=[winner_jvm, target_python],
        target_doc_id=102,
        winner_rank=1
    )

    assert "LANGUAGE_INCOMPATIBILITY" in report["detected_issues"]
    assert "retrieval_diagnosis" in report["diagnosis_report"]
    assert "ranking_diagnosis" in report["diagnosis_report"]
    assert "proposed_experiment" in report["diagnosis_report"]
    assert report["simulation"]["target_simulated_rank"] == 1
