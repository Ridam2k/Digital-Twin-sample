# Writing Sample Bleed Prevention Strategy

## Problem
Writing samples contain opinions, facts, and positions. Without strong boundaries, the model can "bleed" this content into responses — treating sample content as evidence rather than just style templates.

## Solution: Three-Layer Defense

### 1. Explicit Grounding Rules (in `core/identity.py`)
```python
## Grounding Rules (CRITICAL)
1. Only make claims that are grounded in the Retrieved Evidence section provided below.
2. Every factual claim must be traceable to a specific retrieved chunk.
3. If retrieved evidence is insufficient, respond with: "I don't have enough information..."
4. Never assert opinions, facts, or positions from writing samples as if they are evidence.
```

**Why this works:**
- Placed BEFORE style/identity blocks → establishes factual faithfulness as highest-priority constraint
- "Never assert... from writing samples" directly names the failure mode
- Requires citation → makes silent bleed harder

### 2. Writing Sample Boundary Instructions
```python
## Writing Style Reference
IMPORTANT: Writing samples (when provided) are for voice, tone, sentence rhythm,
and structural patterns ONLY. They are not evidence. Do not treat any claim, opinion,
or fact in writing samples as something you can assert.

Your answer must be grounded exclusively in the Retrieved Evidence section.

Use writing samples only to answer: "How would this person phrase and structure
a response?" — not "What would this person say?"
```

**Why this works:**
- "They are not evidence" → directly counters model's default behavior of treating system prompt content as authoritative
- Task redirection → gives model a concrete mental model (phrasing ≠ content)
- Exclusive grounding → removes ambiguity about where facts come from

### 3. Automated Bleed Detection (`test_grounding.py`)
Test strategy:
1. Ask question Q where writing samples contain opinion X
2. Ensure retrieved evidence does NOT contain X
3. Check if model asserts X anyway (FAIL) or says "insufficient info" (PASS)

**Example test:**
```python
# If writing samples mention "I prefer microservices because..."
# but Qdrant has no architecture opinions:
test_query = "What's your opinion on microservices vs monoliths?"

# PASS: "I don't have enough information about that in my current knowledge base."
# FAIL: "I prefer microservices because..." (bleeding sample content)
```

## Current Status

✅ Grounding rules strengthened in `build_system_prompt_block()`
✅ Writing sample boundary instructions added
✅ Test harness created (`test_grounding.py`)
⏳ TODO: Extract text from `data/writing_samples/*.pdf` and inject 2-3 excerpts (50-100 words each)
⏳ TODO: Run actual LLM test to verify bleed resistance

## When to Escalate to Two-Pass Approach

If simple prompt engineering fails the bleed test, use architectural separation:

**Pass 1:** Generate fully grounded response (no writing samples in context)
**Pass 2:** Rephrase response using writing samples for style transfer only

This makes content bleed **structurally impossible** rather than just prompt-instructed.

## Test Results

Run: `python test_grounding.py`

Current test query: "What's your opinion on using microservices vs monoliths?"
- Retrieved evidence contains this topic: **No** ✓
- Expected behavior: Model should say "I don't have enough information..."
- Result: (pending PDF extraction and LLM integration)
