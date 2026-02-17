# Digital Twin - RAG-based Dual Persona AI Assistant

A sophisticated Retrieval-Augmented Generation (RAG) system that creates a personalized AI assistant with dual personas (technical and non-technical). The system ingests data from Google Drive, GitHub repositories, and synthetic sources, then provides intelligent responses with proper source attribution.

## 🌟 High-Level User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION                            │
│  Google Drive (Docs/PDFs/Slides) + GitHub Repos + Synthetic     │
│                            ↓                                     │
│                  Chunking & Embedding                            │
│                            ↓                                     │
│                    Qdrant Vector DB                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                │
│                            ↓                                     │
│              Mode Detection (Technical/Non-technical)            │
│                            ↓                                     │
│        Semantic Retrieval (with optional @code filtering)        │
│                            ↓                                     │
│              Context Building + LLM Generation                   │
│                            ↓                                     │
│              Response with Citations & Evaluation                │
└─────────────────────────────────────────────────────────────────┘
```

### Detailed Flow:
1. **Ingestion**: Documents are fetched from Google Drive folders, GitHub repositories, and local synthetic data
2. **Processing**: Content is chunked, tagged with metadata (personality namespace, content type), and embedded
3. **Storage**: Embeddings stored in Qdrant vector database with metadata for filtering
4. **Query Processing**:
   - User submits query (optionally prefixed with `@code` for code-specific queries)
   - Router detects appropriate personality mode (technical/non-technical)
   - Retriever performs semantic search with optional content-type filtering
   - Context builder assembles relevant chunks with system prompts
   - Generator produces response with proper citations
5. **Evaluation**: Optional groundedness and persona consistency checks
6. **Frontend**: React-based UI with conversation interface and observability metrics

---

## 📋 Prerequisites

- **Python**: 3.9+ (developed with Python 3.12)
- **Node.js**: 16+ (for frontend)
- **pip** or **uv** package manager
- **Git** (for cloning repositories)

---

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd DT
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Install Dependencies

```bash
uv sync
```

### 3. Configuration Files (Provided Offline)

The following files contain sensitive credentials and will be provided separately:

- **`credentials.json`**: Google Drive OAuth credentials
- **`token.json`**: Google Drive authentication token
- **`config.py`**: Contains API keys and configuration:
  - Qdrant database URL and API key
  - OpenAI API keys (for embeddings and generation)
  - Google Drive folder IDs (technical and non-technical) 
  - GitHub personal access token
  - Collection names, chunk sizes, and other parameters

- The project setup currently connects to my(Ridam Srivastava's) Google Drive folders and Github Repos that have been granted access for the same; configuring to your own Drive and Github would require additional steps for setting up access

**⚠️ Important**: Place these files in the project root directory before proceeding

### 4. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

## 🏃 Running the Application

### Option 1: Full Stack (Recommended)

#### Terminal 1 - Start Backend API Server

```bash
source .venv/bin/activate  # Activate virtual environment
uvicorn api_server:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

#### Terminal 2 - Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The UI will be available at `http://localhost:3000`

### Option 2: CLI Query Interface

For quick testing without the UI:

```bash
source .venv/bin/activate
python query_cli.py
```

**Usage**:
- Type queries directly
- Prefix with `@code` for code-specific queries (e.g., `@code how does authentication work?`)
- Type `exit` to quit

---

## 📊 Data Ingestion

### Initial Data Ingestion

- The following files would be provided to DIRECTLY run the retrieval: data/gdrive_hash_store.json, data/github_hash_store.json, data/synthetic_hash_store.json
- If these files are put into the data folder, then the ingestion step DOES NOT need to be run for the app to be run locally, as the associated files are ALREADY present in the QDRANT client

- If running the ingestion flow from scratch:
- First run the deletions script to delete the existing data points: 

Then ingest data sources as:

```bash
source .venv/bin/activate
python main_ingest.py
```

This will:
- Fetch documents from configured Google Drive folders (technical & non-technical)
- Clone and process configured GitHub repositories
- Process synthetic JSON documents from `data/sources/`
- Embed and store everything in Qdrant

**Note**: The system uses hash-based change detection, so subsequent runs only process new or modified files.

### Ingestion Details

- **Google Drive**: Supports Google Docs, PDFs, and Presentations
- **GitHub**: Processes code files (`.py`, `.js`, `.jsx`, `.css`, `.html`, `.ipynb`) and documentation (`.md`)
- **Synthetic**: Custom JSON documents from `data/sources/` directory

---

## 🏗️ Project Structure

```
DT/
├── api_server.py          # FastAPI backend server
├── main_ingest.py         # Data ingestion pipeline
├── query_cli.py           # CLI interface
├── config.py              # Configuration (gitignored)
├── credentials.json       # Google OAuth (gitignored)
├── token.json             # Google token (gitignored)
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Python project metadata
├── uv.lock                # uv lockfile
├── generate_eval.py       # Evaluation dataset generation
├── generate_synthetic_data.py # Synthetic data generator
├── eval_retrieval.py      # Retrieval evaluation runner
├── eval_set.json          # Evaluation dataset
├── eval_log.jsonl         # Evaluation run logs
├── retrieval_stats.json   # Aggregated retrieval stats
├── quick_fix.py           # Utility script
├── test_persona_consistency.py # Tests
├── test_bleed_full.py     # Tests
├── verify_checkpoint1.py  # Checkpoint verification
├── verify_checkpoint2.py  # Checkpoint verification
├── verify_checkpoint3.py  # Checkpoint verification
│
├── core/                  # Core RAG pipeline modules
│   ├── router.py          # Mode detection (technical/non-technical)
│   ├── retriever.py       # Semantic search
│   ├── context_builder.py # Prompt assembly
│   ├── generator.py       # LLM response generation
│   ├── groundedness.py    # Response grounding evaluation
│   ├── persona_consistency.py  # Persona alignment checks
│   ├── retrieval_metrics.py    # Retrieval quality metrics
│   ├── eval_aggregator.py  # Eval aggregation utilities
│   ├── pdf_extractor.py    # PDF parsing utilities
│   ├── identity.py         # Persona/identity helpers
│   └── __init__.py
│
├── ingest/                # Ingestion modules
│   ├── gdrive_reader.py   # Google Drive integration
│   ├── github_reader.py   # GitHub repository processing
│   ├── synthetic_reader.py # Synthetic JSON ingestion
│   ├── chunker.py         # Text chunking and tagging
│   ├── embedder.py        # Embedding generation
│   ├── hash_store.py      # Hash store base class
│   ├── gdrive_hash_store.py # Google Drive change detection
│   ├── synthetic_hash_store.py # Synthetic change detection
│   └── __init__.py
│
├── api/                   # API endpoints
│   ├── eval_endpoints.py  # Evaluation API routes
│   ├── models.py          # API request/response models
│   └── __init__.py
│
├── data/                  # Data assets and hash stores (partially gitignored)
│   ├── sources/           # Synthetic JSON documents
│   ├── writing_samples/   # PDF writing samples
│   ├── traits.json
│   ├── skills.json
│   ├── style.json
│   ├── gdrive_name_map.json
│   ├── github_hash_store.json
│   ├── gdrive_hash_store.json
│   └── synthetic_hash_store.json
│
├── scripts/               # One-off scripts
│   └── export_doc_titles.py
│
├── utility/               # Maintenance utilities
│   ├── delete_collection.py
│   ├── generate_eval.py
│   └── generate_synthetic_data.py
│
└── frontend/              # React UI
    ├── index.html
    ├── package-lock.json
    ├── package.json
    ├── src/
    │   ├── App.jsx        # Main application
    │   ├── App.css
    │   ├── main.jsx       # Vite entrypoint
    │   ├── api/           # API client utilities
    │   ├── pages/         # Page components
    │   ├── styles/        # Global tokens/styles
    │   └── mock/          # Local mock data
    └── vite.config.js
```

---

## 🔑 Key Features

### Dual Personality Mode
- **Technical**: Responds with technical depth, uses jargon, includes code snippets
- **Non-technical**: Simplified explanations, accessible language, concept-focused

### Content Type Filtering
- Use `@code` prefix to filter retrieval to code-related content only
- Ensures code queries retrieve implementation details, not just documentation

### Smart Retrieval
- Semantic search using OpenAI embeddings
- Configurable similarity thresholds
- Out-of-scope detection for irrelevant queries

### Source Attribution
- All responses include citations to source documents
- Links to original files (Google Drive URLs, GitHub file paths)

### Evaluation Metrics
- **Groundedness**: Checks if response claims are supported by retrieved context
- **Persona Consistency**: Validates alignment with personality mode
- **Retrieval Quality**: Precision, recall, and F1 score tracking

---

## 🛠️ API Endpoints

### Core Endpoints

- `POST /api/query` - Submit query and get response
- `GET /api/health` - Health check

### Evaluation Endpoints

- `POST /api/eval/generate-set` - Generate evaluation dataset
- `POST /api/eval/run` - Run evaluation on query set
- `GET /api/eval/results` - Fetch evaluation results

### Ingestion Endpoints

- `POST /api/ingest/gdrive` - Trigger Google Drive ingestion
- `POST /api/ingest/github` - Trigger GitHub ingestion
- `POST /api/ingest/synthetic` - Trigger synthetic data ingestion

---

## 📝 Environment Variables (Optional)

While most configuration is in `config.py`, you can optionally use environment variables:

```bash
export QDRANT_URL="your-qdrant-url"
export QDRANT_API_KEY="your-api-key"
export OPENAI_API_KEY="your-openai-key"
```

## 📚 Configuration Guide

Edit `config.py` to customize:

- **Chunking**: `CHUNK_SIZE`, `CHUNK_OVERLAP`
- **Embedding Model**: `EMBEDDING_MODEL`, `EMBEDDING_DIM`
- **Data Sources**:
  - `TECHNICAL_FOLDER_ID`, `NONTECHNICAL_FOLDER_ID`
  - `GITHUB_REPOS` list
- **Source Types**: `SOURCE_TYPES`, `CONTENT_TYPES`
- **GitHub Settings**: `GITHUB_ALLOWED_EXTENSIONS`, `GITHUB_IGNORE_PATTERNS`

---

## 🧪 Testing

### Test Persona Consistency
```bash
python test_persona_consistency.py
```

### Test Grounding and Bleeding
```bash
python test_bled_full.py
```

### Run Retrieval Evaluation
```bash
python eval_retrieval.py
```

---

--- 

## Steps to setup own ingestion pipeline

### Google Drive
1. Create a Google Cloud project, enable the Google Drive API, and create OAuth client credentials.
2. Download the OAuth client JSON and place it at the repo root as `credentials.json` (same level as `config.py`).
3. Decide which Google Drive folder you want to ingest and copy its folder ID from the URL.
4. Set the folder ID in `config.py` if you’re using `main_ingest.py` (`TECHNICAL_FOLDER_ID` / `NONTECHNICAL_FOLDER_ID`), or pass it directly to `get_gdrive_reader(folder_id)` if you call it yourself
5. Run your ingest flow once; the first run will open a browser for OAuth and create `token.json` at the repo root (this is the cached auth token used on subsequent runs)
6. Re-run ingest as needed; the cached `token.json` is reused automatically

### GitHub
1. Create a GitHub personal access token with read access to the repos you want to ingest
2. Set that token in `config.py` as `GITHUB_TOKEN`
3. Add repo names (`"owner/repo"`) to `GITHUB_REPOS` in `config.py` (or pass a list to `ingest_github(repos=...)`)
4. Verify file filters: `GITHUB_ALLOWED_EXTENSIONS` and `GITHUB_IGNORE_PATTERNS` in `config.py` control what gets ingested
5. Run the ingest flow; it uses `fetch_repo_files()` to traverse repos and pull eligible files

**Built with**: FastAPI, React, Qdrant, OpenAI, LlamaIndex, Google Drive API
