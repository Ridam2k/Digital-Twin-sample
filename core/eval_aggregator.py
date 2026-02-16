"""
Aggregates evaluation metrics from eval_log.jsonl
"""

import json
from collections import defaultdict
from typing import Dict, List, Tuple
from pathlib import Path


def aggregate_eval_logs(
    log_file: str = "eval_log.jsonl",
    namespace_filter: str = None,
    limit: int = 50
) -> Tuple[Dict, List]:
    
    # Check if log file exists
    if not Path(log_file).exists():
        return {
            "summary": {
                "total_queries": 0,
                "avg_groundedness_score": 0.0,
                "avg_persona_consistency_score": 0.0,
                "total_fabricated_claims": 0
            },
            "by_namespace": {},
            "recent_entries": [],
            "metadata": {
                "entries_analyzed": 0,
                "log_file_exists": False
            }
        }, []

    # Read and parse JSONL
    entries = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Apply namespace filter if provided
                if namespace_filter and entry.get('namespace') != namespace_filter:
                    continue
                entries.append(entry)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    if not entries:
        return {
            "summary": {
                "total_queries": 0,
                "avg_groundedness_score": 0.0,
                "avg_persona_consistency_score": 0.0,
                "total_fabricated_claims": 0
            },
            "by_namespace": {},
            "recent_entries": [],
            "metadata": {
                "entries_analyzed": 0,
                "log_file_exists": True
            }
        }, []

    # Compute overall statistics
    total_groundedness = 0.0
    total_persona = 0.0
    total_fabricated = 0

    namespace_stats = defaultdict(lambda: {
        'count': 0,
        'groundedness_sum': 0.0,
        'persona_sum': 0.0
    })

    for entry in entries:
        groundedness = entry.get('groundedness_score', 0.0)
        persona = entry.get('persona_consistency_score', 0.0)
        fabricated = len(entry.get('fabricated_claims', []))
        namespace = entry.get('namespace', 'unknown')

        total_groundedness += groundedness
        total_persona += persona
        total_fabricated += fabricated

        ns = namespace_stats[namespace]
        ns['count'] += 1
        ns['groundedness_sum'] += groundedness
        ns['persona_sum'] += persona

    # Compute averages
    total_queries = len(entries)
    avg_groundedness = total_groundedness / total_queries if total_queries > 0 else 0.0
    avg_persona = total_persona / total_queries if total_queries > 0 else 0.0

    # Compute namespace averages
    by_namespace = {}
    for ns, stats in namespace_stats.items():
        count = stats['count']
        by_namespace[ns] = {
            'count': count,
            'avg_groundedness': stats['groundedness_sum'] / count if count > 0 else 0.0,
            'avg_persona': stats['persona_sum'] / count if count > 0 else 0.0
        }

    # Get recent entries (last N)
    recent = entries[-limit:] if len(entries) > limit else entries
    recent_entries = [
        {
            'ts': e.get('ts'),
            'query': e.get('query'),
            'namespace': e.get('namespace'),
            'groundedness_score': e.get('groundedness_score', 0.0),
            'persona_consistency_score': e.get('persona_consistency_score', 0.0)
        }
        for e in reversed(recent)  # Most recent first
    ]

    summary = {
        "summary": {
            "total_queries": total_queries,
            "avg_groundedness_score": round(avg_groundedness, 3),
            "avg_persona_consistency_score": round(avg_persona, 3),
            "total_fabricated_claims": total_fabricated
        },
        "by_namespace": by_namespace,
        "recent_entries": recent_entries,
        "metadata": {
            "entries_analyzed": total_queries,
            "log_file_exists": True
        }
    }

    return summary, recent_entries


def aggregate_similarity_stats(
    log_file: str = "eval_log.jsonl",
    limit: int = 100
) -> Dict:
    """
    Aggregates chunk similarity statistics from eval_log.jsonl
    """

    # Check if log file exists
    if not Path(log_file).exists():
        return {
            "statistics": {
                "total_queries_analyzed": 0,
                "avg_top_score": 0.0,
                "avg_bottom_score": 0.0,
                "out_of_scope_count": 0,
                "out_of_scope_percentage": 0.0
            },
            "distribution": {},
            "thresholds": {
                "out_of_scope_threshold": 0.3,
                "top_k": 5
            }
        }

    # Read and parse JSONL
    entries = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # Only process entries with citation_scores
                if 'citation_scores' in entry and entry['citation_scores']:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

    # Get recent entries
    recent = entries[-limit:] if len(entries) > limit else entries

    if not recent:
        return {
            "statistics": {
                "total_queries_analyzed": 0,
                "avg_top_score": 0.0,
                "avg_bottom_score": 0.0,
                "out_of_scope_count": 0,
                "out_of_scope_percentage": 0.0
            },
            "distribution": {},
            "thresholds": {
                "out_of_scope_threshold": 0.3,
                "top_k": 5
            }
        }

    # Compute statistics
    all_scores = []
    top_scores = []
    bottom_scores = []
    out_of_scope_count = 0

    for entry in recent:
        scores = entry['citation_scores']
        if not scores:
            continue

        all_scores.extend(scores)
        top_scores.append(max(scores))
        bottom_scores.append(min(scores))

        # Check if out of scope (top score < 0.3)
        if max(scores) < 0.3:
            out_of_scope_count += 1

    total_queries = len(recent)
    avg_top = sum(top_scores) / len(top_scores) if top_scores else 0.0
    avg_bottom = sum(bottom_scores) / len(bottom_scores) if bottom_scores else 0.0
    out_of_scope_pct = (out_of_scope_count / total_queries * 100) if total_queries > 0 else 0.0

    # Build distribution buckets
    distribution = {
        "0.0-0.1": 0,
        "0.1-0.2": 0,
        "0.2-0.3": 0,
        "0.3-0.4": 0,
        "0.4-0.5": 0,
        "0.5-0.6": 0,
        "0.6-0.7": 0,
        "0.7-0.8": 0,
        "0.8-0.9": 0,
        "0.9-1.0": 0
    }

    for score in all_scores:
        if score < 0.1:
            distribution["0.0-0.1"] += 1
        elif score < 0.2:
            distribution["0.1-0.2"] += 1
        elif score < 0.3:
            distribution["0.2-0.3"] += 1
        elif score < 0.4:
            distribution["0.3-0.4"] += 1
        elif score < 0.5:
            distribution["0.4-0.5"] += 1
        elif score < 0.6:
            distribution["0.5-0.6"] += 1
        elif score < 0.7:
            distribution["0.6-0.7"] += 1
        elif score < 0.8:
            distribution["0.7-0.8"] += 1
        elif score < 0.9:
            distribution["0.8-0.9"] += 1
        else:
            distribution["0.9-1.0"] += 1

    return {
        "statistics": {
            "total_queries_analyzed": total_queries,
            "avg_top_score": round(avg_top, 3),
            "avg_bottom_score": round(avg_bottom, 3),
            "out_of_scope_count": out_of_scope_count,
            "out_of_scope_percentage": round(out_of_scope_pct, 1)
        },
        "distribution": distribution,
        "thresholds": {
            "out_of_scope_threshold": 0.3,
            "top_k": 5
        }
    }
