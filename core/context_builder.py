from core.identity import load_identity_context, build_system_prompt_block
from core.retriever import RetrievedChunk

_identity = None   # lazy-loaded once


def _get_identity():
    global _identity
    if _identity is None:
        _identity = load_identity_context()
    return _identity


def build_context(
    query:     str,
    mode:      str,
    chunks:    list[RetrievedChunk],
    out_of_scope: bool,
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_message) ready to pass to the LLM.
    """
    identity      = _get_identity()
    system_prompt = build_system_prompt_block(identity, mode)

    if out_of_scope or not chunks:
        user_message = (
            f"Question: {query}\n\n"
            f"[No sufficiently relevant context was retrieved. "
            f"Respond with the standard out-of-scope message.]"
        )
        return system_prompt, user_message

    evidence_lines = []
    for i, chunk in enumerate(chunks, 1):
        evidence_lines.append(
            f"[{i}] SOURCE: {chunk.doc_title} | score={chunk.score:.3f}\n"
            f"URL: {chunk.source_url}\n"
            f"{chunk.text.strip()}"
        )
    evidence_block = "\n\n---\n\n".join(evidence_lines)

    user_message = (
        f"Using only the evidence below, answer the following question.\n"
        f"Cite sources by their [number] inline where relevant.\n\n"
        f"## Retrieved Evidence\n\n{evidence_block}\n\n"
        f"## Question\n\n{query}"
    )

    return system_prompt, user_message