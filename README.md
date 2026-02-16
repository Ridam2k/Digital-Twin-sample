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
│
├── core/                  # Core RAG pipeline modules
│   ├── router.py          # Mode detection (technical/non-technical)
│   ├── retriever.py       # Semantic search
│   ├── context_builder.py # Prompt assembly
│   ├── generator.py       # LLM response generation
│   ├── groundedness.py    # Response grounding evaluation
│   ├── persona_consistency.py  # Persona alignment checks
│   └── retrieval_metrics.py    # Retrieval quality metrics
│
├── ingest/                # Ingestion modules
│   ├── gdrive_reader.py   # Google Drive integration
│   ├── github_reader.py   # GitHub repository processing
│   ├── chunker.py         # Text chunking and tagging
│   ├── embedder.py        # Embedding generation
│   └── *_hash_store.py    # Change detection stores
│
├── api/                   # API endpoints
│   └── eval_endpoints.py  # Evaluation API routes
│
├── data/                  # Data directory (gitignored)
│   ├── sources/           # Synthetic JSON documents
│   ├── github_hash_store.json
│   ├── gdrive_hash_store.json
│   └── synthetic_hash_store.json
│
└── frontend/              # React UI
    ├── package.json
    ├── src/
    │   ├── App.jsx        # Main application
    │   ├── components/    # UI components
    │   └── pages/         # Page components
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

## 🐛 Troubleshooting

### "No module named 'config'"
- Ensure `config.py` is in the project root
- Verify you've activated the virtual environment

### "Invalid credentials" from Google Drive
- Check `credentials.json` and `token.json` are present
- Re-authenticate if needed

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check CORS settings in `api_server.py`

### Empty search results
- Run `python main_ingest.py` to populate the database
- Verify Qdrant connection in `config.py`

---

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

**Built with**: FastAPI, React, Qdrant, OpenAI, LlamaIndex, Google Drive API
