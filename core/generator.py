import re
from openai import OpenAI
import tiktoken
from core.retriever import RetrievedChunk
from config import OPENAI_API_KEY, HISTORY_TOKEN_BUDGET

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
