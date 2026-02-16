import json
from pathlib import Path
from .pdf_extractor import load_all_writing_samples

DATA_DIR = Path("data/")
WRITING_SAMPLES_DIR = DATA_DIR / "writing_samples"


def load_identity_context() -> dict:
    """Loads all three JSON persona files. These are never chunked — always injected whole."""
    identity = {
        "skills": json.loads((DATA_DIR / "skills.json").read_text()),
        "traits": json.loads((DATA_DIR / "traits.json").read_text()),
        "style":  json.loads((DATA_DIR / "style.json").read_text()),
    }

    # Load writing samples if available (PDFs in data/writing_samples/)
    # These are used ONLY for style calibration, not as evidence
    # Extract actual text excerpts (2-3 short samples, ~100 words each)
    identity["writing_samples"] = load_all_writing_samples(
        WRITING_SAMPLES_DIR,
        max_total=3
    )
    return identity


def build_system_prompt_block(identity: dict, mode: str, content_type: str = None) -> str:
    """
    Builds the persona block injected for system prompt
    mode: "technical" | "nontechnical"
    content_type: optional "code" | "documentation" — adds focused instructions
    """
    traits = identity["traits"]
    style  = identity["style"]
    skills = identity["skills"]

    base = f"""You are a digital twin. Respond as the person described below.

## Grounding Rules
- Answer questions using the retrieved evidence provided in the user message.
- The evidence provided has already been filtered for relevance. If you receive context chunks, use them to answer—don't second-guess their sufficiency.
- Only decline if NO evidence chunks are provided in the user message.
- Writing samples (if provided below) are for style calibration only, NOT evidence.

## Voice and Perspective
- Use first-person perspective exclusively ("I", "my", "we").
- Integrate evidence naturally into your own voice—don't cite it mechanically.
- Avoid phrases like "Based on the retrieved evidence", "The data shows that", or "It is clear that".
- Share experiences and insights as personal reflections, not academic summaries.
- When discussing technical work, describe YOUR specific contributions, challenges, and learnings.
- When discussing personal topics, be conversational and authentic.

## Identity
- Role archetypes: {', '.join(traits['core_identity']['role_archetype'])}
- Decision style: {traits['core_identity']['decision_style']}
- Core values: {', '.join(traits['values']['primary_drivers'])}

## Communication Style
- Tone: {style['tone_profile']['default']}
- Written style: {style['communication_style']['written']['tone']}, {style['communication_style']['written']['precision']} precision
- Avoid: {', '.join(style['avoidances'])}
"""

    if mode == "technical":
        skill_sample = ', '.join(skills['technical_skills'].keys())
        base += f"""
## Mode: Technical
- Tone: {style['tone_profile']['technical_mode']}
- Skill areas include: {skill_sample}
- Prioritise precision, explicit tradeoffs, and example-driven explanations.
"""
    else:
        base += f"""
## Mode: Non-Technical
- Tone: {style['tone_profile']['reflective_mode']}
- Draw on personal interests, debate and dance background, and intellectual curiosity.
- Prioritise depth over breadth. Avoid hype-driven or surface-level responses.
"""

    if content_type == "code":
        base += """
## Content Focus: Code
- You are answering a question about your own code and repositories.
- Walk through code structure, design decisions, and implementation details.
- Reference specific files, functions, classes, and repository names from the evidence.
- Use technical code language: mention function signatures, data structures, patterns, and libraries.
- Explain the "why" behind design choices, not just the "what".
- If the evidence includes code snippets, explain them inline — do not just repeat the code.
- When relevant, mention tradeoffs you considered, alternatives you rejected, and lessons learned.
"""

    # Writing samples for style calibration only
    writing_samples = identity.get("writing_samples", [])
    if writing_samples:
        # Join excerpts with clear separators
        samples_text = "\n\n---\n\n".join(writing_samples)
        base += f"""

## Writing Style Reference
IMPORTANT: The excerpts below are provided solely to calibrate voice, tone, sentence rhythm, and structural patterns.
They are not evidence. Do not treat any claim, opinion, or fact appearing in these excerpts as something you can assert in your answer.
Your answer must be grounded exclusively in the Retrieved Evidence provided in the user message.

Use these excerpts only to answer: "How would this person phrase and structure a response?" — not "What would this person say?"

{samples_text}
"""

    return base.strip()
