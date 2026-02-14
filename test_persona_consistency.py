#!/usr/bin/env python3
"""
Test suite for persona consistency evaluation.

Tests whether the persona evaluator correctly identifies:
1. Values alignment (technical rigor, explicit tradeoffs, etc.)
2. Tone fidelity (mode-appropriate tone, avoidances)
3. Mode sensitivity (different expectations for technical vs nontechnical)
4. Edge cases (out-of-scope, short responses, multiple violations)
"""

from core.persona_consistency import check_persona_consistency


def test_values_alignment():
    """Test detection of values violations"""

    print("\n" + "="*70)
    print("TEST: Values Alignment Detection")
    print("="*70)

    # PASS case: demonstrates technical rigor and explicit tradeoffs
    response_pass = """
    When choosing between microservices and monoliths, the key tradeoffs are:
    1. Operational complexity vs organizational scalability
    2. Deployment independence vs debugging simplicity
    3. Technology flexibility vs stack consistency

    For your context, I'd recommend starting with a modular monolith and extracting
    services only when you have clear boundaries and team scaling needs. The reason
    is that premature microservices introduce distributed system complexity before
    you've proven the domain model.
    """

    result = check_persona_consistency(
        response=response_pass,
        mode="technical",
        query="How do you choose between microservices and monoliths?"
    )

    print(f"PASS Case: values_alignment.score = {result.values_alignment.score}/5")
    print(f"  Reasoning: {result.values_alignment.reasoning}")

    assert result.values_alignment.score >= 4, \
        f"Expected high values alignment (>=4), got {result.values_alignment.score}"

    # FAIL case: violates "technical rigor" and "explicit tradeoffs"
    response_fail = "Just use microservices, they're better in every way! They're the future!"

    result = check_persona_consistency(
        response=response_fail,
        mode="technical",
        query="How do you choose between microservices and monoliths?"
    )

    print(f"\nFAIL Case: values_alignment.score = {result.values_alignment.score}/5")
    print(f"  Reasoning: {result.values_alignment.reasoning}")
    print(f"  Violations: {result.values_alignment.violations}")

    assert result.values_alignment.score <= 2, \
        f"Expected low values alignment (<=2), got {result.values_alignment.score}"
    assert len(result.values_alignment.violations) > 0, \
        "Expected violations to be detected"

    print("✅ PASS: Values Alignment Detection")


def test_tone_fidelity():
    """Test detection of tone violations"""

    print("\n" + "="*70)
    print("TEST: Tone Fidelity Detection")
    print("="*70)

    # PASS case: confident and analytical (technical mode)
    response_pass = """
    RAG pipeline architecture requires careful evaluation design. The key metrics
    to track are:
    - Retrieval precision@k (are the right chunks returned?)
    - Answer grounding score (is the response supported by retrieved context?)
    - Latency p95 (can you serve queries under SLA?)

    I've found that embedding quality matters more than retriever complexity for
    most use cases. Start with simple bi-encoder retrieval, measure hallucination
    rate, and only add reranking if you see systematic retrieval failures.
    """

    result = check_persona_consistency(
        response=response_pass,
        mode="technical",
        query="How do you evaluate RAG pipelines?"
    )

    print(f"PASS Case: tone_fidelity.score = {result.tone_fidelity.score}/5")
    print(f"  Reasoning: {result.tone_fidelity.reasoning}")

    assert result.tone_fidelity.score >= 4, \
        f"Expected high tone fidelity (>=4), got {result.tone_fidelity.score}"

    # FAIL case: violates "overly casual tone" and "hype-driven explanations"
    response_fail = """
    RAG is totally awesome! It's like, the coolest thing ever and will
    revolutionize everything lol 🚀 You should definitely use it for everything!
    It's gonna be huge!
    """

    result = check_persona_consistency(
        response=response_fail,
        mode="technical",
        query="How do you evaluate RAG pipelines?"
    )

    print(f"\nFAIL Case: tone_fidelity.score = {result.tone_fidelity.score}/5")
    print(f"  Reasoning: {result.tone_fidelity.reasoning}")
    print(f"  Violations: {result.tone_fidelity.violations}")

    assert result.tone_fidelity.score <= 2, \
        f"Expected low tone fidelity (<=2), got {result.tone_fidelity.score}"

    # Check that violations mention casual tone or hype
    violation_text = " ".join(result.tone_fidelity.violations).lower()
    assert any(word in violation_text for word in ["casual", "hype", "awesome", "lol"]), \
        f"Expected violations to mention casual tone or hype, got: {result.tone_fidelity.violations}"

    print("✅ PASS: Tone Fidelity Detection")


def test_mode_sensitivity():
    """Test that evaluation criteria change based on mode"""

    print("\n" + "="*70)
    print("TEST: Mode Sensitivity")
    print("="*70)

    # Introspective response - should score higher in nontechnical mode
    response = """
    I find that the most compelling aspect of this question lies in
    the underlying tension between immediate pragmatism and long-term
    architectural vision. On one hand, there's value in shipping quickly
    and learning from real usage. On the other, there's a cost to
    technical debt that compounds over time in ways that aren't always
    visible early on.
    """

    result_tech = check_persona_consistency(
        response=response,
        mode="technical",
        query="How do you balance speed and quality?"
    )

    result_nontech = check_persona_consistency(
        response=response,
        mode="nontechnical",
        query="How do you balance speed and quality?"
    )

    print(f"Technical mode: weighted_score = {result_tech.weighted_score:.3f}")
    print(f"  tone_fidelity = {result_tech.tone_fidelity.score}/5")
    print(f"\nNontechnical mode: weighted_score = {result_nontech.weighted_score:.3f}")
    print(f"  tone_fidelity = {result_nontech.tone_fidelity.score}/5")

    # The introspective tone should score higher in nontechnical mode
    # (where "reflective_mode" tone is expected)
    assert result_nontech.tone_fidelity.score >= result_tech.tone_fidelity.score, \
        "Introspective response should score higher in nontechnical mode"

    print("✅ PASS: Mode Sensitivity")


def test_out_of_scope_handling():
    """Test that even refusal responses maintain appropriate tone"""

    print("\n" + "="*70)
    print("TEST: Out-of-Scope Handling")
    print("="*70)

    response = "I don't have enough information about that in my current knowledge base."

    result = check_persona_consistency(
        response=response,
        mode="technical",
        query="What is your favorite restaurant?"
    )

    print(f"Out-of-scope response: tone_fidelity.score = {result.tone_fidelity.score}/5")
    print(f"  Reasoning: {result.tone_fidelity.reasoning}")

    # Should evaluate tone even for short responses
    assert result.tone_fidelity.score >= 3, \
        f"Refusal response should still maintain appropriate tone (>=3), got {result.tone_fidelity.score}"

    print("✅ PASS: Out-of-Scope Handling")


def test_integration_with_full_pipeline():
    """Test that persona eval works in full pipeline"""

    print("\n" + "="*70)
    print("TEST: Integration with Full Pipeline")
    print("="*70)

    from core.router import detect_mode
    from core.retriever import retrieve
    from core.context_builder import build_context
    from core.generator import generate
    from core.groundedness import check_groundedness

    query = "How do you approach evaluating RAG systems?"

    # Step 1: detect mode
    mode, scores = detect_mode(query)
    print(f"Detected mode: {mode}")

    # Step 2: retrieve
    chunks, out_of_scope = retrieve(query, namespace=mode)
    print(f"Retrieved {len(chunks)} chunks, out_of_scope={out_of_scope}")

    # Step 3: build context
    system_prompt, user_message = build_context(query, mode, chunks, out_of_scope)

    # Step 4: generate
    result = generate(system_prompt, user_message, chunks, out_of_scope)
    print(f"Generated response ({len(result['response'])} chars)")

    # Step 5a: check groundedness
    grounded_result = check_groundedness(
        response=result["response"],
        retrieved_chunks=[c.text for c in chunks]
    )
    print(f"Groundedness score: {grounded_result.groundedness_score:.2f}")

    # Step 5b: check persona consistency
    persona_result = check_persona_consistency(
        response=result["response"],
        mode=mode,
        query=query
    )
    print(f"Persona consistency score: {persona_result.weighted_score:.2f}")

    # Validate result structure
    assert 0.0 <= persona_result.weighted_score <= 1.0, \
        f"Weighted score should be in [0,1], got {persona_result.weighted_score}"

    assert len([persona_result.values_alignment, persona_result.tone_fidelity]) == 2, \
        "Should have exactly 2 dimension scores"

    assert persona_result.values_alignment.dimension == "values_alignment", \
        "First dimension should be values_alignment"

    assert persona_result.tone_fidelity.dimension == "tone_fidelity", \
        "Second dimension should be tone_fidelity"

    print(f"\n  Dimension scores:")
    print(f"    values_alignment: {persona_result.values_alignment.score}/5")
    print(f"    tone_fidelity: {persona_result.tone_fidelity.score}/5")

    print("✅ PASS: Integration with Full Pipeline")


def run_test_suite():
    """Run all tests"""
    tests = [
        ("Values Alignment Detection", test_values_alignment),
        ("Tone Fidelity Detection", test_tone_fidelity),
        ("Mode Sensitivity", test_mode_sensitivity),
        ("Out-of-Scope Handling", test_out_of_scope_handling),
        ("Integration with Full Pipeline", test_integration_with_full_pipeline),
    ]

    print("=" * 80)
    print("PERSONA CONSISTENCY TEST SUITE")
    print("=" * 80)

    passed = 0
    failed = []

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAIL: {name}")
            print(f"   {str(e)}")
            failed.append((name, str(e)))
        except Exception as e:
            print(f"\n⚠️  ERROR: {name}")
            print(f"   {str(e)}")
            failed.append((name, f"Error: {str(e)}"))

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(tests)} passed")
    if failed:
        print("\nFailed tests:")
        for name, error in failed:
            print(f"  - {name}: {error}")
    print("=" * 80)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_test_suite()
    exit(0 if success else 1)
