"""
Retrieval evaluation metrics (Recall@K, MRR@K) - refactored from eval_retrieval.py
"""

import json
from collections import defaultdict
from typing import Dict
from pathlib import Path
from qdrant_client import QdrantClient
from core.retriever import retrieve
from config import QDRANT_URL, COLLECTION_NAME, QDRANT_API_KEY
import datetime


# File path for persistent storage
RETRIEVAL_STATS_FILE = "retrieval_stats.json"


def load_retrieval_stats_from_file():
    """Load retrieval stats from JSON file if it exists."""
    if Path(RETRIEVAL_STATS_FILE).exists():
        with open(RETRIEVAL_STATS_FILE, 'r') as f:
            return json.load(f)
    return None


def save_retrieval_stats_to_file(stats_dict):
    """Save retrieval stats to JSON file."""
    with open(RETRIEVAL_STATS_FILE, 'w') as f:
        json.dump(stats_dict, f, indent=2)


def compute_retrieval_metrics(
    k: int = 5,
    eval_file: str = "eval_set.json",
    force_recompute: bool = False
) -> Dict:
    """
    Computes Recall@K and MRR@K metrics from evaluation set.
    Uses file-based caching to persist results across server restarts.

    Args:
        k: K value for Recall@K and MRR@K
        eval_file: Path to evaluation set JSON file
        force_recompute: If True, bypass cache and recompute

    Returns:
        Dict with overall and namespace-level metrics
    """

    # Try to load from file first (unless force_recompute)
    if not force_recompute:
        cached_stats = load_retrieval_stats_from_file()
        if cached_stats is not None:
            print(f"✓ Loaded retrieval stats from {RETRIEVAL_STATS_FILE}")
            return cached_stats

    print(f"Computing retrieval metrics for {eval_file}...")

    # Load eval set
    with open(eval_file, "r") as f:
        eval_data = json.load(f)

    total_queries = len(eval_data)
    recall_hits = 0
    reciprocal_ranks = []

    namespace_stats = defaultdict(lambda: {
        "count": 0,
        "recall_hits": 0,
        "reciprocal_ranks": []
    })

    # Evaluate each query
    for row in eval_data:
        query = row["query"]
        namespace = row["namespace"]
        gold_doc_id = row["gold"]["doc_id"]

        # Retrieve top-K chunks
        chunks, out_of_scope = retrieve(query, namespace)

        # Extract retrieved doc_ids
        retrieved_doc_ids = [chunk.doc_id for chunk in chunks]

        # Recall@K: Check if gold doc is in top-K
        hit = gold_doc_id in retrieved_doc_ids
        if hit:
            recall_hits += 1

        # MRR@K: Find rank of gold doc
        rr = 0
        for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
            if doc_id == gold_doc_id:
                rr = 1.0 / rank
                break

        reciprocal_ranks.append(rr)

        # Namespace breakdown
        ns = namespace_stats[namespace]
        ns["count"] += 1
        if hit:
            ns["recall_hits"] += 1
        ns["reciprocal_ranks"].append(rr)

    # Compute overall metrics
    recall_at_k = recall_hits / total_queries if total_queries > 0 else 0.0
    mrr_at_k = sum(reciprocal_ranks) / total_queries if total_queries > 0 else 0.0

    # Compute namespace metrics
    by_namespace = {}
    for ns, stats in namespace_stats.items():
        count = stats["count"]
        ns_recall = stats["recall_hits"] / count if count > 0 else 0.0
        ns_mrr = sum(stats["reciprocal_ranks"]) / count if count > 0 else 0.0

        by_namespace[ns] = {
            "count": count,
            "recall_at_k": round(ns_recall, 4),
            "mrr_at_k": round(ns_mrr, 4)
        }

    # Build result
    result = {
        "overall": {
            "recall_at_k": round(recall_at_k, 4),
            "mrr_at_k": round(mrr_at_k, 4),
            "k": k,
            "total_queries": total_queries
        },
        "by_namespace": by_namespace,
        "metadata": {
            "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cache_ttl_seconds": 3600,
            "eval_set_file": eval_file
        }
    }

    # Save to file for future use
    save_retrieval_stats_to_file(result)
    print(f"✓ Saved retrieval stats to {RETRIEVAL_STATS_FILE}")

    return result
