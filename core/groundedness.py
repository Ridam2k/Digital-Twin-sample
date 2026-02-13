"""
groundedness.py

Evaluates whether a digital twin response is grounded in the
retrieved context chunks. Each substantive claim is audited
against the context; the judge must quote a supporting span
explicitly to mark a claim as SUPPORTED.

Usage:
    from groundedness import check_groundedness

    result = check_groundedness(
        response="I prefer async communication and have strong experience with RAG pipelines.",
        retrieved_chunks=["...skills.json content...", "...traits.json content..."],
    )
    print(result)
"""

import json
import os
from dataclasses import dataclass
from config import OPENAI_API_KEY

from openai import OpenAI

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class ClaimAudit:
    claim: str
    verdict: str          # "SUPPORTED" | "INFERRED" | "FABRICATED"
    supporting_span: str  # quoted text from context, or "" if none


@dataclass
class GroundednessResult:
    claim_audits: list[ClaimAudit]
    groundedness_score: float   # 0.0 – 1.0
    fabricated_claims: list[str]
    raw_response: str           # full judge output, for debugging


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a precise groundedness auditor for a digital twin system.

Your job is to verify whether each substantive claim in a twin's \
response is supported by the retrieved context provided to you.

Rules:
1. Extract every substantive claim from the TWIN RESPONSE — these are \
   statements about the person's identity, skills, opinions, experiences, \
   or traits. Ignore filler phrases.
2. For each claim, assign exactly one verdict:
   - SUPPORTED: you can find a span in the RETRIEVED CONTEXT that directly \
     backs the claim. You MUST quote that span verbatim.
   - INFERRED: the claim is a reasonable inference from context but is not \
     stated explicitly. Quote the closest relevant span.
   - FABRICATED: no span in the context supports or implies the claim. \
     Leave supporting_span as an empty string.
3. Be strict. If you cannot find a real quote, do not invent one — mark \
   the claim FABRICATED instead.
4. Return ONLY valid JSON. No prose, no markdown, no backtick fences.

Output schema:
{
  "claim_audits": [
    {
      "claim": "<the claim extracted from the response>",
      "verdict": "SUPPORTED" | "INFERRED" | "FABRICATED",
      "supporting_span": "<verbatim quote from context, or empty string>"
    }
  ]
}
"""

_USER_TEMPLATE = """\
RETRIEVED CONTEXT:
---
{context}
---

TWIN RESPONSE:
---
{response}
---
"""


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _build_context_block(chunks: list[str]) -> str:
    """Join retrieved chunks with clear separators."""
    return "\n\n---chunk---\n\n".join(chunk.strip() for chunk in chunks)


def _score(audits: list[ClaimAudit]) -> float:
    """
    Weighted score:
      SUPPORTED   → 1.0
      INFERRED    → 0.5
      FABRICATED  → 0.0
    Returns 0.0 if there are no claims.
    """
    if not audits:
        return 0.0
    weights = {"SUPPORTED": 1.0, "INFERRED": 0.5, "FABRICATED": 0.0}
    total = sum(weights.get(a.verdict, 0.0) for a in audits)
    return round(total / len(audits), 3)


def _parse_judge_output(raw: str) -> list[ClaimAudit]:
    """
    Parse the judge's JSON output into ClaimAudit objects.
    Raises ValueError with a descriptive message on malformed output.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge returned non-JSON output: {e}\n\nRaw:\n{raw}")

    audits = []
    for item in data.get("claim_audits", []):
        verdict = item.get("verdict", "FABRICATED").upper()
        if verdict not in ("SUPPORTED", "INFERRED", "FABRICATED"):
            verdict = "FABRICATED"

        # Guard: if verdict is SUPPORTED/INFERRED but span is empty,
        # downgrade to FABRICATED — the judge didn't actually find evidence.
        span = item.get("supporting_span", "").strip()
        if verdict in ("SUPPORTED", "INFERRED") and not span:
            verdict = "FABRICATED"

        audits.append(ClaimAudit(
            claim=item.get("claim", ""),
            verdict=verdict,
            supporting_span=span,
        ))

    return audits


def check_groundedness(
    response: str,
    retrieved_chunks: list[str],
    model: str = "gpt-4o-mini"
) -> GroundednessResult:
    """
    Run the groundedness check for a single twin response.

    Args:
        response:         The twin's response string.
        retrieved_chunks: List of raw text chunks retrieved for this query.
        model:            OpenAI model to use as judge.
        api_key:          Optional API key override; falls back to env var.

    Returns:
        GroundednessResult with per-claim audits, a 0–1 score,
        and a list of any fabricated claims for easy surfacing.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    context_block = _build_context_block(retrieved_chunks)
    user_message = _USER_TEMPLATE.format(
        context=context_block,
        response=response,
    )

    completion = client.chat.completions.create(
        model=model,
        temperature=0,   # deterministic for evaluation
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    )

    raw = completion.choices[0].message.content.strip()
    audits = _parse_judge_output(raw)
    score = _score(audits)
    fabricated = [a.claim for a in audits if a.verdict == "FABRICATED"]

    return GroundednessResult(
        claim_audits=audits,
        groundedness_score=score,
        fabricated_claims=fabricated,
        raw_response=raw,
    )


# ---------------------------------------------------------------------------
# Pretty printer (useful in dev / notebook contexts)
# ---------------------------------------------------------------------------

def print_result(result: GroundednessResult) -> None:
    print(f"\nGroundedness Score: {result.groundedness_score:.3f}\n")
    for audit in result.claim_audits:
        icon = {"SUPPORTED": "✓", "INFERRED": "~", "FABRICATED": "✗"}.get(audit.verdict, "?")
        print(f"  {icon} [{audit.verdict}] {audit.claim}")
        if audit.supporting_span:
            print(f"      └─ \"{audit.supporting_span}\"")
    if result.fabricated_claims:
        print(f"\n⚠ Fabricated claims ({len(result.fabricated_claims)}):")
        for c in result.fabricated_claims:
            print(f"  - {c}")


# ---------------------------------------------------------------------------
# Quick smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _test_chunks = [
        # Simulates what might be retrieved from your persona files
        'technical_skills includes "RAG pipeline architecture" and "LLM agent orchestration".',
        'core_identity role_archetype: ["Builder", "Systems Thinker", "Research-to-Production Translator"].',
        'growth_edges: ["asking for help earlier", "navigating career ambiguity"].',
    ]

    _test_response = (
        "I have deep experience building RAG pipelines and consider myself a systems thinker. "
        "I also love competitive gaming and find it helps me decompress."  # fabricated
    )

    result = check_groundedness(
        response=_test_response,
        retrieved_chunks=_test_chunks,
    )
    print_result(result)