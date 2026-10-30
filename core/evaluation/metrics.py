"""
Information Retrieval (IR) Evaluation Metrics
Production implementations of NDCG@k, Recall@k, MRR@k, Precision@k, and MAP.
"""

from typing import Dict, List, Any, Optional
import math


def dcg_at_k(relevance_scores: List[float], k: int = 10) -> float:
    """
    Computes Discounted Cumulative Gain at rank k:
    DCG@k = sum_{i=1}^k (2^{rel_i} - 1) / log2(i + 1)
    """
    dcg = 0.0
    for i, rel in enumerate(relevance_scores[:k], start=1):
        if rel > 0:
            dcg += (math.pow(2.0, rel) - 1.0) / math.log2(i + 1)
    return dcg


def ndcg_at_k(retrieved_doc_ids: List[int], ground_truth: Dict[int, float], k: int = 10) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at rank k:
    NDCG@k = DCG@k / IDCG@k
    """
    actual_relevances = [ground_truth.get(did, 0.0) for did in retrieved_doc_ids[:k]]
    actual_dcg = dcg_at_k(actual_relevances, k=k)

    # Ideal DCG: sort all ground truth relevances in descending order
    ideal_relevances = sorted(ground_truth.values(), reverse=True)
    ideal_dcg = dcg_at_k(ideal_relevances, k=k)

    if ideal_dcg <= 1e-9:
        return 1.0 if actual_dcg <= 1e-9 else 0.0

    return actual_dcg / ideal_dcg


def recall_at_k(
    retrieved_doc_ids: List[int],
    ground_truth: Dict[int, float],
    k: int = 10,
    min_relevance: float = 1.0
) -> float:
    """
    Computes Recall@k: fraction of all relevant documents retrieved within top k.
    """
    relevant_total = sum(1 for rel in ground_truth.values() if rel >= min_relevance)
    if relevant_total == 0:
        return 1.0

    retrieved_relevant = sum(
        1 for did in retrieved_doc_ids[:k]
        if ground_truth.get(did, 0.0) >= min_relevance
    )
    return retrieved_relevant / relevant_total


def mrr_at_k(
    retrieved_doc_ids: List[int],
    ground_truth: Dict[int, float],
    k: int = 10,
    min_relevance: float = 1.0
) -> float:
    """
    Computes Mean Reciprocal Rank (MRR) at rank k:
    1 / rank of first document with relevance >= min_relevance, or 0.0.
    """
    for rank, did in enumerate(retrieved_doc_ids[:k], start=1):
        if ground_truth.get(did, 0.0) >= min_relevance:
            return 1.0 / rank
    return 0.0


def precision_at_k(
    retrieved_doc_ids: List[int],
    ground_truth: Dict[int, float],
    k: int = 10,
    min_relevance: float = 1.0
) -> float:
    """
    Computes Precision@k: fraction of top k retrieved docs that are relevant.
    """
    if k <= 0:
        return 0.0
    retrieved_relevant = sum(
        1 for did in retrieved_doc_ids[:k]
        if ground_truth.get(did, 0.0) >= min_relevance
    )
    return retrieved_relevant / min(k, len(retrieved_doc_ids) or 1)


def evaluate_query_ranking(
    retrieved_doc_ids: List[int],
    ground_truth: Dict[int, float]
) -> Dict[str, float]:
    """
    Computes comprehensive suite of IR metrics for a single query.
    """
    return {
        "ndcg@10": round(ndcg_at_k(retrieved_doc_ids, ground_truth, k=10), 4),
        "ndcg@5": round(ndcg_at_k(retrieved_doc_ids, ground_truth, k=5), 4),
        "recall@10": round(recall_at_k(retrieved_doc_ids, ground_truth, k=10), 4),
        "recall@50": round(recall_at_k(retrieved_doc_ids, ground_truth, k=50), 4),
        "mrr@10": round(mrr_at_k(retrieved_doc_ids, ground_truth, k=10), 4),
        "precision@5": round(precision_at_k(retrieved_doc_ids, ground_truth, k=5), 4),
    }
