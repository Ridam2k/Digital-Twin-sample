import json
from collections import defaultdict
from typing import List, Dict
from qdrant_client import QdrantClient
from core.retriever import retrieve   
from config import QDRANT_URL, COLLECTION_NAME, QDRANT_API_KEY

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

EVAL_FILE = "eval_set.json"
K = 5  # Recall@K and MRR@K

qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# retriever = retrieve()


# ─────────────────────────────────────────────────────────────
# Helper: Resolve gold chunk doc_ids dynamically
# ─────────────────────────────────────────────────────────────

def fetch_gold_doc_ids(doc_id: str) -> List[str]:
    """
    Returns list of chunk IDs belonging to a given doc_id.
    We don't rely on stored chunk IDs in eval set.
    """
    results, _ = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        with_payload=True,
        with_vectors=False,
        scroll_filter={
            "must": [
                {"key": "doc_id", "match": {"value": doc_id}}
            ]
        },
        limit=1000
    )

    return [point.id for point in results]


# ─────────────────────────────────────────────────────────────
# Core Evaluation
# ─────────────────────────────────────────────────────────────

def evaluate():
    with open(EVAL_FILE, "r") as f:
        eval_data = json.load(f)

    total_queries = len(eval_data)
    recall_hits = 0
    reciprocal_ranks = []

    namespace_stats = defaultdict(lambda: {
        "count": 0,
        "recall_hits": 0,
        "reciprocal_ranks": []
    })

    print(f"Evaluating {total_queries} queries at K={K}\n")

    for row in eval_data:
        query = row["query"]
        namespace = row["namespace"]
        gold_doc_id = row["gold"]["doc_id"]

        # Retrieve top-K (returns tuple: chunks, out_of_scope)
        chunks, out_of_scope = retrieve(query, namespace)

        # Extract retrieved doc_ids from RetrievedChunk objects
        retrieved_doc_ids = [chunk.doc_id for chunk in chunks]

        # ─────────────────────────────
        # Recall@K
        # ─────────────────────────────
        hit = gold_doc_id in retrieved_doc_ids
        if hit:
            recall_hits += 1

        # ─────────────────────────────
        # MRR@K
        # ─────────────────────────────
        rr = 0
        for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
            if doc_id == gold_doc_id:
                rr = 1.0 / rank
                break

        reciprocal_ranks.append(rr)

        # ─────────────────────────────
        # Namespace breakdown
        # ─────────────────────────────
        ns = namespace_stats[namespace]
        ns["count"] += 1
        if hit:
            ns["recall_hits"] += 1
        ns["reciprocal_ranks"].append(rr)

    # ─────────────────────────────────────────────────────────
    # Final Metrics
    # ─────────────────────────────────────────────────────────

    recall_at_k = recall_hits / total_queries
    mrr_at_k = sum(reciprocal_ranks) / total_queries

    print("──────────── Overall Results ────────────")
    print(f"Recall@{K}: {recall_at_k:.4f}")
    print(f"MRR@{K}:    {mrr_at_k:.4f}")
    print()

    print("──────────── Namespace Breakdown ────────────")
    for ns, stats in namespace_stats.items():
        ns_recall = stats["recall_hits"] / stats["count"]
        ns_mrr = sum(stats["reciprocal_ranks"]) / stats["count"]

        print(f"\nNamespace: {ns}")
        print(f"  Count: {stats['count']}")
        print(f"  Recall@{K}: {ns_recall:.4f}")
        print(f"  MRR@{K}:    {ns_mrr:.4f}")

    print("\nDone.")

# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    evaluate()
