import numpy as np
from llama_index.embeddings.openai import OpenAIEmbedding
from config import EMBEDDING_MODEL, OPENAI_API_KEY
import os

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

global _anchor_vecs

CONFIDENCE_THRESHOLD = 0.08

# new
_ANCHORS = {
    "technical": (
       # ML Systems & Optimization (Samsung, research)
        "How do I reduce model size using quantization-aware training?",
        "What are the tradeoffs between structured pruning and sparsity?",
        "How does binary neural network inference work on constrained devices?",
        "Explain early exit strategies for dynamic LLM inference",
        "How do I optimize CUDA kernels for on-device vision models?",

        # RAG & LLM Systems (Wells Fargo, projects)
        "How do I architect a production RAG pipeline for financial documents?",
        "What indexing strategy should I use with FAISS for low-latency retrieval?",
        "How does semantic caching improve RAG response time?",
        "Design an LLM agent with tool calling for document Q&A",
        "What evaluation metrics should I use for retrieval quality?",

        # Vision & Multimodal (ONR, Samsung)
        "How do I improve landmark detection accuracy with Vision Transformers?",
        "What's the best approach for real-time object detection under 30ms?",
        "How do I combine classical CV feature extraction with deep neural networks?",
        "Explain semantic segmentation pipelines for scene understanding",
        "How do vision-language models generate structured outputs from images?",

        # Systems & Backend (Wells Fargo, Amazon)
        "How do I design a high-throughput SQL-backed data service with Spring Boot?",
        "What's the best Kafka architecture for real-time analytics across 10+ consumers?",
        "How do I optimize schema design to reduce storage by 40%?",
        "Explain distributed computing with MPI and SLURM on HPC nodes",
        "How do I deploy containerized ML inference services with Kubernetes autoscaling?",

        # Research & Production Translation
        "How do I productionize a research model into a C++ latency-sensitive pipeline?",
        "What's the gap between a research RAG prototype and a production system?",
        "How do I measure goal alignment in LLM-guided search systems?",
        "Explain PEFT fine-tuning strategies for constrained reasoning tasks",
        "How do I design evaluation pipelines for agentic AI systems?",
   
    ),
    "nontechnical": (
        "debate speech argument rebuttal personal opinion hobby "
        "interest reading books travel values beliefs philosophy "
        "non-work life reflection essay topic discussion"
        "cooking recipes dance contemporary western ballet"
        "likes dislikes eating drinking food"
    ),
}

_embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL)
_anchor_vecs: dict[str, np.ndarray] = {}


# def _get_anchor_vecs() -> dict[str, np.ndarray]:
#     if not _anchor_vecs:
#         for ns, text in _ANCHORS.items():
#             vec = _embed_model.get_text_embedding(text)
#             _anchor_vecs[ns] = np.array(vec)
#     return _anchor_vecs


# def _cosine(a: np.ndarray, b: np.ndarray) -> float:
#     return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# def detect_mode(query: str) -> tuple[str, dict[str, float]]:
#     """
#     Returns (mode, scores) where:
#       mode   — "technical" or "nontechnical"
#       scores — {"technical": 0.82, "nontechnical": 0.61} for transparency
#     """
#     anchors  = _get_anchor_vecs()
#     qvec     = np.array(_embed_model.get_text_embedding(query))
#     scores   = {ns: _cosine(qvec, vec) for ns, vec in anchors.items()}
#     mode     = max(scores, key=scores.get)
#     return mode, scores

# Cache: maps each utterance string -> np.ndarray
_utterance_vecs: dict[str, np.ndarray] = {}


def _get_utterance_vecs() -> dict[str, dict[str, list[np.ndarray]]]:
    """
    Returns a nested dict: { namespace -> { utterance -> vec } }
    Embeddings are computed once and cached in _utterance_vecs.
    """
    result: dict[str, list[np.ndarray]] = {}
    for ns, utterances in _ANCHORS.items():
        vecs = []
        for utt in utterances:
            if utt not in _utterance_vecs:
                _utterance_vecs[utt] = np.array(_embed_model.get_text_embedding(utt))
            vecs.append(_utterance_vecs[utt])
        result[ns] = vecs
    return result


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def detect_mode(query: str) -> tuple[str, dict[str, float]]:
    """
    Scores the query against every utterance in each namespace,
    takes the max per-namespace (nearest-neighbor, not centroid),
    then applies a confidence margin check.

    Returns:
        mode   – "technical", "nontechnical", or "ambiguous"
        scores – {"technical": 0.82, "nontechnical": 0.61} for transparency
    """
    ns_vecs = _get_utterance_vecs()
    qvec = np.array(_embed_model.get_text_embedding(query))

    # Score each namespace as the MAX cosine similarity across its utterances.
    # This is a nearest-neighbor decision rather than centroid, which preserves
    # intra-class variance and avoids outlier utterances dragging the mean.
    scores: dict[str, float] = {
        ns: max(_cosine(qvec, vec) for vec in vecs)
        for ns, vecs in ns_vecs.items()
    }

    sorted_scores = sorted(scores.values(), reverse=True)
    best, second = sorted_scores[0], sorted_scores[1]
    margin = best - second

    if margin < CONFIDENCE_THRESHOLD:
        return "ambiguous", scores

    mode = max(scores, key=scores.get)
    return mode, scores






