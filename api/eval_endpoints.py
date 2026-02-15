"""
FastAPI router for evaluation metrics endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from api.models import (
    MetricsResponse,
    RetrievalStatsResponse,
    DbStatsResponse,
    SimilarityStatsResponse
)
from core.eval_aggregator import aggregate_eval_logs, aggregate_similarity_stats
from core.retrieval_metrics import compute_retrieval_metrics
from qdrant_client import QdrantClient
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
import datetime


router = APIRouter()

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


@router.get("/metrics", response_model=MetricsResponse)
async def get_eval_metrics(
    namespace: str = Query(None, description="Filter by namespace (technical/nontechnical/ambiguous)"),
    limit: int = Query(50, description="Number of recent entries to include")
):
    """
    Aggregates groundedness and persona consistency scores from eval_log.jsonl.
    """
    try:
        result, _ = aggregate_eval_logs(
            log_file="eval_log.jsonl",
            namespace_filter=namespace,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error aggregating eval metrics: {str(e)}")


@router.get("/retrieval-stats", response_model=RetrievalStatsResponse)
async def get_retrieval_stats(
    k: int = Query(5, description="K value for Recall@K and MRR@K"),
    recompute: bool = Query(False, description="Force recomputation (bypass cache)")
):
    """
    Returns cached or recomputed Recall@K and MRR@K metrics.
    """
    try:
        result = compute_retrieval_metrics(
            k=k,
            eval_file="eval_set.json",
            force_recompute=recompute
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing retrieval stats: {str(e)}")


@router.get("/db-stats", response_model=DbStatsResponse)
async def get_db_stats():
    """
    Queries Qdrant for collection metadata and statistics.
    """
    try:
        # Get collection info
        collection_info = qdrant_client.get_collection(collection_name=COLLECTION_NAME)
        total_chunks = collection_info.points_count

        # Count chunks per namespace and unique doc_ids
        namespaces = ["technical", "nontechnical"]
        namespace_stats = {}
        total_unique_docs = set()

        for ns in namespaces:
            # Scroll through namespace chunks
            results, _ = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                with_payload=True,
                with_vectors=False,
                scroll_filter={
                    "must": [
                        {"key": "personality_ns", "match": {"value": ns}}
                    ]
                },
                limit=10000  # High limit to get all chunks
            )

            # Count chunks and unique docs
            chunk_count = len(results)
            doc_ids = set(point.payload.get("doc_id") for point in results if "doc_id" in point.payload)

            namespace_stats[ns] = {
                "chunk_count": chunk_count,
                "doc_count": len(doc_ids)
            }

            total_unique_docs.update(doc_ids)

        return {
            "collection_name": COLLECTION_NAME,
            "total_chunks": total_chunks,
            "total_documents": len(total_unique_docs),
            "namespaces": namespace_stats,
            "metadata": {
                "vector_dimension": collection_info.config.params.vectors.size,
                "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying Qdrant: {str(e)}")


@router.get("/similarity-stats", response_model=SimilarityStatsResponse)
async def get_similarity_stats(
    limit: int = Query(100, description="Number of recent queries to analyze")
):
    """
    Provides statistics on chunk similarity scores from recent queries.
    """
    try:
        result = aggregate_similarity_stats(
            log_file="eval_log.jsonl",
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing similarity stats: {str(e)}")
