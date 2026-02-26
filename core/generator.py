import json
import re
from openai import OpenAI
import tiktoken
from core.retriever import RetrievedChunk
from config import OPENAI_API_KEY, HISTORY_TOKEN_BUDGET
# from types import Any

_client = OpenAI(api_key=OPENAI_API_KEY)

GENERATION_MODEL = "gpt-4o-mini"
MAX_TOKENS       = 1024


def _strip_markdown_emphasis(text: str) -> str:
    """Remove GPT-style emphasis markers and map '*' bullets to '-'."""
    if not text:
        return text

    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("* "):
            indent = " " * (len(line) - len(stripped))
            line = f"{indent}- {stripped[2:]}"
        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", text)
    return text


def _format_structured_response(raw_content: str) -> str:
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        return raw_content.strip()

    items = payload.get("items")
    if not isinstance(items, list):
        return raw_content.strip()

    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("response_text", "")).strip()
        if not text:
            continue
        citation_number = item.get("citation_number")
        if isinstance(citation_number, int) and citation_number > 0:
            text = f"{text} [{citation_number}]"
        parts.append(text)

    return " ".join(parts).strip()


def generate(
    system_prompt: str,
    user_message:  str,
    chunks:        list[RetrievedChunk],
    out_of_scope:  bool,
    response_format_json,
    history,
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

    request_params = {
        "model": GENERATION_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": messages,
        "temperature": 0.2,
    }
    if response_format_json:
        request_params["response_format"] = response_format_json

    response = _client.chat.completions.create(**request_params)

    raw_content = response.choices[0].message.content.strip()
    answer = _format_structured_response(raw_content) if response_format_json else raw_content
    answer = _strip_markdown_emphasis(answer)

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
