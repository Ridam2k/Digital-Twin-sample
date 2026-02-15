"""
Pydantic models for eval API responses.
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any


# ─────────────────────────────────────────────────────────
# Metrics Endpoint Models
# ─────────────────────────────────────────────────────────

class MetricsSummary(BaseModel):
    total_queries: int
    avg_groundedness_score: float
    avg_persona_consistency_score: float
    total_fabricated_claims: int


class NamespaceMetrics(BaseModel):
    count: int
    avg_groundedness: float
    avg_persona: float


class RecentEntry(BaseModel):
    ts: str
    query: str
    namespace: str
    groundedness_score: float
    persona_consistency_score: float


class MetricsResponse(BaseModel):
    summary: MetricsSummary
    by_namespace: Dict[str, NamespaceMetrics]
    recent_entries: List[RecentEntry]
    metadata: Dict[str, Any]


# ─────────────────────────────────────────────────────────
# Retrieval Stats Endpoint Models
# ─────────────────────────────────────────────────────────

class OverallRetrievalStats(BaseModel):
    recall_at_k: float
    mrr_at_k: float
    k: int
    total_queries: int


class NamespaceRetrievalStats(BaseModel):
    count: int
    recall_at_k: float
    mrr_at_k: float


class RetrievalStatsResponse(BaseModel):
    overall: OverallRetrievalStats
    by_namespace: Dict[str, NamespaceRetrievalStats]
    metadata: Dict[str, Any]


# ─────────────────────────────────────────────────────────
# Database Stats Endpoint Models
# ─────────────────────────────────────────────────────────

class NamespaceDbStats(BaseModel):
    chunk_count: int
    doc_count: int


class DbStatsResponse(BaseModel):
    collection_name: str
    total_chunks: int
    total_documents: int
    namespaces: Dict[str, NamespaceDbStats]
    metadata: Dict[str, Any]


# ─────────────────────────────────────────────────────────
# Similarity Stats Endpoint Models
# ─────────────────────────────────────────────────────────

class SimilarityStatistics(BaseModel):
    total_queries_analyzed: int
    avg_top_score: float
    avg_bottom_score: float
    out_of_scope_count: int
    out_of_scope_percentage: float


class SimilarityStatsResponse(BaseModel):
    statistics: SimilarityStatistics
    distribution: Dict[str, int]
    thresholds: Dict[str, float]
