"""
Candidate Fusion Strategies
Implements Reciprocal Rank Fusion (RRF) and Normalized Linear Score Fusion
to merge lexical (BM25) and semantic (Dense) candidate lists.
"""

from typing import Dict, List, Any, Optional


def reciprocal_rank_fusion(
    lexical_results: List[Dict[str, Any]],
    dense_results: List[Dict[str, Any]],
    k: int = 60,
    top_k: int = 50
) -> List[Dict[str, Any]]:
    """
    Combines ranked lists using Reciprocal Rank Fusion:
    RRF_score(doc) = 1 / (k + rank_lexical) + 1 / (k + rank_dense)
    """
    fused_scores: Dict[int, float] = {}
    doc_info: Dict[int, Dict[str, Any]] = {}
    lex_ranks: Dict[int, int] = {}
    dense_ranks: Dict[int, int] = {}
    lex_scores: Dict[int, float] = {}
    dense_scores: Dict[int, float] = {}

    for rank, item in enumerate(lexical_results, start=1):
        did = item["doc_id"]
        doc_info[did] = item
        lex_ranks[did] = rank
        lex_scores[did] = item["score"]
        fused_scores[did] = fused_scores.get(did, 0.0) + (1.0 / (k + rank))

    for rank, item in enumerate(dense_results, start=1):
        did = item["doc_id"]
        if did not in doc_info:
            doc_info[did] = item
        dense_ranks[did] = rank
        dense_scores[did] = item["score"]
        fused_scores[did] = fused_scores.get(did, 0.0) + (1.0 / (k + rank))

    sorted_docs = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for rank, (did, score) in enumerate(sorted_docs, start=1):
        info = doc_info[did]
        results.append({
            "doc_id": did,
            "title": info.get("title", ""),
            "body": info.get("body", ""),
            "language": info.get("language", "generic"),
            "timestamp": info.get("timestamp", 0),
            "fusion_score": round(score, 6),
            "fusion_rank": rank,
            "lexical_rank": lex_ranks.get(did),
            "lexical_score": lex_scores.get(did),
            "dense_rank": dense_ranks.get(did),
            "dense_score": dense_scores.get(did),
            "channel_provenance": "both" if (did in lex_ranks and did in dense_ranks) else ("lexical" if did in lex_ranks else "dense")
        })

    return results


def linear_score_fusion(
    lexical_results: List[Dict[str, Any]],
    dense_results: List[Dict[str, Any]],
    alpha: float = 0.5,
    top_k: int = 50
) -> List[Dict[str, Any]]:
    """
    Min-max normalizes lexical and dense scores and computes weighted sum:
    score = alpha * norm(lexical) + (1 - alpha) * norm(dense)
    """
    doc_info: Dict[int, Dict[str, Any]] = {}
    lex_scores: Dict[int, float] = {item["doc_id"]: item["score"] for item in lexical_results}
    dense_scores: Dict[int, float] = {item["doc_id"]: item["score"] for item in dense_results}

    for item in lexical_results + dense_results:
        doc_info[item["doc_id"]] = item

    # Min-max normalization helper
    def min_max_normalize(scores: Dict[int, float]) -> Dict[int, float]:
        if not scores:
            return {}
        vals = scores.values()
        min_v, max_v = min(vals), max(vals)
        if max_v - min_v < 1e-9:
            return {k: 1.0 for k in scores}
        return {k: (v - min_v) / (max_v - min_v) for k, v in scores.items()}

    norm_lex = min_max_normalize(lex_scores)
    norm_dense = min_max_normalize(dense_scores)

    all_dids = set(norm_lex.keys()) | set(norm_dense.keys())
    combined_scores: Dict[int, float] = {}

    for did in all_dids:
        s_lex = norm_lex.get(did, 0.0)
        s_dense = norm_dense.get(did, 0.0)
        combined_scores[did] = alpha * s_lex + (1.0 - alpha) * s_dense

    sorted_docs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for rank, (did, score) in enumerate(sorted_docs, start=1):
        info = doc_info[did]
        results.append({
            "doc_id": did,
            "title": info.get("title", ""),
            "body": info.get("body", ""),
            "language": info.get("language", "generic"),
            "timestamp": info.get("timestamp", 0),
            "fusion_score": round(score, 4),
            "fusion_rank": rank,
            "lexical_score": lex_scores.get(did),
            "dense_score": dense_scores.get(did),
            "channel_provenance": "both" if (did in lex_scores and did in dense_scores) else ("lexical" if did in lex_scores else "dense")
        })

    return results
