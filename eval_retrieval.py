import json
import hashlib
from collections import defaultdict
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from core.retriever import retrieve
from config import QDRANT_URL, COLLECTION_NAME, QDRANT_API_KEY

EVAL_FILE = "eval_set.json"
K = 5

qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def doc_title_hash(namespace: str, doc_title: str) -> str:
    return sha256(f"{namespace}::{doc_title}".strip())

def evaluate():
    with open(EVAL_FILE, "r") as f:
        eval_data: List[Dict[str, Any]] = json.load(f)

    total_queries = len(eval_data)
    recall_hits = 0
    reciprocal_ranks: List[float] = []

    namespace_stats = defaultdict(lambda: {
        "count": 0,
        "recall_hits": 0,
        "reciprocal_ranks": [],
    })

    failures = []  # store a few for debugging

    print(f"Evaluating {total_queries} queries at K={K}\n")

    for row in eval_data:
        query = row["query"]
        namespace = row["namespace"]

        gold = row["gold"]
        gold_hash = gold["doc_title_hash"]
        gold_title = gold["doc_title"]

        chunks, out_of_scope = retrieve(query, namespace)

        retrieved_hashes = []
        retrieved_titles = []

        for c in chunks[:K]:
            title = getattr(c, "doc_title", "") or ""
            retrieved_titles.append(title)
            retrieved_hashes.append(doc_title_hash(namespace, title) if title else None)

        # Recall@K
        hit = gold_hash in retrieved_hashes
        if hit:
            recall_hits += 1

        # MRR@K
        rr = 0.0
        for rank, h in enumerate(retrieved_hashes, start=1):
            if h == gold_hash:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

        ns = namespace_stats[namespace]
        ns["count"] += 1
        if hit:
            ns["recall_hits"] += 1
        ns["reciprocal_ranks"].append(rr)

        # Save a few misses for inspection
        if not hit and len(failures) < 10:
            failures.append({
                "query": query,
                "namespace": namespace,
                "gold_title": gold_title,
                "retrieved_titles": retrieved_titles,
                "out_of_scope": out_of_scope,
            })

    recall_at_k = recall_hits / total_queries if total_queries else 0.0
    mrr_at_k = sum(reciprocal_ranks) / total_queries if total_queries else 0.0

    print("──────────── Overall Results ────────────")
    print(f"Recall@{K}: {recall_at_k:.4f}")
    print(f"MRR@{K}:    {mrr_at_k:.4f}\n")

    print("──────────── Namespace Breakdown ────────────")
    for ns, stats in namespace_stats.items():
        ns_recall = stats["recall_hits"] / stats["count"] if stats["count"] else 0.0
        ns_mrr = sum(stats["reciprocal_ranks"]) / stats["count"] if stats["count"] else 0.0
        print(f"\nNamespace: {ns}")
        print(f"  Count: {stats['count']}")
        print(f"  Recall@{K}: {ns_recall:.4f}")
        print(f"  MRR@{K}:    {ns_mrr:.4f}")

    if failures:
        for i, f in enumerate(failures, 10):
            print(f"\n[{i}] {f['namespace']} | out_of_scope={f['out_of_scope']}")
            print(f"Q: {f['query']}")
            print(f"Gold: {f['gold_title']}")
            print(f"Top-{K}: {f['retrieved_titles']}")

    print("\nDone.")

if __name__ == "__main__":
    evaluate()
