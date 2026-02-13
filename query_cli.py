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

DIVIDER = "─" * 60


def format_response(result: dict, mode: str, scores: dict) -> str:
    lines = []
    lines.append(f"\n{DIVIDER}")
    lines.append(f"  Mode   : {mode}  (tech={scores['technical']:.3f}, non-tech={scores['nontechnical']:.3f})")

    if result["out_of_scope"]:
        lines.append(f"  Status : OUT OF SCOPE")
    else:
        lines.append(f"  Status : grounded ({len(result['citations'])} sources)")

    lines.append(DIVIDER)
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

        # Step 3: assemble context
        system_prompt, user_message = build_context(query, mode, chunks, out_of_scope)

        # Step 4: generate
        result = generate(system_prompt, user_message, chunks, out_of_scope)

        # Step 5: display
        print(format_response(result, mode, scores))


if __name__ == "__main__":
    run()