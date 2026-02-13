from openai import OpenAI
from core.retriever import RetrievedChunk
from config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)

GENERATION_MODEL = "gpt-4o-mini"
MAX_TOKENS       = 1024


def generate(
    system_prompt: str,
    user_message:  str,
    chunks:        list[RetrievedChunk],
    out_of_scope:  bool,
) -> dict:
    """
    Calls gpt-4o-mini and returns a structured result:
    {
        "response":     str,          # the generated answer
        "out_of_scope": bool,
        "citations":    list[dict],   # [{index, doc_title, source_url, score}]
    }
    """
    response = _client.chat.completions.create(
        model=GENERATION_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_message},
        ],
        temperature=0.3,    # low temp — grounded, consistent, not creative
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