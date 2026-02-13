#!/usr/bin/env python3
"""
Full end-to-end bleed detection test with actual LLM calls.

This test verifies that writing sample content does NOT leak into factual responses
when the retrieved evidence doesn't support those claims.
"""

from openai import OpenAI
from core.identity import load_identity_context, build_system_prompt_block
from core.retriever import retrieve
from config import OPENAI_API_KEY


def format_retrieved_evidence(chunks: list) -> str:
    """Format retrieved chunks as the model expects to see them."""
    if not chunks:
        return "No relevant information found in knowledge base."

    evidence = "# Retrieved Evidence\n\n"
    for i, chunk in enumerate(chunks, 1):
        evidence += f"## Chunk {i}\n"
        evidence += f"Source: {chunk.doc_title}\n"
        evidence += f"Relevance Score: {chunk.score:.3f}\n\n"
        evidence += chunk.text + "\n\n"
        evidence += "---\n\n"

    return evidence


def run_bleed_test(query: str, namespace: str = "technical"):
    """
    Run a single bleed test.

    Args:
        query: The test question
        namespace: Which namespace to query

    Returns:
        dict with test results and analysis
    """
    print("=" * 80)
    print("BLEED RESISTANCE TEST - FULL LLM CALL")
    print("=" * 80)
    print()

    # 1. Load identity and build system prompt
    identity = load_identity_context()
    system_prompt = build_system_prompt_block(identity, mode=namespace)

    print(f"Writing samples loaded: {len(identity.get('writing_samples', []))} excerpts")
    print()

    # Show a preview of what's in writing samples (for analysis)
    samples = identity.get('writing_samples', [])
    if samples:
        print("Writing sample preview (first 150 chars of each):")
        for i, sample in enumerate(samples, 1):
            preview = sample[:150].replace('\n', ' ')
            print(f"  [{i}] {preview}...")
        print()

    # 2. Retrieve evidence
    print(f"TEST QUERY: {query}")
    print()
    print("Retrieving evidence from Qdrant...")

    chunks, out_of_scope = retrieve(query, namespace=namespace)
    print(f"Retrieved {len(chunks)} chunks (out_of_scope={out_of_scope})")
    print()

    if chunks:
        print("Retrieved evidence preview:")
        for i, chunk in enumerate(chunks[:2], 1):
            preview = chunk.text[:150].replace('\n', ' ')
            print(f"  [{i}] Score {chunk.score:.3f}: {preview}...")
        print()

    # 3. Format the full user message
    evidence_section = format_retrieved_evidence(chunks)
    user_message = f"{evidence_section}\n\nQuestion: {query}"

    # 4. Call the LLM
    print("Calling OpenAI GPT-4...")
    print()

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4o" for full GPT-4
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )

    answer = response.choices[0].message.content

    # 5. Analyze the response
    print("=" * 80)
    print("MODEL RESPONSE:")
    print("=" * 80)
    print(answer)
    print()
    print("=" * 80)

    # Check for bleed indicators
    insufficient_info_response = (
        "don't have enough information" in answer.lower() or
        "insufficient" in answer.lower() or
        "not enough information" in answer.lower() or
        "current knowledge base" in answer.lower()
    )

    # Check if response makes specific claims (heuristic: longer responses with technical terms)
    makes_specific_claims = len(answer.split()) > 50 and not insufficient_info_response

    print()
    print("ANALYSIS:")
    print("-" * 80)
    print(f"Response length: {len(answer.split())} words")
    print(f"Says 'insufficient info': {insufficient_info_response}")
    print(f"Makes specific claims: {makes_specific_claims}")
    print()

    if insufficient_info_response:
        print("✅ PASS: Model correctly refused to answer without evidence")
    elif makes_specific_claims and (not chunks or out_of_scope):
        print("❌ FAIL: Model made claims despite insufficient evidence")
        print("   This suggests content may be bleeding from writing samples")
    elif chunks and not out_of_scope:
        print("⚠️  INCONCLUSIVE: Retrieved evidence may contain the answer")
        print("   Choose a question where writing samples have opinions but Qdrant doesn't")
    else:
        print("⚠️  UNCLEAR: Manual review needed")

    print("=" * 80)

    return {
        "query": query,
        "answer": answer,
        "chunks_retrieved": len(chunks),
        "out_of_scope": out_of_scope,
        "insufficient_info_response": insufficient_info_response,
        "makes_specific_claims": makes_specific_claims,
    }


def run_test_suite():
    """Run multiple test cases to thoroughly check bleed resistance."""

    test_cases = [
        # Test 1: Question likely NOT in your knowledge base
        {
            "query": "What's your opinion on using microservices vs monoliths?",
            "namespace": "technical",
            "expected": "Should say insufficient info unless writing samples contain this opinion"
        },

        # Test 2: Another likely gap
        {
            "query": "What do you think about the future of quantum computing?",
            "namespace": "technical",
            "expected": "Should say insufficient info unless knowledge base has this"
        },

        # Test 3: Personal preference question
        {
            "query": "What's your favorite programming language and why?",
            "namespace": "technical",
            "expected": "Should say insufficient info unless explicitly documented"
        },
    ]

    print("Running bleed test suite...")
    print()

    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST CASE {i}/{len(test_cases)}")
        print(f"Expected behavior: {test['expected']}")
        print(f"{'='*80}\n")

        result = run_bleed_test(test['query'], test['namespace'])
        results.append(result)

        # Small pause between tests
        import time
        if i < len(test_cases):
            print("\n" + "="*80)
            time.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results if r['insufficient_info_response'])
    failed = sum(1 for r in results if r['makes_specific_claims'] and r['out_of_scope'])

    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print()

    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['insufficient_info_response'] else "❌ FAIL"
        print(f"{status} - Test {i}: {result['query'][:60]}...")

    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--suite":
        run_test_suite()
    else:
        # Single test mode
        query = "What's your opinion on using microservices vs monoliths?"
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])

        run_bleed_test(query)
