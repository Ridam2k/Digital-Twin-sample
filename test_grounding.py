#!/usr/bin/env python3
"""
Bleed detection test for writing samples.

This script tests whether opinions/facts from writing samples leak into
responses when they are NOT present in retrieved evidence.

Strategy:
1. Ask a question where writing samples contain a specific opinion
2. Provide retrieved evidence that does NOT contain that opinion
3. Check if the model asserts the opinion anyway (FAIL) or says "not enough info" (PASS)
"""

from core.identity import load_identity_context, build_system_prompt_block
from core.retriever import retrieve


def test_bleed_resistance():
    """
    Test: Can the model resist bleeding writing sample content into factual responses?

    If writing samples mention "I prefer X for reason Y" and retrieved evidence
    doesn't contain that preference, the model should NOT assert the preference.
    """

    identity = load_identity_context()
    system_prompt = build_system_prompt_block(identity, mode="technical")

    print("=" * 80)
    print("BLEED RESISTANCE TEST")
    print("=" * 80)
    print()
    print("System prompt grounding rules:")
    print("-" * 80)
    # Extract just the grounding rules section
    if "## Grounding Rules" in system_prompt:
        grounding_section = system_prompt.split("## Grounding Rules")[1].split("##")[0]
        print(grounding_section.strip())
    print("-" * 80)
    print()

    # Example test case (you'll customize this based on your actual writing samples)
    test_query = "What's your opinion on using microservices vs monoliths?"

    print(f"TEST QUERY: {test_query}")
    print()
    print("Step 1: Retrieve evidence from Qdrant...")

    # This will retrieve from your actual knowledge base
    try:
        results, out_of_scope = retrieve(test_query, namespace="technical")
        print(f"Retrieved {len(results)} chunks")
        print()

        if results:
            print("Retrieved evidence preview:")
            for i, chunk in enumerate(results[:2], 1):
                preview = chunk.text[:150].replace('\n', ' ')
                print(f"  [{i}] {preview}...")
            print()
        else:
            print("  (No chunks retrieved)")
            print()

        # Check if any retrieved chunk contains opinions about microservices
        contains_architecture_opinion = any(
            "microservice" in chunk.text.lower() or "monolith" in chunk.text.lower()
            for chunk in results
        )

        print(f"Retrieved evidence contains architecture opinions: {contains_architecture_opinion}")
        print()

        if contains_architecture_opinion:
            print("⚠️  WARNING: Retrieved evidence DOES contain relevant content.")
            print("   This test is inconclusive. Choose a question where your writing")
            print("   samples have opinions but your Qdrant data does NOT.")
            print()
        else:
            print("✓ Good test case: retrieved evidence lacks this specific opinion.")
            print()
            print("EXPECTED BEHAVIOR:")
            print('  Model should respond: "I don\'t have enough information..."')
            print()
            print("FAILURE MODE (if bleed occurs):")
            print("  Model asserts an architecture preference without citing evidence")
            print()

    except Exception as e:
        print(f"Could not retrieve: {e}")
        print("(This is fine for initial testing - just checking prompt structure)")
        print()

    print("=" * 80)
    print("Next steps:")
    print("1. Extract text from writing_samples/*.pdf")
    print("2. Inject 2-3 short excerpts (50-100 words each) into system prompt")
    print("3. Run this test with actual LLM to detect bleed")
    print("=" * 80)


if __name__ == "__main__":
    test_bleed_resistance()
