"""
Pydantic Schemas for Atlas Search API
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="User search query string")
    mode: str = Field("hybrid_ltr", description="Retrieval mode: bm25, dense, hybrid, or hybrid_ltr")
    top_k: int = Field(15, ge=1, le=100)
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="Linear fusion weight")


class AutopsyRequest(BaseModel):
    query: str
    target_doc_id: Optional[int] = None
    winner_rank: int = 1


class TrainLTRRequest(BaseModel):
    model_type: str = Field("ridge", description="ridge or gbdt")
    regularization: float = 1.0


class DocumentIngestRequest(BaseModel):
    id: int
    title: str
    body: str
    language: str = "generic"
    tags: List[str] = []
