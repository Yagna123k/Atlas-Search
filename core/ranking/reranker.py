"""
Reranking Pipeline
Applies Learning-to-Rank models to candidate pools with full feature explanations
and rank delta analysis.
"""

from typing import Dict, List, Any, Optional
import time
from core.ranking.features import FeatureExtractor, FEATURE_NAMES
from core.ranking.ltr import BaseLTRModel, LinearLTRModel


class RerankingPipeline:
    """
    Second-stage ranker that scores retrieval candidates using trained LTR models.
    """
    def __init__(
        self,
        ltr_model: Optional[BaseLTRModel] = None,
        feature_extractor: Optional[FeatureExtractor] = None
    ):
        self.ltr_model = ltr_model or LinearLTRModel()
        self.feature_extractor = feature_extractor or FeatureExtractor()

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 20,
        avg_doc_length: float = 100.0
    ) -> Dict[str, Any]:
        """
        Extracts features, evaluates LTR model, and reranks candidates.
        """
        t0 = time.perf_counter()
        if not candidates:
            return {
                "reranked_results": [],
                "rerank_latency_ms": 0.0,
                "model_type": self.ltr_model.__class__.__name__
            }

        enriched_candidates = []
        feature_vectors = []

        for initial_rank, cand in enumerate(candidates, start=1):
            feats = self.feature_extractor.extract_features(
                query=query,
                doc=cand,
                avg_doc_length=avg_doc_length
            )
            vec = self.feature_extractor.to_feature_vector(feats)
            feature_vectors.append(vec)
            
            cand_copy = cand.copy()
            cand_copy["features"] = feats
            cand_copy["initial_rank"] = initial_rank
            enriched_candidates.append(cand_copy)

        # Batch prediction or sequential
        for i, cand in enumerate(enriched_candidates):
            score = self.ltr_model.predict_score(feature_vectors[i])
            cand["final_score"] = round(float(score), 4)

        # Sort descending by final score
        reranked = sorted(enriched_candidates, key=lambda x: x["final_score"], reverse=True)[:top_k]

        # Calculate rank movement deltas
        for final_rank, item in enumerate(reranked, start=1):
            item["final_rank"] = final_rank
            item["rank_delta"] = item["initial_rank"] - final_rank  # Positive = promoted, Negative = demoted

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "reranked_results": reranked,
            "rerank_latency_ms": round(latency_ms, 3),
            "model_type": self.ltr_model.__class__.__name__,
            "feature_importances": self.ltr_model.get_feature_importances()
        }
