from core.identity import load_identity_context, build_system_prompt_block
from core.retriever import RetrievedChunk

_identity = None   

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
    content_type: str = None,
) -> tuple[str, str]:

    identity      = _get_identity()
    system_prompt = build_system_prompt_block(identity, mode, content_type=content_type)

    if out_of_scope or not chunks:
        user_message = (
            f"Question: {query}\n\n"
            f"[No sufficiently relevant context was retrieved. "
            f"Respond with the standard out-of-scope message.]"
        )
        return system_prompt, user_message

    evidence_lines = []
    for i, chunk in enumerate(chunks):
        evidence_lines.append(
            f"[{i}] SOURCE: {chunk.doc_title} | score={chunk.score:.3f}\n"
            f"URL: {chunk.source_url}\n"
            f"{chunk.text.strip()}"
        )
    evidence_block = "\n\n---\n\n".join(evidence_lines)

    if content_type == "code":
        user_message = (
            f"Here is code and documentation from your repositories:\n\n"
            f"{evidence_block}\n\n"
            f"Now respond to this question about your code: {query}\n\n"
            f"(Reference specific files, functions, or repos where relevant. "
            f"Use [number] citations to link back to source chunks.)"
        )
    else:
        user_message = (
            f"Here's some context about this query:\n\n"
            f"{evidence_block}\n\n"
            f"Now respond naturally to this question: {query}\n\n"
            f"(You can reference sources with [number] if helpful, but integrate them naturally into your voice.)"
        )

    return system_prompt, user_message