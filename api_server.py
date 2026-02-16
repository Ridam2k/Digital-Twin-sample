"""
FastAPI server

Run: uvicorn api_server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
from typing import Optional
from main_ingest import ingest_folder
from config import TECHNICAL_FOLDER_ID, NONTECHNICAL_FOLDER_ID
from main_ingest import ingest_github


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


class QueryRequest(BaseModel):
    query: str
    content_type: Optional[str] = None


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
        result = generate(system_prompt, user_message, chunks, out_of_scope)
        
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

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "digital-twin-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
