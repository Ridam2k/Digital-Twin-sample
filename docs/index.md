# Digital Twin Project Workflow

This document describes how the project’s core classes, functions, and modules work together to deliver ingestion, retrieval, response generation, and observability. It is written from the code as it exists in this repo.

## System Map (Modules That Orchestrate Everything)

1. Ingestion entrypoint: `main_ingest.py` and endpoints in `api_server.py`
2. Query runtime: `api_server.py` or `query_cli.py`
3. Core RAG pipeline: `core/router.py`, `core/retriever.py`, `core/context_builder.py`, `core/generator.py`
4. Evaluators: `core/groundedness.py`, `core/persona_consistency.py`
5. Observability APIs: `api/eval_endpoints.py`, models in `api/models.py`
6. Frontend: `frontend/src/App.jsx` and `frontend/src/api/client.js`

---

## Architectural Rationale (High Level)

- Separation of concerns: ingestion, retrieval, generation, and evaluation live in discrete modules to keep components swappable and testable.
- Qdrant as vector store: purpose-built, scalable retrieval backend with metadata filtering; LlamaIndex is used for orchestration, not storage.
- LlamaIndex for parsing/chunking: reduces boilerplate while producing consistent node metadata and optional relationships.
- Deterministic chunk IDs: enable idempotent ingests and safe deletions when files change.
- Dual-persona routing: reduces retrieval noise by constraining search space to the most relevant namespace.
- Streaming responses + background metrics: low latency for users while still capturing evaluation signals.
- Observability APIs: metrics are surfaced consistently for manual tuning and regression monitoring.

---

## Ingestion Workflow (Google Drive, GitHub, Synthetic)

The ingestion pipeline is executed in `main_ingest.py` and can be triggered from the API via `/api/ingest/*` routes in `api_server.py`.

### 1) Source Readers (Extract Raw Documents)

1. Google Drive: `ingest/gdrive_reader.py`
   - `RateLimitedGoogleDriveReader` extends `GoogleDriveReader` with retry/backoff.
   - `get_gdrive_reader(folder_id)` returns a reader configured with `credentials.json` and `token.json`.
2. GitHub: `ingest/github_reader.py`
   - `fetch_repo_files(repo_name)` crawls a repo using `Github` (PyGithub), filters by extension, skips `GITHUB_IGNORE_PATTERNS`, and returns file dicts.
   - `files_to_documents(files)` wraps those dicts into `llama_index.core.Document` with metadata.
3. Synthetic: `ingest/synthetic_reader.py`
   - `load_synthetic_document(path)` loads JSON into a `Document`.
   - Validates `personality_ns` against `PERSONALITY_NAMESPACES` from `config.py`.

### 2) Change Detection (Skip Unchanged Files)

Each source has a hash store that records prior ingests and Qdrant point IDs.

1. GitHub: `ingest/hash_store.py`
   - `is_changed(store, file_key, current_sha)` determines whether a file changed.
   - `record_file(...)` stores new SHA and point IDs.
   - `get_old_point_ids(...)` returns IDs for deletion on updates.
2. Google Drive: `ingest/gdrive_hash_store.py`
   - `is_gdrive_changed(store, file_id, modified_time)` uses Drive `modified_time`.
   - `record_gdrive_file(...)` and `get_old_gdrive_point_ids(...)`.
3. Synthetic: `ingest/synthetic_hash_store.py`
   - `is_synthetic_changed(store, file_name, current_sha)` uses SHA256 of file contents.
   - `record_synthetic_file(...)` and `get_old_synthetic_point_ids(...)`.

These are used inside:

1. `main_ingest.ingest_folder(...)` for Google Drive
2. `main_ingest.ingest_github(...)` for GitHub
3. `main_ingest.ingest_synthetic(...)` for synthetic JSON

Each ingest function deletes stale Qdrant points before re-upserting with new embeddings.

### 3) Chunking and Metadata Tagging

`ingest/chunker.py` is the canonical place where metadata is added to every chunk.

1. `tag_and_chunk(documents, personality_ns, content_type)`:
   - Uses `SentenceSplitter` with `CHUNK_SIZE` and `CHUNK_OVERLAP` from `config.py`.
   - Adds metadata: `personality_ns`, `content_type`, `chunk_index`, `chunk_total`, `ingested_at`.
   - Derives `doc_title` from `file path` or `file name`.
   - Creates deterministic `node_id` UUIDs from `file_id|namespace|content_type|chunk_index`.

The deterministic ID design enables `main_ingest.py` to safely delete old chunks when a file changes.

### 4) Embeddings and Qdrant Upsert

`ingest/embedder.py` handles vector generation and storage.

1. `ensure_collection(client)`:
   - Creates Qdrant collection and payload indexes for `personality_ns` and `content_type`.
2. `_embed_texts(texts)`:
   - Uses OpenAI embeddings with `EMBEDDING_MODEL` from `config.py`.
3. `upsert_nodes(client, nodes)`:
   - Filters empty nodes.
   - Produces `PointStruct` with payload fields that retriever expects:
     `text`, `doc_title`, `source_url`, `personality_ns`, `content_type`,
     `chunk_index`, `chunk_total`, `ingested_at`, `file_name`, `file_path`.
   - Calls `client.upsert(...)` to Qdrant.

### 5) Orchestration Entry Points

`main_ingest.py` ties the above together:

1. `ingest_folder(TECHNICAL_FOLDER_ID, "technical", "documentation")`
2. `ingest_folder(NONTECHNICAL_FOLDER_ID, "nontechnical", "documentation")`
3. `ingest_github()` uses `GITHUB_REPOS`
4. `ingest_synthetic()` ingests `data/sources/*.json`

API equivalents in `api_server.py`:

1. `POST /api/ingest/gdrive` → `ingest_folder(...)` for both namespaces.
2. `POST /api/ingest/github` → `ingest_github(repos=...)`.

---

## Query Runtime Workflow (RAG + Dual Persona)

Queries can be executed via REST (`api_server.py`) or CLI (`query_cli.py`). Both use the same core pipeline.

### 1) Router: Select Persona Namespace

`core/router.py`

1. `detect_mode(query)`:
   - Embeds the query with `OpenAIEmbedding`.
   - Compares against `_ANCHORS` per namespace using cosine similarity.
   - Returns `mode` and `scores`.
   - If the top-two margin is below `CONFIDENCE_THRESHOLD`, returns `"ambiguous"`.

### 2) Retriever: Fetch Evidence From Qdrant

`core/retriever.py`

1. `retrieve(query, namespace, content_types=None)`:
   - Embeds query via `OpenAIEmbedding`.
   - Uses Qdrant `query_points` with filters:
     `personality_ns` and optionally `content_type`.
   - Returns a list of `RetrievedChunk` dataclass instances and an `out_of_scope` flag.
   - If `namespace == "ambiguous"`, `_query_namespace(...)` is run for each namespace and results are merged.
   - `out_of_scope` is computed from `OUT_OF_SCOPE_THRESHOLD`.

The `RetrievedChunk` dataclass (`core/retriever.py`) is the shared record passed to later steps:

1. `text`
2. `score`
3. `doc_title`
4. `source_url`
5. `chunk_index`
6. `personality_ns`
7. `content_type`

### 3) Context Builder: Build Prompt and Evidence Block

`core/context_builder.py`

1. `build_context(query, mode, chunks, out_of_scope, content_type=None)`:
   - Pulls persona identity via `load_identity_context()` from `core/identity.py`.
   - Builds the system prompt with `build_system_prompt_block(...)`.
   - Assembles retrieved evidence into a `[i] SOURCE: ...` block.
   - If `out_of_scope` is True, returns a standard instruction to answer out of scope.
   - For `content_type == "code"` it instructs the model to reference files, functions, and repos.

### 4) Generator: LLM Response + Citation Packaging

`core/generator.py`

1. `generate(system_prompt, user_message, chunks, out_of_scope, history=None)`:
   - Builds OpenAI Chat Completion call with `GENERATION_MODEL = "gpt-4o-mini"`.
   - Includes optional `history` (passed from frontend).
   - `answer` is cleaned via `_strip_markdown_emphasis`.
   - Returns:
     `response`, `out_of_scope`, and `citations` (from retrieved chunks).

The citation list is aligned with the `RetrievedChunk` order and uses 1-based indexing.

### 5) Evaluators (Optional but default in API)

#### Generation-Level
`core/groundedness.py`

1. `check_groundedness(response, retrieved_chunks)`:
   - Uses an LLM judge to extract claims and label them as `SUPPORTED`, `INFERRED`, or `FABRICATED` by passing retrieved chunks and asking the LLM to evaluate
   - Returns `GroundednessResult` with per-claim audits and a numeric score

`core/persona_consistency.py`

1. `check_persona_consistency(response, mode, query)`:
   - Also uses LLM as judge
   - Loads persona via `load_identity_context()`
   - Builds values and tone references from `traits.json` and `style.json`
   - Returns `PersonaConsistencyResult` with dimension scores and a weighted score

### Retrieval-Level
This is the offline evaluation for the retriever only (not generation). It answers: “Does the retriever return chunks from the correct document for a given query?”

#### Eval Set Generation
`utility/generate_eval.py`

1. Reconstructs full documents from Qdrant by grouping chunks on `(personality_ns, doc_title)`:
   - `fetch_documents_from_qdrant()` scrolls Qdrant, sorts by `chunk_index`, and concatenates the chunk `text`.
2. For each reconstructed document:
   - Calls an LLM (`MODEL = "gpt-5.1"`) to generate 3 queries (easy/medium/hard) that are answerable from that document
   - Adds a `gold` label containing:
     `doc_title`, `doc_title_hash` (namespace-qualified), and `doc_hash`
3. Writes the dataset to `eval_set.json`

This creates a document‑level gold standard: each query is tied to the source document it came from

#### Eval Computation
`core/retrieval_metrics.py`

1. Loads `eval_set.json`
2. For each query (currently a random sample of 50):
   - Calls `retrieve(query, namespace)` to fetch top‑K chunks
   - Converts each chunk’s `doc_title` into a `doc_title_hash(namespace, title)`.
3. Computes:
   - **Recall@K**: whether the gold document appears in the top‑K results
   - **MRR@K**: reciprocal rank of the gold document within the top‑K list
4. Returns overall + per‑namespace metrics and caches them in `retrieval_stats.json`

#### What These Metrics Indicate (Diagnostic)
- **Recall@K** measures whether retrieval is hitting the *right document* at all.
- **MRR@K** measures how *early* the correct document appears in the results.
- These are **document‑level** retrieval signals; they do not measure answer quality or grounding.

#### How They Are Used to Improve Retrieval Quality (Practice)
- **Chunking and indexing**: sweep `CHUNK_SIZE`, `CHUNK_OVERLAP`, and metadata inclusion; keep settings that raise Recall@K without tanking MRR@K.
- **Retriever variants**: compare embedding models or distance functions; choose the model with higher Recall@K/MRR@K on the same eval set.
- **Hybrid retrieval**: evaluate vector-only vs. hybrid (BM25 + vectors). Recall@K typically moves first when hybrid is beneficial.
- **Re‑ranking**: add a cross‑encoder reranker on top‑N candidates. Use MRR@K to validate that the correct document is pushed earlier even if Recall@K stays flat.
- **Threshold tuning**: adjust `OUT_OF_SCOPE_THRESHOLD` using Recall@K drops at low confidence as a proxy for missed retrievals.
- **Regression gating**: compare metrics across runs; if Recall@K or MRR@K regresses, block deployment or revert.

Layer 1 – Retrieval Quality
- Recall@K (hit rate for correct document)
- MRR@K (ranking quality for correct document)
- Re‑ranking effectiveness (MRR@K delta with/without cross‑encoder)

Layer 2 – Contract Enforcement
- Confidence gating
- Out‑of‑scope detection
- Refusal behavior

Layer 3 – Generation Quality (Implemented)
- Groundedness (evidence alignment to retrieved chunks, faithfulness)
- Persona consistency (alignment with twin identity & tone)

Layer 4 – Advanced Generation Evaluation (Future Work)
- RAGAS‑style LLM judging
- Automated hallucination detection

### 6) API Endpoints that Orchestrate the Pipeline

`api_server.py`

1. `POST /api/query`:
   - Executes all steps synchronously.
   - Logs metrics to `eval_log.jsonl`.
   - Uses `_enrich_citations(...)` to resolve Google Drive links and names.
2. `POST /api/query/stream`:
   - Runs steps 1–4, sends response immediately via SSE.
   - Runs evaluators asynchronously and streams metrics events.
3. `GET /api/projects`:
   - `fetch_grouped_doc_titles()` uses Qdrant `scroll` to group doc titles by namespace/content type.
   - Resolves Google Drive IDs to names with `_resolve_gdrive_names(...)`.

The request/response schemas are defined by Pydantic models:

1. `ConversationTurn`, `QueryRequest`, `Citation`, `QueryResponse` in `api_server.py`
2. Eval response models in `api/models.py`

### 7) CLI Query (Local Testing)

`query_cli.py`

1. Uses the same `detect_mode → retrieve → build_context → generate` sequence.
2. Adds `@code` prefix handling to set `content_type="code"`.
3. Prints the answer and citation list.

---

## Frontend Workflow

The React frontend mirrors the backend pipeline through API calls defined in `frontend/src/api/client.js`.

### 1) Chat Flow (Streaming)

1. `frontend/src/App.jsx`
   - `handleQuery(...)` builds `history` from previous messages.
   - Calls `streamQuery(...)` from `frontend/src/api/client.js`.
2. `streamQuery(...)`:
   - `POST /api/query/stream`
   - Parses SSE events:
     `response`, `metrics_groundedness`, `metrics_persona`, `done`, `error`
3. Response updates the chat UI (status, citations, out-of-scope)

### 2) Observability Dashboard

`frontend/src/pages/ObservabilityPage.jsx` renders the panels that call:

1. `fetchEvalMetrics()` → `GET /api/eval/metrics`
2. `fetchRetrievalStats()` → `GET /api/eval/retrieval-stats`
3. `fetchDbStats()` → `GET /api/eval/db-stats`
4. `fetchSimilarityStats()` → `GET /api/eval/similarity-stats`

### 3) Ingestion Controls and Projects List

`frontend/src/components/Avatar/AvatarPanel.jsx`

1. `ingestGoogleDrive()` → `POST /api/ingest/gdrive`
2. `ingestGithub()` → `POST /api/ingest/github`
3. `fetchProjects()` → `GET /api/projects`

This panel displays grouped project lists and provides buttons to trigger ingestion.

---

## Observability and Metrics Flow

Metrics are computed and exposed by `api/eval_endpoints.py` using utilities in `core/`.

1. `aggregate_eval_logs(...)` in `core/eval_aggregator.py`
   - Reads `eval_log.jsonl`
   - Returns summary stats and recent entries
2. `aggregate_similarity_stats(...)` in `core/eval_aggregator.py`
   - Computes score distributions and out-of-scope rates from `citation_scores`
3. `compute_retrieval_metrics(...)` in `core/retrieval_metrics.py`
   - Loads `eval_set.json`
   - Runs `retrieve(...)` and computes Recall@K / MRR@K
   - Caches result in `retrieval_stats.json`

These functions are surfaced as:

1. `GET /api/eval/metrics`
2. `GET /api/eval/retrieval-stats`
3. `GET /api/eval/db-stats`
4. `GET /api/eval/similarity-stats`

---

## Persona and Identity Inputs

Persona configuration is injected into the system prompt by `core/identity.py`:

1. `data/skills.json`
2. `data/traits.json`
3. `data/style.json`
4. Optional writing samples from `data/writing_samples/*.pdf` via `core/pdf_extractor.py`

These are combined in `build_system_prompt_block(...)` and then used by the generator.

---

## Configuration Flow (config.py)

`config.py` defines constants used throughout the system:

1. Qdrant config: `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME`
2. Embeddings: `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`
3. Chunking: `CHUNK_SIZE`, `CHUNK_OVERLAP`
4. Routing and retrieval: `PERSONALITY_NAMESPACES`, `CONTENT_TYPES`, `SOURCE_TYPES`, `SOURCE_TYPE_MIME_MAPPING`
5. Ingestion: `TECHNICAL_FOLDER_ID`, `NONTECHNICAL_FOLDER_ID`, `GITHUB_REPOS`
6. Storage: `HASH_STORE_PATH`, `GDRIVE_HASH_STORE_PATH`, `SYNTHETIC_HASH_STORE_PATH`

Note: `HISTORY_TOKEN_BUDGET` and `MAX_HISTORY_TURNS` are currently not enforced by the backend; the frontend truncates history in `frontend/src/App.jsx`.

---

## Supporting Scripts

1. `scripts/export_doc_titles.py`
   - Scrolls Qdrant and exports unique doc titles to `data/doc_titles.json`.
   - Uses Google Drive name resolution similar to `/api/projects`.
2. `utility/generate_eval.py` and `utility/generate_synthetic_data.py`
   - Generate evaluation sets and synthetic documents.
3. `eval_retrieval.py` and test files in the root
   - Provide additional evaluation and verification utilities.

---

## Future Enhancements: Org-Level Privileged Access Controls

### From Static Tokens to Policy-Driven Connector Governance

#### Current State
The system currently connects to Google Drive and GitHub using stored OAuth tokens and credentials. While functional, this model has limitations:

- Privileged actions (e.g., writes) are implicitly controlled in code.
- Connector access is effectively global once tokens are stored.
- Admins lack visibility and control over integration risk.
- There is limited separation between read and write capabilities.

This approach works for prototyping but does not meet enterprise governance expectations.

#### Proposed Improvement: Organization-Configurable Access Policies
Introduce an organization-level connector policy layer that replaces global privileged gates with admin-controlled toggles.

Each organization will define:
- `enabled`: whether the connector can be used
- `allow_write`: whether write operations are permitted

All connector actions will pass through a centralized policy check before execution.

#### Workflow Improvements

1. Policy Check Before Token Usage  
   Instead of:
   `feature → use stored token → call API`  
   The improved workflow becomes:
   `feature → policy validation → token validation → provider API call`

   This ensures:
   - Disabled connectors cannot be used even if tokens exist.
   - Write operations are blocked unless explicitly enabled.
   - Access decisions are consistent and centralized.

2. Write Access Requires Explicit Re-Authorization  
   If an admin enables write access:
   - The system will trigger OAuth reauthorization.
   - Elevated scopes will be requested.
   - Tokens will be rotated and updated.
   - Policy state and OAuth scopes will remain aligned.

   This prevents scope drift and enforces least-privilege by default.

3. Administrative Governance & Auditability  
   Enhancements will include:
   - Admin-only integration controls.
   - Audit logs for:
     - Connector enable/disable events
     - Write permission changes
     - Reauthorization events

   This introduces enterprise-grade visibility and compliance readiness.

---

## End-to-End Functional Flow Summary

1. Ingest: Documents and code are read (`gdrive_reader`, `github_reader`, `synthetic_reader`).
2. Chunk: `tag_and_chunk(...)` splits and tags content with metadata and deterministic IDs.
3. Embed + Upsert: `upsert_nodes(...)` writes vectors and payloads to Qdrant.
4. Query: `detect_mode(...)` → `retrieve(...)` → `build_context(...)` → `generate(...)`.
5. Evaluate: `check_groundedness(...)` and `check_persona_consistency(...)`.
6. Serve: `api_server.py` returns response (REST or streaming).
7. Observe: `eval_endpoints.py` aggregates logs and retrieval stats for the dashboard.

This is the core loop that connects ingestion, persona routing, retrieval, generation, and observability into a single coherent system.
