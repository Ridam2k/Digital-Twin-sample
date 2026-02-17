"""
FastAPI server

Run: uvicorn api_server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from core.router import detect_mode
from core.retriever import retrieve
from core.context_builder import build_context
from core.generator import generate
from core.groundedness import check_groundedness
from core.persona_consistency import check_persona_consistency
from api.eval_endpoints import router as eval_router
import json
import datetime
from typing import Optional, AsyncGenerator, List
import asyncio
from main_ingest import ingest_folder
from config import TECHNICAL_FOLDER_ID, NONTECHNICAL_FOLDER_ID
from main_ingest import ingest_github
from qdrant_client import QdrantClient, models
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from pathlib import Path
from ingest.gdrive_reader import RateLimitedGoogleDriveReader


app = FastAPI(title="Digital Twin API", version="1.0.0")

# Mount eval endpoints
app.include_router(eval_router, prefix="/api/eval", tags=["evaluation"])

# CORS middleware - allow Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConversationTurn(BaseModel):
    role: str       # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    query: str
    content_type: Optional[str] = None
    history: List[ConversationTurn] = []


class Citation(BaseModel):
    index: int
    doc_title: str
    source_url: str
    score: float


class QueryResponse(BaseModel):
    response: str
    out_of_scope: bool
    citations: list[Citation]
    mode: str
    router_scores: dict[str, float]
    content_type: Optional[str] = None


class GithubIngestRequest(BaseModel):
    repos: Optional[list[str]] = None


GDRIVE_HASH_STORE_PATH = Path("data/gdrive_hash_store.json")
GDRIVE_NAME_MAP_PATH = Path("data/gdrive_name_map.json")


def _load_gdrive_id_set() -> set[str]:
    if not GDRIVE_HASH_STORE_PATH.exists():
        return set()
    try:
        data = json.loads(GDRIVE_HASH_STORE_PATH.read_text())
        return set(data.keys())
    except Exception:
        return set()


def _load_gdrive_name_map() -> dict[str, str]:
    if not GDRIVE_NAME_MAP_PATH.exists():
        return {}
    try:
        return json.loads(GDRIVE_NAME_MAP_PATH.read_text())
    except Exception:
        return {}


def _save_gdrive_name_map(name_map: dict[str, str]) -> None:
    GDRIVE_NAME_MAP_PATH.write_text(json.dumps(name_map, indent=2))


def _resolve_gdrive_names(file_ids: list[str]) -> dict[str, str]:
    if not file_ids:
        return {}
    name_map = _load_gdrive_name_map()
    missing = [fid for fid in file_ids if fid not in name_map]
    if not missing:
        return name_map

    if not Path("token.json").exists() or not Path("credentials.json").exists():
        return name_map

    reader = RateLimitedGoogleDriveReader(
        credentials_path="credentials.json",
        token_path="token.json",
        folder_id=None,
    )

    for fid in missing:
        try:
            info = reader.get_resource_info(fid)
            file_path = (info.get("file_path") or "").strip()
            name = file_path.split("/")[-1] if file_path else fid
            name_map[fid] = name
        except Exception:
            name_map[fid] = fid

    _save_gdrive_name_map(name_map)
    return name_map


def _gdrive_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"


def _enrich_citations(citations: list[dict]) -> list[dict]:
    """Fill in source_url for GDrive citations that have empty URLs."""
    gdrive_ids = _load_gdrive_id_set()
    name_map = _load_gdrive_name_map()
    for cite in citations:
        if cite.get("source_url"):
            continue
        doc_title = cite.get("doc_title", "")
        if doc_title in gdrive_ids:
            cite["source_url"] = _gdrive_url(doc_title)
            if doc_title in name_map:
                cite["doc_title"] = name_map[doc_title]
        elif "." in doc_title:
            stem = doc_title.rsplit(".", 1)[0]
            if stem in gdrive_ids:
                cite["source_url"] = _gdrive_url(stem)
                if stem in name_map:
                    cite["doc_title"] = name_map[stem]
    return citations


def _scroll_titles(
    client: QdrantClient,
    scroll_filter: models.Filter | None,
) -> dict[str, str]:
    """Return {doc_title: source_url} for all unique titles matching the filter."""
    title_urls: dict[str, str] = {}
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000,
            with_payload=["doc_title", "file_name", "source_url"],
            with_vectors=False,
            scroll_filter=scroll_filter,
            offset=offset,
        )
        if not points:
            break

        for p in points:
            payload = p.payload or {}
            title = (payload.get("doc_title") or payload.get("file_name") or "").strip()
            if title and title not in title_urls:
                title_urls[title] = (payload.get("source_url") or "").strip()

        if next_offset is None:
            break
        offset = next_offset

    return title_urls


def _build_filter(personality_ns: str | None, content_type: str | None) -> models.Filter | None:
    must = []
    if personality_ns:
        must.append(
            models.FieldCondition(
                key="personality_ns",
                match=models.MatchValue(value=personality_ns),
            )
        )
    if content_type:
        must.append(
            models.FieldCondition(
                key="content_type",
                match=models.MatchValue(value=content_type),
            )
        )
    return models.Filter(must=must) if must else None


def fetch_grouped_doc_titles() -> dict:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    technical_code = _scroll_titles(
        client,
        _build_filter("technical", "code"),
    )
    technical_docs = _scroll_titles(
        client,
        _build_filter("technical", "documentation"),
    )
    nontechnical_all = _scroll_titles(
        client,
        _build_filter("nontechnical", None),
    )

    client.close()

    gdrive_ids = _load_gdrive_id_set()
    all_titles = set(
        list(technical_code.keys())
        + list(technical_docs.keys())
        + list(nontechnical_all.keys())
    )
    ids_to_resolve = []
    for t in all_titles:
        if t in gdrive_ids:
            ids_to_resolve.append(t)
            continue
        if "." in t:
            stem = t.rsplit(".", 1)[0]
            if stem in gdrive_ids:
                ids_to_resolve.append(stem)
    name_map = _resolve_gdrive_names(ids_to_resolve)

    def _maybe_append_ext(name: str, ext: str) -> str:
        if not ext:
            return name
        if name.lower().endswith(f".{ext.lower()}"):
            return name
        return f"{name}.{ext}"

    def _map_titles(title_urls: dict[str, str]) -> list[dict]:
        """Map raw titles to {title, url} objects with name resolution."""
        mapped: dict[str, str] = {}  # display_name -> url
        for t, url in title_urls.items():
            # Google Drive name resolution
            if t in name_map:
                display = name_map[t]
                mapped[display] = url or _gdrive_url(t)
                continue
            if "." in t:
                stem, ext = t.rsplit(".", 1)
                if stem in name_map:
                    display = _maybe_append_ext(name_map[stem], ext)
                    mapped[display] = url or _gdrive_url(stem)
                    continue
            # Non-GDrive (GitHub) or unresolved
            mapped[t] = url
        return [
            {"title": name, "url": u}
            for name, u in sorted(mapped.items(), key=lambda x: x[0])
        ]

    technical_code_mapped = _map_titles(technical_code)
    technical_docs_mapped = _map_titles(technical_docs)
    nontechnical_mapped = _map_titles(nontechnical_all)

    seen = set()
    for item in technical_code_mapped + technical_docs_mapped + nontechnical_mapped:
        seen.add(item["title"])
    total_unique = len(seen)

    return {
        "total_unique": total_unique,
        "groups": {
            "technical": {
                "code": technical_code_mapped,
                "documentation": technical_docs_mapped,
            },
            "nontechnical": {
                "all": nontechnical_mapped,
            },
        },
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(req : QueryRequest):
    """
    Main query endpoint - runs the 6-stage pipeline and returns response.
    """
    print("Query: ", req)
    
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Step 1: Router - detect mode (technical/nontechnical/ambiguous)
        mode, scores = detect_mode(req.query)

        # Step 2: Retriever - get relevant chunks from vector DB
        chunks, out_of_scope = retrieve(
            req.query, namespace=mode,
            content_types=[req.content_type] if req.content_type else None,
        )

        retrieved_texts = [c.text for c in chunks]

        print("Chunks retreived")

        # Step 3: Assemble system prompt + user message
        system_prompt, user_message = build_context(
            req.query, mode, chunks, out_of_scope,
            content_type=req.content_type,
        )

        # Step 4: Get LLM response
        result = generate(system_prompt, user_message, chunks, out_of_scope, history=req.history)

        print("Response generated")

        # Step 5: Evaluation
        grounded_result = check_groundedness(
            response=result["response"],
            retrieved_chunks=retrieved_texts
        )

        persona_result = check_persona_consistency(
            response=result["response"],
            mode=mode,
            query=req.query
        )

        # Step 6: Logging 
        log_entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "query": req.query,
            "namespace": mode,
            "content_type": req.content_type,

            # Groundedness metrics
            "groundedness_score": grounded_result.groundedness_score,
            "fabricated_claims": grounded_result.fabricated_claims,
            "claim_audits": [vars(a) for a in grounded_result.claim_audits],

            # Persona consistency metrics
            "persona_consistency_score": persona_result.weighted_score,
            "persona_violations": (
                persona_result.values_alignment.violations +
                persona_result.tone_fidelity.violations
            ),
            "persona_dimension_scores": {
                "values_alignment": persona_result.values_alignment.score,
                "tone_fidelity": persona_result.tone_fidelity.score,
            },
            "persona_dimension_reasoning": {
                "values_alignment": persona_result.values_alignment.reasoning,
                "tone_fidelity": persona_result.tone_fidelity.reasoning,
            },

            "citation_scores": [c["score"] for c in result["citations"]]
        }
        
        with open("eval_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Enrich GDrive citations with URLs and resolved names
        result["citations"] = _enrich_citations(result["citations"])

        # Return API response (without evaluation metrics)
        return QueryResponse(
            response=result["response"],
            out_of_scope=result["out_of_scope"],
            citations=result["citations"],
            mode=mode,
            router_scores=scores,
            content_type=req.content_type,
        )

    except Exception as e:
        print(f"Pipeline error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {str(e)}"
        )


@app.post("/api/query/stream")
async def query_stream_endpoint(req: QueryRequest):
    """
    Streaming endpoint to returns response immediately and computes metrics in background.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Steps 1-4: Execute synchronously (router, retriever, context, generation)
            mode, scores = detect_mode(req.query)

            chunks, out_of_scope = retrieve(
                req.query,
                namespace=mode,
                content_types=[req.content_type] if req.content_type else None,
            )

            retrieved_texts = [c.text for c in chunks]

            system_prompt, user_message = build_context(
                req.query, mode, chunks, out_of_scope,
                content_type=req.content_type,
            )

            result = generate(system_prompt, user_message, chunks, out_of_scope, history=req.history)

            print("Response generated, streaming to client...")

            # Enrich GDrive citations with URLs and resolved names
            result["citations"] = _enrich_citations(result["citations"])

            # IMMEDIATE: Send response to client
            yield f"data: {json.dumps({
                'type': 'response',
                'data': {
                    'response': result['response'],
                    'citations': result['citations'],
                    'out_of_scope': out_of_scope,
                    'mode': mode,
                    'router_scores': scores,
                }
            })}\n\n"

            # BACKGROUND: Compute metrics asynchronously
            grounded_result = None
            persona_result = None

            # Groundedness evaluation
            try:
                grounded_result = await asyncio.to_thread(
                    check_groundedness,
                    response=result["response"],
                    retrieved_chunks=retrieved_texts
                )

                print("Groundedness evaluation complete")

                yield f"data: {json.dumps({
                    'type': 'metrics_groundedness',
                    'data': {
                        'groundedness_score': grounded_result.groundedness_score,
                        'fabricated_claims': grounded_result.fabricated_claims,
                        'claim_audits': [
                            {
                                'claim': a.claim,
                                'grounded': a.grounded,
                                'evidence': a.evidence
                            } for a in grounded_result.claim_audits
                        ],
                    }
                })}\n\n"
            except Exception as e:
                print(f"Groundedness evaluation failed: {e}")
                # Continue even if eval fails

            # Persona consistency evaluation
            try:
                persona_result = await asyncio.to_thread(
                    check_persona_consistency,
                    response=result["response"],
                    mode=mode,
                    query=req.query
                )

                print("Persona evaluation complete")

                yield f"data: {json.dumps({
                    'type': 'metrics_persona',
                    'data': {
                        'persona_consistency_score': persona_result.weighted_score,
                        'persona_violations': (
                            persona_result.values_alignment.violations +
                            persona_result.tone_fidelity.violations
                        ),
                        'dimension_scores': {
                            'values_alignment': persona_result.values_alignment.score,
                            'tone_fidelity': persona_result.tone_fidelity.score,
                        },
                        'dimension_reasoning': {
                            'values_alignment': persona_result.values_alignment.reasoning,
                            'tone_fidelity': persona_result.tone_fidelity.reasoning,
                        }
                    }
                })}\n\n"
            except Exception as e:
                print(f"Persona evaluation failed: {e}")
                # Continue even if eval fails

            # Log to eval_log.jsonl (reuse existing logging logic)
            log_entry = {
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "query": req.query,
                "namespace": mode,
                "content_type": req.content_type,

                # Groundedness metrics
                "groundedness_score": grounded_result.groundedness_score if grounded_result else None,
                "fabricated_claims": grounded_result.fabricated_claims if grounded_result else [],
                "claim_audits": [vars(a) for a in grounded_result.claim_audits] if grounded_result else [],

                # Persona consistency metrics
                "persona_consistency_score": persona_result.weighted_score if persona_result else None,
                "persona_violations": (
                    persona_result.values_alignment.violations +
                    persona_result.tone_fidelity.violations
                ) if persona_result else [],
                "persona_dimension_scores": {
                    "values_alignment": persona_result.values_alignment.score,
                    "tone_fidelity": persona_result.tone_fidelity.score,
                } if persona_result else {},
                "persona_dimension_reasoning": {
                    "values_alignment": persona_result.values_alignment.reasoning,
                    "tone_fidelity": persona_result.tone_fidelity.reasoning,
                } if persona_result else {},

                "citation_scores": [c["score"] for c in result["citations"]]
            }

            # Async file write to avoid blocking
            await asyncio.to_thread(
                lambda: open("eval_log.jsonl", "a").write(json.dumps(log_entry) + "\n")
            )

            print("Logged to eval_log.jsonl")

            # Signal completion
            yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"

        except Exception as e:
            # If error occurs before response is sent, send error event
            print(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({
                'type': 'error',
                'data': {'message': str(e)}
            })}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if deployed
        }
    )


@app.post("/api/ingest/gdrive")
async def ingest_gdrive_endpoint():
    """
    Triggers ingestion of both technical and non-technical Google Drive folders
    """
    try:
        # Ingest technical folder
        tech_result = ingest_folder(
            TECHNICAL_FOLDER_ID,
            "technical",
            "documentation"
        )

        # Ingest non-technical folder
        nontech_result = ingest_folder(
            NONTECHNICAL_FOLDER_ID,
            "nontechnical",
            "documentation"
        )

        return {
            "status": "success",
            "message": "Google Drive ingestion completed",
            "technical": tech_result,
            "nontechnical": nontech_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@app.post("/api/ingest/github")
async def ingest_github_endpoint(req: GithubIngestRequest = GithubIngestRequest()):
    """
    Triggers ingestion of configured GitHub repositories.
    Optionally accepts custom repos list.
    """
    try:
        # Use custom repos if provided, otherwise use config defaults
        repos = req.repos if req.repos else None
        result = ingest_github(repos=repos)

        return {
            "status": "success",
            "message": "GitHub ingestion completed",
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@app.get("/api/projects")
async def get_projects():
    """
    Returns unique doc_title values from Qdrant.
    """
    try:
        grouped = fetch_grouped_doc_titles()
        return {
            "collection": COLLECTION_NAME,
            "total_unique": grouped["total_unique"],
            "groups": grouped["groups"],
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving projects: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "digital-twin-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
