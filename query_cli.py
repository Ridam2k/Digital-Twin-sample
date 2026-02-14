"""
Interactive CLI for the digital twin.
Run: uv run query_cli.py

Commands:
  Type any question and press Enter to query.
  Type 'mode' to see which namespace was detected.
  Type 'exit' or Ctrl+C to quit.
"""

from core.router import detect_mode
from core.retriever import retrieve
from core.context_builder import build_context
from core.generator import generate
from core.groundedness import check_groundedness
from core.persona_consistency import check_persona_consistency
import json, datetime

DIVIDER = "─" * 60


def format_response(result: dict, mode: str, scores: dict,
                   grounded_result=None, persona_result=None) -> str:
    lines = []
    lines.append(f"\n{DIVIDER}")
    lines.append(f"  Mode   : {mode}  (tech={scores['technical']:.3f}, non-tech={scores['nontechnical']:.3f})")

    if result["out_of_scope"]:
        lines.append(f"  Status : OUT OF SCOPE")
    else:
        lines.append(f"  Status : grounded ({len(result['citations'])} sources)")

    # Persona consistency display
    # lines.append(f"  Persona: {persona_result.weighted_score:.2f} " +
    #             f"(values={persona_result.values_alignment.score}/5, " +
    #             f"tone={persona_result.tone_fidelity.score}/5)")

    # # Show violations if any
    # all_violations = (persona_result.values_alignment.violations +
    #                  persona_result.tone_fidelity.violations)
    # if all_violations:
    #     lines.append(f"  ⚠ Persona violations: {', '.join(all_violations[:2])}")

    # lines.append(DIVIDER)
    lines.append(result["response"])

    if result["citations"]:
        lines.append(f"\n{DIVIDER}")
        lines.append("  Sources:")
        for c in result["citations"]:
            lines.append(f"  [{c['index']}] {c['doc_title']} (score={c['score']})")
            if c["source_url"]:
                lines.append(f"       {c['source_url']}")

    lines.append(DIVIDER)
    return "\n".join(lines)


def run():
    print("\n Digital Twin — Query CLI")
    print(" Type your question. 'exit' to quit.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not query:
            continue
        if query.lower() == "exit":
            print("Bye.")
            break

        # Step 1: detect mode
        mode, scores = detect_mode(query)

        # Step 2: retrieve
        chunks, out_of_scope = retrieve(query, namespace=mode)
        
        retrieved_texts = [c.text for c in chunks]

        # Step 3: assemble context
        system_prompt, user_message = build_context(query, mode, chunks, out_of_scope)

        # Step 4: generate
        result = generate(system_prompt, user_message, chunks, out_of_scope)

        # Step 5: evaluation
       
        # Eval - Groundedness
        # grounded_result = check_groundedness(response=result["response"], retrieved_chunks=retrieved_texts)

        # # Eval - Persona Consistency
        # persona_result = check_persona_consistency(
        #     response=result["response"],
        #     mode=mode,
        #     query=query
        # )

        # Step 6: display
        # print(format_response(result, mode, scores, grounded_result, persona_result))
        print(format_response(result, mode, scores, None, None))

        # Log to JSONL — one record per query, append-only
        # log_entry = {
        #     "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        #     "query": query,
        #     "namespace": mode,

        #     # Groundedness metrics
        #     "groundedness_score": grounded_result.groundedness_score,
        #     "fabricated_claims": grounded_result.fabricated_claims,
        #     "claim_audits": [vars(a) for a in grounded_result.claim_audits],

        #     # Persona consistency metrics
        #     "persona_consistency_score": persona_result.weighted_score,
        #     "persona_violations": (
        #         persona_result.values_alignment.violations +
        #         persona_result.tone_fidelity.violations
        #     ),
        #     "persona_dimension_scores": {
        #         "values_alignment": persona_result.values_alignment.score,
        #         "tone_fidelity": persona_result.tone_fidelity.score,
        #     },
        #     "persona_dimension_reasoning": {
        #         "values_alignment": persona_result.values_alignment.reasoning,
        #         "tone_fidelity": persona_result.tone_fidelity.reasoning,
        #     },
        # }
        # with open("eval_log.jsonl", "a") as f:
        #     f.write(json.dumps(log_entry) + "\n")


if __name__ == "__main__":
    run()