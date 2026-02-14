"""
persona_consistency.py

Evaluates whether a digital twin response is consistent with the
person's persona, across two dimensions:
  1. Values alignment   (weight: 0.6)
  2. Tone fidelity      (weight: 0.4)

Each dimension is scored 1–5 by an LLM judge grounded in the actual
traits.json and style.json content. A weighted aggregate is returned
alongside the per-dimension breakdown.
"""

import json
from dataclasses import dataclass
from config import OPENAI_API_KEY
from openai import OpenAI

from .identity import load_identity_context

_WEIGHTS = {
    "values_alignment": 0.6,
    "tone_fidelity":    0.4,
}


@dataclass
class DimensionScore:
    dimension:   str           # "values_alignment" | "tone_fidelity"
    score:       int           # 1–5
    reasoning:   str           # judge's explanation
    violations:  list[str]     # specific issues found, if any


@dataclass
class PersonaConsistencyResult:
    values_alignment: DimensionScore
    tone_fidelity:    DimensionScore
    weighted_score:   float    # 0.0–1.0, normalized from 1–5 scale
    raw_response:     str      # full judge output, for debugging


# ---------------------------------------------------------------------------
# Reference builders — dynamic extraction from traits.json and style.json
# ---------------------------------------------------------------------------
def _build_values_reference(traits: dict) -> str:
    
    values = traits.get("values", {})
    patterns = traits.get("personality_patterns", {})
    core_identity = traits.get("core_identity", {})

    primary_drivers = ", ".join(values.get("primary_drivers", []))
    secondary_drivers = ", ".join(values.get("secondary_drivers", []))

    ref = f"""
    Primary drivers: {primary_drivers}
    Secondary drivers: {secondary_drivers}
    Thinking mode: {patterns.get("thinking_mode", "N/A")}
    Decision style: {core_identity.get("decision_style", "N/A")}
    Communication tendency: {patterns.get("communication_tendency", "N/A")}
    Growth orientation: {patterns.get("growth_orientation", "N/A")}
    Intellectual orientation: {core_identity.get("intellectual_orientation", "N/A")}
    """.strip()

    return ref


def _build_tone_reference(style: dict, mode: str) -> str:
    
    tone_profile = style.get("tone_profile", {})
    comm_style = style.get("communication_style", {})
    written = comm_style.get("written", {})
    prefs = style.get("response_preferences", {})
    avoidances = style.get("avoidances", [])

    # Mode-specific tone
    if mode == "technical":
        expected_tone = tone_profile.get("technical_mode", "N/A")
    elif mode == "nontechnical":
        expected_tone = tone_profile.get("reflective_mode", "N/A")
    else:  # ambiguous
        expected_tone = tone_profile.get("default", "N/A")

    ref = f"""
    Default tone: {tone_profile.get("default", "N/A")}
    Mode-specific tone ({mode}): {expected_tone}
    Written style: {written.get("tone", "N/A")}, {written.get("precision", "N/A")} precision
    Organization: {written.get("organization", "N/A")}
    Meta-reasoning: {written.get("meta_reasoning", "N/A")}
    Abstraction usage: {written.get("abstraction_usage", "N/A")}

    Response preferences:
    - Clarity over cleverness: {prefs.get("clarity_over_cleverness", "N/A")}
    - Depth over breadth: {prefs.get("depth_over_breadth", "N/A")}
    - Explicit tradeoffs: {prefs.get("explicit_tradeoffs", "N/A")}
    - Example-driven explanations: {prefs.get("example_driven_explanations", "N/A")}

    {", ".join(f"- {a}" for a in avoidances)}
    """.strip()

    return ref


_SYSTEM_PROMPT = """
    You are a persona consistency auditor for a digital twin system.
    Your job is to evaluate whether a twin's response is consistent with
    the person's defined values and communication style.

    You will be given:
    - The original query
    - The twin's response
    - The persona reference for each dimension

    Score each dimension from 1 to 5:
    5 — Fully consistent. The response strongly reflects the persona.
    4 — Mostly consistent. Minor gaps but nothing that feels out of character.
    3 — Partially consistent. Some alignment but notable inconsistencies.
    2 — Mostly inconsistent. The response often contradicts the persona.
    1 — Fully inconsistent. The response reads as a different person entirely.

    Be strict and specific. If you identify violations, quote the exact phrase
    from the response that caused the deduction.

    Return ONLY valid JSON. No prose, no markdown, no backtick fences.

    Output schema:
    {
    "values_alignment": {
        "score": <1–5>,
        "reasoning": "<1–2 sentence explanation>",
        "violations": ["<quoted phrase from response>", ...]
    },
    "tone_fidelity": {
        "score": <1–5>,
        "reasoning": "<1–2 sentence explanation>",
        "violations": ["<quoted phrase from response>", ...]
    }
    }
    """

_USER_TEMPLATE = """
## Values Reference
{values_reference}

## Tone Reference (Mode: {mode})
{tone_reference}

## Query
{query}

## Twin Response
{response}
"""


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------
def _parse_judge_output(raw: str) -> tuple[DimensionScore, DimensionScore]:
    """
    We parse the judge's JSON output to the DimensionScore objects
    ValueError raised with a descriptive message on malformed output
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Judge returned non-JSON output: {e}\n\nRaw:\n{raw}")

    def _extract(key: str) -> DimensionScore:
        block = data.get(key, {})
        score = int(block.get("score", 1))
        
        score = max(1, min(5, score))   # Clamp to valid range
        
        return DimensionScore(
            dimension=key,
            score=score,
            reasoning=block.get("reasoning", ""),
            violations=block.get("violations", []),
        )

    return _extract("values_alignment"), _extract("tone_fidelity")


def _weighted_score(va: DimensionScore, tf: DimensionScore) -> float:
    """
    Normalizing and applying weights
    """
    va_norm = (va.score - 1) / 4
    tf_norm = (tf.score - 1) / 4
    aggregate = (
        _WEIGHTS["values_alignment"] * va_norm +
        _WEIGHTS["tone_fidelity"]    * tf_norm
    )
    return round(aggregate, 3)


def check_persona_consistency(
    response: str,
    mode: str,
    query: str = "",
    model: str = "gpt-4o-mini",
) -> PersonaConsistencyResult:
    # Load identity context (cached by identity.py)
    identity = load_identity_context()

    # Build dynamic persona references
    values_ref = _build_values_reference(identity["traits"])
    tone_ref = _build_tone_reference(identity["style"], mode)

    client = OpenAI(api_key=OPENAI_API_KEY)

    user_message = _USER_TEMPLATE.format(
        values_reference=values_ref,
        tone_reference=tone_ref,
        mode=mode,
        query=query,
        response=response,
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=0,  # deterministic for evaluation
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        )

        raw = completion.choices[0].message.content.strip()
        va, tf = _parse_judge_output(raw)
        score = _weighted_score(va, tf)

        return PersonaConsistencyResult(
            values_alignment=va,
            tone_fidelity=tf,
            weighted_score=score,
            raw_response=raw,
        )

    except json.JSONDecodeError as e:
        # Return degraded result on JSON parse error
        return PersonaConsistencyResult(
            values_alignment=DimensionScore(
                dimension="values_alignment",
                score=1,
                reasoning="Evaluator error: malformed judge output",
                violations=[],
            ),
            tone_fidelity=DimensionScore(
                dimension="tone_fidelity",
                score=1,
                reasoning="Evaluator error: malformed judge output",
                violations=[],
            ),
            weighted_score=0.0,
            raw_response=str(e),
        )

    except Exception as e:
       
        return PersonaConsistencyResult(
            values_alignment=DimensionScore(
                dimension="values_alignment",
                score=1,
                reasoning=f"Evaluator error: {str(e)}",
                violations=[],
            ),
            tone_fidelity=DimensionScore(
                dimension="tone_fidelity",
                score=1,
                reasoning=f"Evaluator error: {str(e)}",
                violations=[],
            ),
            weighted_score=0.0,
            raw_response="",
        )


# ---------------------------------------------------------------------------
# For printing
# ---------------------------------------------------------------------------
def print_result(result: PersonaConsistencyResult) -> None:
    """Pretty-print the persona consistency result."""
    
    print(f"\nPersona Consistency Score: {result.weighted_score:.3f}  (0=none, 1=perfect)")
    print(f"  Weights: values_alignment={_WEIGHTS['values_alignment']}, "
          f"tone_fidelity={_WEIGHTS['tone_fidelity']}\n")

    for dim in (result.values_alignment, result.tone_fidelity):
        print(f"    {dim.reasoning}")
        if dim.violations:
            for v in dim.violations:
                print(v)
    print()
