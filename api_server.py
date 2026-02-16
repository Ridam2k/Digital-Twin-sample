"""
FastAPI server exposing the digital twin query pipeline.

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
        chunks, out_of_scope = retrieve(req.query, namespace=mode)
        
        print()
        retrieved_texts = [c.text for c in chunks]
        
        print("Chunks retreived")

        # Step 3: Context Builder - assemble system prompt + user message
        system_prompt, user_message = build_context(
            req.query, mode, chunks, out_of_scope
        )

        # Step 4: Generator - get LLM response
        result = generate(system_prompt, user_message, chunks, out_of_scope)
        
        print("Response generated")

        # Step 5: Evaluation (backend-only, logged but not returned to frontend)
        # Eval 5a: Groundedness check
        grounded_result = check_groundedness(
            response=result["response"],
            retrieved_chunks=retrieved_texts
        )

        # Eval 5b: Persona consistency check
        persona_result = check_persona_consistency(
            response=result["response"],
            mode=mode,
            query=req.query
        )

        # Step 6: Logging (same format as CLI)
        log_entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "query": req.query,
            "namespace": mode,

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

            # Citation scores for similarity analysis
            "citation_scores": [c["score"] for c in result["citations"]]
        }
        with open("eval_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Return API response (evaluation metrics not included in response)
        return QueryResponse(
            response=result["response"],
            out_of_scope=result["out_of_scope"],
            citations=result["citations"],
            mode=mode,
            router_scores=scores
        )

    except Exception as e:
        # Log error for debugging
        print(f"Pipeline error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "digital-twin-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
