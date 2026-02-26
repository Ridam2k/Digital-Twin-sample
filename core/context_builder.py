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
) -> tuple[str, str, dict | None]:
    # response_format_json = {
    # "response_text": "refers to a particular portion of the response",
    # "citation_number": "specific source chunk number based on which this portion of the response is generated",
    # "chunk_title": "title of this specific source chunk"  
    # } 
    
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "grounded_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "response_text": {"type": "string"},
                                "citation_number": {"type": "integer"},
                                "chunk_title": {"type": "string"}
                            },
                            "required": ["response_text", "citation_number", "chunk_title"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["items"],
                "additionalProperties": False
            }
        }
    }

    identity      = _get_identity()
    system_prompt = build_system_prompt_block(identity, mode, content_type=content_type)

    if out_of_scope or not chunks:
        user_message = (
            f"Question: {query}\n\n"
            f"[No sufficiently relevant context was retrieved. "
            f"Respond with the standard out-of-scope message.]"
        )
        return system_prompt, user_message, None

    evidence_lines = []
    for i, chunk in enumerate(chunks, 1):
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
            f"Return JSON only with this shape:\n"
            f"{{\"items\": [{{\"response_text\": \"...\", \"citation_number\": 1, \"chunk_title\": \"...\"}}]}}\n"
            f"Rules: one item per grounded sentence or short paragraph; "
            f"in response_text, reference specific files, functions, or repos where relevant; "
            f"citation_number must match the SOURCE number in the evidence block; "
            f"chunk_title must match the SOURCE title; "
            f"do NOT include [number] in response_text."
        )
    else:
        user_message = (
            f"Here's some context about this query:\n\n"
            f"{evidence_block}\n\n"
            f"Now respond naturally to this question: {query}\n\n"
            f"Return JSON only with this shape:\n"
            f"{{\"items\": [{{\"response_text\": \"...\", \"citation_number\": 1, \"chunk_title\": \"...\"}}]}}\n"
            f"Rules: one item per grounded sentence or short paragraph; "
            f"citation_number must match the SOURCE number in the evidence block; "
            f"chunk_title must match the SOURCE title; "
            f"do NOT include [number] in response_text."
            # f"(You can reference sources with [number] if helpful, but integrate them naturally into your voice.)"
            # f"While generating the response, explicitly mention the SOURCE number and CHUNK TITLE from the evidence block provided"
            # f"so that each portion of the response has the SOURCE number and CHUNK TITLE associated with it in the format of "
            # f"example - [number] SOURCE: {"chunk title"}"
        )

    return system_prompt, user_message, response_format
