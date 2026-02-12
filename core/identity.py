import json
from pathlib import Path

DATA_DIR = Path("data/")


def load_identity_context() -> dict:
    """Loads all three JSON persona files. These are never chunked — always injected whole."""
    return {
        "skills": json.loads((DATA_DIR / "skills.json").read_text()),
        "traits": json.loads((DATA_DIR / "traits.json").read_text()),
        "style":  json.loads((DATA_DIR / "style.json").read_text()),
    }


def build_system_prompt_block(identity: dict, mode: str) -> str:
    """
    Builds the persona block injected at the top of every system prompt.
    mode: "technical" | "nontechnical"
    """
    traits = identity["traits"]
    style  = identity["style"]
    skills = identity["skills"]

    base = f"""You are a digital twin. Respond as the person described below. Only make claims that are grounded in the retrieved context provided to you. If retrieved context is insufficient, respond with: "I don't have enough information about that in my current knowledge base."

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
        skill_sample = ', '.join(skills['technical_skills']['systems_engineering'][:3])
        base += f"""
## Mode: Technical
- Tone: {style['tone_profile']['technical_mode']}
- Key skill areas include: {skill_sample} (and others in skills.json)
- Prioritise precision, explicit tradeoffs, and example-driven explanations.
"""
    else:
        base += f"""
## Mode: Non-Technical
- Tone: {style['tone_profile']['reflective_mode']}
- Draw on personal interests, debate background, and intellectual curiosity.
- Prioritise depth over breadth. Avoid hype-driven or surface-level responses.
"""

    return base.strip()
