from openai import OpenAI
import tiktoken
from core.retriever import RetrievedChunk
from config import OPENAI_API_KEY, HISTORY_TOKEN_BUDGET

_client = OpenAI(api_key=OPENAI_API_KEY)

GENERATION_MODEL = "gpt-4o-mini"
MAX_TOKENS       = 1024


def _truncate_history(history: list, budget: int) -> list:
    """Keep the most recent turns that fit within the token budget."""
    if not history:
        return []

    enc = tiktoken.encoding_for_model(GENERATION_MODEL)
    truncated = []
    used = 0

    for turn in reversed(history):
        content = turn.content if hasattr(turn, "content") else turn["content"]
        turn_tokens = len(enc.encode(content))
        if used + turn_tokens > budget:
            break
        truncated.append(turn)
        used += turn_tokens

    truncated.reverse()

    # Ensure history starts with a user message (trim orphaned assistant at start)
    while truncated and (truncated[0].role if hasattr(truncated[0], "role") else truncated[0]["role"]) == "assistant":
        truncated.pop(0)

    return truncated


def generate(
    system_prompt: str,
    user_message:  str,
    chunks:        list[RetrievedChunk],
    out_of_scope:  bool,
    history:       list = None,
) -> dict:
    """
    Structured Result
    {
        "response":     str,
        "out_of_scope": bool,
        "citations":    list[dict],   -> [{index, doc_title, source_url, score}]
    }
    """
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for turn in history:
            role = turn.role if hasattr(turn, "role") else turn["role"]
            content = turn.content if hasattr(turn, "content") else turn["content"]
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})
    
    print("Messages: ", messages)

    response = _client.chat.completions.create(
        model=GENERATION_MODEL,
        max_tokens=MAX_TOKENS,
        messages=messages,
        temperature=0.2,
    )

    answer = response.choices[0].message.content.strip()

    citations = []
    if not out_of_scope:
        for i, chunk in enumerate(chunks, 1):
            citations.append({
                "index":      i,
                "doc_title":  chunk.doc_title,
                "source_url": chunk.source_url,
                "score":      round(chunk.score, 3),
            })

    return {
        "response":     answer,
        "out_of_scope": out_of_scope,
        "citations":    citations,
    }