"""
generate_eval_set.py
────────────────────
Generates a robust, difficulty-stratified evaluation dataset for the digital
twin RAG pipeline. Dynamically pulls documents from Qdrant and generates queries
with document-level gold references (robust to chunk ID changes).

Output schema (eval_set.json):
[
  {
    "query":      str,          # the test query
    "namespace":  str,          # "technical" | "nontechnical"
    "difficulty": str,          # "easy" | "medium" | "hard"
    "query_type": str,          # see DIFFICULTY TAXONOMY below
    "gold": {
      "doc_id":    str,         # stable document identifier (file_id from GDrive)
      "doc_title": str,         # human-readable document name
      "doc_hash":  str,         # SHA256 hash of full document text for integrity
    }
  },
  ...
]

DIFFICULTY TAXONOMY
───────────────────
easy   – direct / lexically close to source text
           → tests whether the vector store is populated correctly
medium – paraphrased / concept-mapped
           → tests semantic generalisation of embeddings
hard   – indirect / inferential / cross-domain
           → tests whether retrieval can bridge abstraction gaps

Usage:
    python generate_eval.py
Requires: OPENAI_API_KEY, Qdrant connection configured in config.py
"""

import json
import os
from pathlib import Path
from openai import OpenAI
from collections import Counter, defaultdict
from config import OPENAI_PVT_KEY
import hashlib
from qdrant_client import QdrantClient


DATA_DIR    = Path("data/")
OUTPUT_FILE = Path("eval_set.json")
MODEL       = "gpt-5.1"   #using own credentials for this task

client = OpenAI(api_key=OPENAI_PVT_KEY)

# Import Qdrant config
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME

client_qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


# ── Prompt template ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an evaluation dataset generator for a RAG-based digital twin system.
Your job is to generate realistic, diverse test queries that will be used to
evaluate the quality of a semantic retrieval pipeline.

The digital twin represents a real person. Queries will be asked by:
- Recruiters assessing fit
- Engineers evaluating technical depth
- Collaborators curious about working style
- Visitors exploring personal interests

You must generate queries across three difficulty levels:

EASY (direct):
  - Lexically close to the source text
  - A keyword from the source appears naturally in the query
  - Example seed "RAG pipeline architecture" → "How do you build a RAG pipeline?"

MEDIUM (paraphrased / concept-mapped):
  - Same intent but phrased differently; no direct keyword overlap with source
  - Requires semantic understanding to retrieve correctly
  - Example seed "RAG pipeline architecture" → "How would you approach building
    a system that retrieves context before generating an answer?"

HARD (indirect / inferential):
  - The query does NOT mention the topic directly
  - It requires the retriever to bridge an abstraction gap or infer relevance
  - Often cross-domain: e.g. asking about a behaviour that is *caused by* a skill
  - Example seed "RAG pipeline architecture" → "If you were debugging a hallucinating
    LLM product, where would you start?"

Rules:
  1. Output ONLY valid JSON — no markdown, no commentary.
  2. Each query must be answerable from the provided source text.
  3. Hard queries must be genuinely indirect — not just paraphrases with synonyms.
  4. Vary query length: some short (5–8 words), some conversational (15–25 words).
  5. Do not echo the seed field verbatim in the query text.
""".strip()

def compute_doc_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_user_prompt(
    source_text: str,
    doc_title:   str,
    namespace:   str,
    seed_field:  str = None,
    n_easy:      int = 2,
    n_medium:    int = 2,
    n_hard:      int = 2,
) -> str:
    seed_field_str = seed_field if seed_field else "N/A"
    return f"""
Generate evaluation queries for the following source chunk from a digital twin knowledge base.

SOURCE DOCUMENT: {doc_title}
NAMESPACE: {namespace}
SEED FIELD: {seed_field_str}

SOURCE TEXT:
\"\"\"
{source_text}
\"\"\"

Generate exactly {n_easy} EASY, {n_medium} MEDIUM, and {n_hard} HARD queries.

Return a JSON array with this exact schema per item:
{{
  "query":           "<the test query string>",
  "namespace":       "{namespace}",
  "difficulty":      "<easy|medium|hard>",
  "query_type":      "<direct|paraphrased|inferential|cross_domain|behavioural>"
}}
""".strip()


def fetch_documents_from_qdrant() -> list[dict]:
    """
    Fetch all chunks from Qdrant and reconstruct documents
    grouped by file_id (doc_id).
    """
    scroll_result, _ = client_qdrant.scroll(
        collection_name=COLLECTION_NAME,
        limit=1000,  # adjust if needed
        with_payload=True,
        with_vectors=False,
    )

    docs = defaultdict(list)

    for point in scroll_result:
        payload = point.payload

        # Map your actual Qdrant payload fields
        doc_id = payload.get("file id")  # GoogleDriveReader uses "file id"
        doc_title = payload.get("file_name")  # GoogleDriveReader uses "file_name"
        namespace = payload.get("personality_ns")  # Your namespace field
        # LlamaIndex stores text in payload under "_node_content" key as JSON string
        text = payload.get("_node_content", "")
        if text and isinstance(text, str):
            try:
                node_data = json.loads(text)
                text = node_data.get("text", "")
            except:
                text = ""

        if not doc_id or not text:
            continue

        docs[doc_id].append({
            "text": text,
            "doc_title": doc_title,
            "namespace": namespace
        })

    reconstructed_docs = []

    for doc_id, chunks in docs.items():
        # Reconstruct full text by concatenating chunks
        full_text = "\n".join(chunk["text"] for chunk in chunks)

        reconstructed_docs.append({
            "doc_id": doc_id,
            "doc_title": chunks[0]["doc_title"],
            "namespace": chunks[0]["namespace"],
            "full_text": full_text
        })

    return reconstructed_docs


def main():
    all_rows: list[dict] = []

    documents = fetch_documents_from_qdrant()

    print(f"Found {len(documents)} documents in Qdrant")
    count = 0
    
    for doc in documents:
        if (count == 2):
            break
        
        doc_id = doc["doc_id"]
        doc_title = doc["doc_title"]
        namespace = doc["namespace"]
        full_text = doc["full_text"]

        print(f"Generating queries for: {doc_title}")

        doc_hash = compute_doc_hash(full_text)

        # Reuse existing prompt builder
        prompt = build_user_prompt(
            source_text=full_text,
            doc_title=doc_title,
            namespace=namespace,
            seed_field=None,  # not needed anymore
            n_easy=2,
            n_medium=2,
            n_hard=2,
        )

        response = client.chat.completions.create(
            model=MODEL,
            max_completion_tokens=1024,
            temperature=0.7,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()
        count+=1

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        generated_rows = json.loads(raw.strip())

        # ✅ Inject robust gold structure
        for row in generated_rows:
            row["gold"] = {
                "doc_id": doc_id,
                "doc_title": doc_title,
                "doc_hash": doc_hash
            }

            # Remove legacy field if model included it
            row.pop("expected_source", None)

        all_rows.extend(generated_rows)

        print(f"  → {len(generated_rows)} queries generated")
    

    OUTPUT_FILE.write_text(json.dumps(all_rows, indent=2))
    print(f"\nDone. {len(all_rows)} total eval rows written to {OUTPUT_FILE}")

    by_difficulty = Counter(r["difficulty"] for r in all_rows)
    by_namespace  = Counter(r["namespace"]  for r in all_rows)
    print(f"  Difficulty split: {dict(by_difficulty)}")
    print(f"  Namespace split:  {dict(by_namespace)}")


if __name__ == "__main__":
    main()