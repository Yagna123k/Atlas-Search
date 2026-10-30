"""
Learning-to-Rank (LTR) Laboratory
Implements Pointwise Linear Ranker, Gradient Boosted Decision Tree (GBDT) Ranker,
model training on relevance judgments, and feature attribution for explainability.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from core.ranking.features import FEATURE_NAMES, FeatureExtractor


class BaseLTRModel:
    """Base interface for Learning-to-Rank models."""
    def predict_score(self, feature_vector: np.ndarray) -> float:
        raise NotImplementedError

    def predict_batch(self, feature_matrix: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_feature_importances(self) -> Dict[str, float]:
        raise NotImplementedError


class LinearLTRModel(BaseLTRModel):
    """
    Linear / Ridge Learning-to-Rank model with direct interpretability.
    """
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        if weights:
            self.weights = weights.copy()
        else:
            # Calibrated default production weights
            self.weights = {
                "bm25_score": 0.24,
                "dense_score": 0.28,
                "title_match_ratio": 0.16,
                "body_coverage_ratio": 0.08,
                "language_affinity": 0.22,
                "freshness_score": 0.08,
                "length_ratio": -0.04,  # Mild penalty for excessively verbose docs
                "channel_consensus": 0.08,
            }
        self.bias: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> None:
        """Trains Ridge regression model on (features, relevance_grades)."""
        model = Ridge(alpha=alpha)
        model.fit(X, y)
        for i, name in enumerate(FEATURE_NAMES):
            self.weights[name] = float(model.coef_[i])
        self.bias = float(model.intercept_)

    def predict_score(self, feature_vector: np.ndarray) -> float:
        score = self.bias
        for i, name in enumerate(FEATURE_NAMES):
            score += self.weights.get(name, 0.0) * float(feature_vector[i])
        return float(score)

    def predict_batch(self, feature_matrix: np.ndarray) -> np.ndarray:
        w_vec = np.array([self.weights.get(name, 0.0) for name in FEATURE_NAMES], dtype=np.float32)
        return np.dot(feature_matrix, w_vec) + self.bias

    def get_feature_importances(self) -> Dict[str, float]:
        total = sum(abs(v) for v in self.weights.values()) or 1.0
        return {k: round(abs(v) / total, 4) for k, v in self.weights.items()}

    def attribute_score_difference(
        self,
        features_a: Dict[str, float],
        features_b: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Explains why Doc A scored differently than Doc B:
        contribution_diff(feature) = (feat_A - feat_B) * weight
        """
        diffs = {}
        for name in FEATURE_NAMES:
            delta = features_a.get(name, 0.0) - features_b.get(name, 0.0)
            diffs[name] = round(delta * self.weights.get(name, 0.0), 4)
        return diffs


class GBDTLTRModel(BaseLTRModel):
    """
    Gradient Boosted Decision Tree (GBDT) Ranker capturing non-linear interactions
    between lexical, semantic, and metadata signals.
    """
    def __init__(self, n_estimators: int = 50, max_depth: int = 3, learning_rate: float = 0.1):
        self.model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=42
        )
        self.is_trained = False
        self._linear_fallback = LinearLTRModel()

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fits gradient boosted trees on training data."""
        self.model.fit(X, y)
        self.is_trained = True

    def predict_score(self, feature_vector: np.ndarray) -> float:
        if not self.is_trained:
            return self._linear_fallback.predict_score(feature_vector)
        pred = self.model.predict(feature_vector.reshape(1, -1))[0]
        return float(pred)

    def predict_batch(self, feature_matrix: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            return self._linear_fallback.predict_batch(feature_matrix)
        return self.model.predict(feature_matrix)

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_trained:
            return self._linear_fallback.get_feature_importances()
        importances = self.model.feature_importances_
        return {name: round(float(importances[i]), 4) for i, name in enumerate(FEATURE_NAMES)}
