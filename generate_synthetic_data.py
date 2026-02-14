"""
Synthetic Data Generation for Digital Twin

Usage:
    python scripts/generate_synthetic_data.py [--dry-run] [--output-dir data/sources]

Generates first-person synthetic documents grounded in persona JSONs (skills.json, traits.json, style.json).
Each document is written AS the person, matching their communication style and knowledge domains.
"""

import json
import os
import argparse
from pathlib import Path
from openai import OpenAI
from config import OPENAI_API_KEY


def load_persona_context():
    """Load persona JSONs and build system context for generation."""
    skills = json.loads(Path("data/skills.json").read_text())
    traits = json.loads(Path("data/traits.json").read_text())
    style = json.loads(Path("data/style.json").read_text())

    persona_block = f"""
You are generating synthetic first-person documents for a digital twin.
Write AS this person, matching their communication style and knowledge.

TRAITS: {json.dumps(traits, indent=2)}

STYLE: {json.dumps(style, indent=2)}

SKILLS: {json.dumps(skills, indent=2)}

CRITICAL RULES:
- Write in first person ("I worked on...", "In my experience...", "What I've learned...")
- Match the tone profile from style.json (thoughtful, direct, analytical, semi-formal)
- Stay grounded in the skills and experiences listed above — do NOT invent capabilities
- Be specific and concrete, not generic (reference actual technologies, frameworks, metrics)
- Vary length: 150-500 words per document
- Use structured explanations with clear reasoning
- Avoid overly casual tone, hype-driven language, and surface-level responses
- Include explicit tradeoffs when discussing technical decisions
- Use example-driven explanations where appropriate
- Show depth-seeking intellectual orientation through layered analysis
"""
    return persona_block


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT SPECIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

DOCUMENT_SPECS = [
    # ────────────────────────────────────────────────────────────────────────────
    # TECHNICAL (25 documents)
    # ────────────────────────────────────────────────────────────────────────────

    # Project Writeups (8 docs)
#     {
#         "doc_title": "Building a RAG Pipeline for Investment Banking Analysts",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write a detailed first-person account of designing and building a RAG pipeline for an investment banking analyst query system. Cover:

# - The problem: analysts needed fast access to internal documentation, deal memos, and research reports
# - Architecture decisions: why you chose Qdrant over Pinecone, your chunking strategy (768 tokens with 120 overlap using SentenceSplitter), embedding model selection (text-embedding-3-small for cost/quality balance)
# - Retrieval evaluation approach: how you set up eval using ROUGE-L and LLM-as-judge for assessing answer quality
# - Router design: technical vs nontechnical namespace filtering based on query classification
# - Key lessons learned: what worked well (personality_ns filtering reduced noise significantly), what you'd change next time (would invest more in eval dataset quality early)
# - Specific technical details that demonstrate your depth (e.g., metadata payload structure, vector similarity thresholds, handling out-of-scope queries)

# Be specific about the technologies, metrics, and reasoning. Show your structured thinking and tradeoff analysis."""
#     },
#     {
#         "doc_title": "Transformer Model Implementation for Conditional Generation",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write a first-person deep dive into implementing a transformer model for conditional text generation. Cover:

# - Your understanding of autoregressive transformer architecture (self-attention, positional encoding, decoder-only vs encoder-decoder)
# - The specific generation task you worked on and why transformers were the right fit
# - Implementation challenges you faced (memory constraints during training, attention mask construction, handling variable-length sequences)
# - How you approached conditional generation (prompt engineering, control codes, fine-tuning strategy)
# - Evaluation metrics you used and what they revealed about model behavior
# - What you learned about the gap between transformer theory and production implementation

# Reference your ML background (NLP models, deep learning) and show your research-to-production translation mindset. Be concrete about architectural choices and their rationale."""
#     },
#     {
#         "doc_title": "PSPNet Implementation for Semantic Segmentation",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write about your experience implementing PSPNet (Pyramid Scene Parsing Network) for semantic segmentation. Cover:

# - The segmentation task context and dataset characteristics
# - Why you chose PSPNet specifically (pyramid pooling module for capturing context at multiple scales)
# - Implementation details: backbone architecture (ResNet), pooling pyramid structure, upsampling strategy
# - Training challenges (class imbalance, memory constraints with high-resolution images, augmentation strategy)
# - How you evaluated segmentation quality (IoU, pixel accuracy, per-class performance)
# - Specific results and what they taught you about the model's strengths and failure modes
# - What you'd do differently in a production deployment

# Show your computer vision depth and your ability to move from research papers to working implementations."""
#     },
#     {
#         "doc_title": "Multimodal Deep Learning: Speech Emotion Recognition and Fake News Detection",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write about your work on multimodal deep learning systems, specifically hierarchical speech emotion recognition and multimodal fake news detection (SEMI-FND). Cover:

# - The challenge of combining modalities (audio, text, visual features) and why multimodal approaches outperform unimodal ones
# - Architecture design for fusion: early fusion vs late fusion vs hierarchical approaches
# - For speech emotion recognition: how you handled temporal hierarchies (frame-level → utterance-level features), acoustic feature extraction, emotion label ambiguity
# - For fake news detection: combining text semantics with user engagement patterns and source credibility signals
# - Technical challenges in aligning modalities (different sampling rates, feature dimensionality mismatches)
# - Evaluation approach and what metrics revealed about which modalities contributed most
# - Lessons about when multimodal complexity is worth the engineering effort

# Demonstrate your understanding of multimodal systems and deep learning fundamentals."""
#     },
#     {
#         "doc_title": "LLM Agent Orchestration System with Tool Calling",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write a first-person account of building an LLM agent orchestration system with reliable tool calling. Cover:

# - The agent use case and why tool calling was necessary (e.g., accessing external APIs, databases, computation tools)
# - Framework choices (LangChain, custom orchestration, function calling APIs) and their tradeoffs
# - How you designed the tool registry and tool schemas for reliable execution
# - Reliability challenges: hallucinated tool calls, malformed arguments, infinite loops, error recovery
# - Decision trace analysis: how you logged and evaluated agent reasoning chains
# - Evaluation strategy: LLM-as-judge for assessing tool selection appropriateness, unit tests for tool execution correctness
# - Specific failure modes you encountered and how you mitigated them (retries vs guardrails tradeoff)
# - Production considerations: latency, cost, observability

# Show your ML systems design thinking and agent reliability measurement expertise."""
#     },
    
#     {
#         "doc_title": "Model Quantization for On-Device Inference",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write about your experience with model quantization for on-device deployment. Cover:

# - The deployment context (mobile, edge device) and constraints (memory, latency, power)
# - Quantization techniques you explored (post-training quantization, quantization-aware training, INT8 vs FP16)
# - The specific model you quantized and baseline performance characteristics
# - Latency vs accuracy tradeoffs you measured and how you made the tradeoff decision
# - Implementation details (quantization libraries, calibration dataset selection, per-layer vs per-tensor quantization)
# - Evaluation: how you measured on-device performance, what metrics mattered most
# - Surprising learnings (e.g., certain layer types more sensitive to quantization, batch norm folding impact)
# - When quantization is worth the complexity vs when to optimize architecture instead

# Demonstrate your on-device inference optimization knowledge and tradeoff reasoning."""
#     },
#     {
#         "doc_title": "Risk Appetite Modeling System for Financial Governance",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write about designing a risk appetite modeling system for a financial institution. Cover:

# - The governance context and why risk appetite frameworks matter (regulatory compliance, board-level decision making)
# - Data modeling approach: entity-relationship design (PK/FK structure), how you represented risk metrics, thresholds, and organizational hierarchy
# - UML diagrams you created to communicate the model to stakeholders
# - Schema design decisions: normalization choices, handling temporal data (risk tolerance changes over time), audit trail requirements
# - Integration challenges: connecting risk data from multiple source systems, data quality issues
# - How you balanced flexibility (configurable risk metrics) with structure (governance requirements)
# - Lessons learned about translating qualitative risk statements into quantitative data models

# Show your data modeling expertise and ability to work in regulated domains."""
#     },
#     {
#         "doc_title": "Evaluation Pipeline for LLM Agent Systems",
#         "personality_ns": "technical",
#         "content_type": "project_writeup",
#         "prompt": """Write about building a comprehensive evaluation pipeline for LLM agent systems. Cover:

# - Why evaluating agents is harder than evaluating traditional ML models (stochasticity, multi-turn interactions, tool use)
# - Your evaluation framework design: metrics (ROUGE for text quality, decision trace correctness, tool call success rate, end-to-end task completion)
# - LLM-as-judge setup: prompt engineering for the judge LLM, calibration against human ratings, handling judge disagreements
# - Evaluation dataset creation: how you built a diverse test set, balancing coverage vs effort
# - Reliability measurement: retry strategies, consistency across runs, failure mode categorization
# - How you automated the eval pipeline and tracked metric regressions over time
# - Specific insights from running evals: which failure modes were most common, surprising model behaviors
# - Tradeoffs between eval rigor and iteration speed

# Demonstrate your ML systems design and evaluation expertise."""
#     },

#     # Technical Explainers (6 docs)
#     {
#         "doc_title": "How I Think About Retrieval Evaluation Metrics",
#         "personality_ns": "technical",
#         "content_type": "technical_explainer",
#         "prompt": """Explain your mental framework for evaluating retrieval quality in RAG systems. Cover:

# - Why retrieval evaluation matters (garbage in, garbage out for generation)
# - Metrics you use: recall@k (did we retrieve the right docs?), ROUGE-L (does the answer match reference?), LLM-as-judge (is the answer actually helpful?)
# - When to use which metric: offline eval vs online monitoring
# - Common failure modes in retrieval (out-of-scope queries, ambiguous intent, poor chunking) and how metrics help you catch them
# - Concrete examples from your RAG pipeline work (e.g., "We noticed recall@5 was 0.8 but answer quality was poor — turned out chunk boundaries were cutting off critical context")
# - How you iterate: metrics → error analysis → retrieval improvements → re-eval
# - What metrics DON'T tell you and why human eval still matters

# Use your structured explanation style with clear reasoning and example-driven insights."""
#     },
#     {
#         "doc_title": "My Approach to Data Modeling",
#         "personality_ns": "technical",
#         "content_type": "technical_explainer",
#         "prompt": """Explain your mental model for data modeling (relational schemas, UML diagrams). Cover:

# - Core principles: normalization vs denormalization tradeoffs, when to use which
# - How you think about primary keys and foreign keys: entity identity, referential integrity
# - Your process: start with entities and relationships, iterate with stakeholders, formalize in UML
# - Practical heuristics (e.g., "If you're repeating the same data in multiple places, you probably need a junction table")
# - How you handle temporal data (e.g., tracking changes over time, audit trails)
# - Common mistakes you've seen or made (over-normalization leading to query complexity, under-normalization causing update anomalies)
# - Real example from your risk appetite modeling work or other projects
# - How you communicate data models to non-technical stakeholders

# Show your systems engineering depth and structured thinking."""
#     },
    
#     {
#         "doc_title": "Concurrency and Locking in Distributed Systems",
#         "personality_ns": "technical",
#         "content_type": "technical_explainer",
#         "prompt": """Explain how you reason about concurrency, race conditions, and locking mechanisms. Cover:

# - Your mental model for concurrent access: what can go wrong (lost updates, dirty reads, deadlocks)
# - Locking strategies: pessimistic (locks) vs optimistic (version checks), when to use which
# - Distributed systems complications: network partitions, clock skew, consensus requirements
# - Concrete example of a race condition you've debugged or prevented
# - How you think about atomicity and isolation in the context of database transactions
# - Tradeoffs between correctness (strong consistency) and performance (eventual consistency)
# - Practical approaches: how you test for concurrency bugs, what tools/patterns you use

# Demonstrate your distributed systems fundamentals and concurrency reasoning."""
#     },
#     {
#         "doc_title": "REST API Design Principles I Follow",
#         "personality_ns": "technical",
#         "content_type": "technical_explainer",
#         "prompt": """Explain your REST API design philosophy and conventions. Cover:

# - Core REST principles you care about: resource-oriented URLs, proper HTTP methods (GET/POST/PUT/DELETE), statelessness
# - How you structure endpoints (e.g., /users/:id/orders vs /orders?user_id=:id) and when to nest vs query
# - Versioning strategy (URL path versioning vs header versioning) and why it matters
# - Error handling: status codes you use, error response format, how much detail to expose
# - Pagination, filtering, sorting conventions
# - Authentication/authorization patterns (bearer tokens, API keys)
# - What you've learned from maintaining APIs over time (backwards compatibility is hard, explicit > implicit)
# - Real example from a system you've built

# Show your API design depth and practical experience."""
#     },
#     {
#         "doc_title": "Observability in Production ML Systems",
#         "personality_ns": "technical",
#         "content_type": "technical_explainer",
#         "prompt": """Explain your philosophy on observability for ML systems in production. Cover:

# - Why observability is different for ML systems (model drift, data distribution shifts, not just uptime)
# - The three pillars: logging, metrics, alerting — what you instrument and why
# - ML-specific metrics you track (latency, prediction distribution, feature drift, model confidence scores)
# - How you structure logs for debuggability (structured JSON, request IDs, trace context)
# - Alerting strategy: what's worth paging someone for vs what's just FYI
# - Concrete example: a production issue you debugged using logs/metrics, what you learned
# - Tradeoffs: observability overhead (cost, latency) vs debugging speed
# - How observability influences system design (e.g., building for debuggability)

# Demonstrate your ML systems and production engineering mindset."""
#     },
         
# {
#     "doc_title": "Research-to-Production Translation: Bridging the Gap",
#     "personality_ns": "technical",
#     "content_type": "technical_explainer",
# "prompt": """Explain how you think about moving ML models from research to production. Cover:

# - The gap: research code optimizes for experimentation, production code optimizes for reliability and maintainability
# - Common challenges: reproducibility, dependency management, data pipeline brittleness, latency requirements
# - Your approach: what stays from research (core model architecture, hyperparameters), what changes (inference optimization, error handling, monitoring)
# - Concrete example from your experience (e.g., PSPNet, transformer models, RAG pipeline)
# - How you balance iteration speed (research mindset) with correctness (production mindset)
# - Productionization checklist you mentally run through: error handling, logging, versioning, rollback strategy
# - When to rebuild vs refactor research code
# - Lessons learned from projects that went smoothly vs messily

# Show your research-to-production translation expertise and systems thinking."""
#     },

#     # Work Experience (3 docs)
#     {
#         "doc_title": "Work Experience: ML Engineer Role",
#         "personality_ns": "technical",
#         "content_type": "work_experience",
#         "prompt": """Write a narrative-style resume description of your ML engineering work. Cover:

# - The role context: team size, problem domain, scope of responsibility
# - Specific systems you built or contributed to (RAG pipeline, transformer models, evaluation frameworks)
# - Technical scope: architecture design, implementation, evaluation, productionization
# - Impact metrics where applicable (latency improvements, accuracy gains, user adoption)
# - Cross-functional collaboration: how you worked with data scientists, product managers, infrastructure teams
# - Technical challenges you solved and how (retrieval quality, model reliability, evaluation rigor)
# - What you learned from this role about ML systems, production engineering, or collaboration
# - Technologies/tools you used extensively

# Write in first person with concrete details, showing ownership and technical depth."""
#     },
    
    
#     {
#         "doc_title": "Work Experience: Systems Engineering and Distributed Systems",
#         "personality_ns": "technical",
#         "content_type": "work_experience",
#         "prompt": """Write about your experience with systems engineering, microservices, and distributed systems. Cover:

# - The systems context: what you built, scale/complexity, architectural patterns
# - Microservices work: service decomposition, inter-service communication (REST, message queues), distributed tracing
# - Data modeling responsibilities: schema design, database selection, query optimization
# - Distributed systems challenges you tackled (concurrency, consistency, fault tolerance)
# - Observability and reliability work: logging, metrics, alerting, incident response
# - Collaboration with other teams: how you interfaced with frontend, data, infrastructure teams
# - Specific technical decisions you made and their outcomes
# - Growth areas: what this role taught you about system design and production engineering

# Use structured narrative style with concrete examples and measurable outcomes."""
#     },
#     {
#         "doc_title": "Work Experience: Computer Vision Research and ML",
#         "personality_ns": "technical",
#         "content_type": "work_experience",
#         "prompt": """Write about your research and project work in computer vision and machine learning. Cover:

# - Research context: academic projects, personal projects, or research assistant roles
# - Specific CV work: semantic segmentation (PSPNet), diffusion models (DDPM), conditional generation
# - Multimodal projects: speech emotion recognition, fake news detection
# - Your role: implementation, experimentation, evaluation, paper reading and reproduction
# - Technical skills developed: PyTorch/TensorFlow, dataset handling, training pipelines, hyperparameter tuning
# - Evaluation approaches: metrics you used, how you validated model performance, ablation studies
# - What you learned about the research-to-implementation gap
# - How this work shaped your understanding of ML systems

# Write with technical depth showing your hands-on ML experience."""
#     },

#     # Design Decisions (4 docs)
#     {
#         "doc_title": "Why I Chose Qdrant Over Pinecone for the RAG Pipeline",
#         "personality_ns": "technical",
#         "content_type": "design_decision",
#         "prompt": """Write a structured analysis of why you chose Qdrant over Pinecone for your vector database. Cover:

# - The decision context: RAG pipeline for investment banking docs, requirements (filtered search by namespace, metadata filtering, cost constraints)
# - Qdrant advantages: flexible filtering (personality_ns, content_type), self-hosted option for cost control, good Python SDK, transparent query semantics
# - Pinecone tradeoffs: managed service simplicity vs cost at scale, metadata filtering capabilities
# - Specific features that mattered: filtered vector search, payload retrieval, query performance
# - Cost analysis if applicable (managed vs self-hosted economics)
# - What you'd reconsider if requirements changed (e.g., massive scale might favor managed service)
# - Lessons learned after running this in production

# Use your explicit tradeoff reasoning style with concrete technical details."""
#     },
#     {
#         "doc_title": "Embedding Model Selection for RAG: Balancing Cost and Quality",
#         "personality_ns": "technical",
#         "content_type": "design_decision",
#         "prompt": """Explain your decision process for choosing text-embedding-3-small for your RAG pipeline. Cover:

# - Models you evaluated: text-embedding-3-small vs text-embedding-3-large vs text-embedding-ada-002, alternatives like sentence-transformers
# - Evaluation criteria: retrieval quality (recall@k), cost per query, latency, embedding dimension (storage cost)
# - How you measured quality: held-out query set, ROUGE scores, manual evaluation
# - Cost-quality tradeoff: text-embedding-3-small (1536 dim, cheaper) was "good enough" vs text-embedding-3-large (3072 dim, better but pricier)
# - Latency considerations: embedding generation time, vector search speed with different dimensions
# - What you'd change if requirements shifted (higher quality needs, budget constraints, scale)
# - Lessons about premature optimization (when to start with a cheap model vs invest in quality upfront)

# Show analytical decision-making with quantitative backing."""
#     },
#     {
#         "doc_title": "Chunking Strategy Tradeoffs: Sentence vs Fixed-Size vs Semantic",
#         "personality_ns": "technical",
#         "content_type": "design_decision",
#         "prompt": """Explain your chunking strategy decision for RAG document processing. Cover:

# - Chunking approaches you considered: sentence-based (SentenceSplitter), fixed-size (token count), semantic (topic-based)
# - Why you chose SentenceSplitter with 768 tokens and 120 overlap for your pipeline
# - Tradeoffs: sentence boundaries preserve semantic coherence, fixed overlap ensures context continuity, token limit fits embedding model constraints
# - Failure modes of each approach: fixed-size can break mid-sentence, sentence-only can create tiny/huge chunks, semantic chunking is expensive
# - How you validated the choice: retrieval quality on test queries, chunk size distribution analysis
# - What you learned about chunk size impact on retrieval (too small = no context, too large = irrelevant content dilutes the match)
# - When you'd reconsider (different document types, different query patterns)

# Use structured tradeoff analysis with specific examples."""
#     },
    
    
#     {
#         "doc_title": "Agent Reliability: Retries vs Guardrails",
#         "personality_ns": "technical",
#         "content_type": "design_decision",
#         "prompt": """Explain your architectural approach to LLM agent reliability. Cover:

# - The reliability problem: agents can hallucinate tool calls, generate malformed inputs, loop infinitely
# - Two strategies: retries (regenerate on failure, give LLM another chance) vs guardrails (validate before execution, reject bad calls)
# - When you use retries: transient errors, ambiguous but recoverable failures, when you trust the LLM to self-correct
# - When you use guardrails: safety-critical operations, structured output requirements, deterministic validation possible
# - Hybrid approach: guardrails for validation, retries for recovery
# - Concrete example from your agent orchestration work
# - Tradeoffs: retries add latency and cost, guardrails require upfront engineering
# - Lessons learned: what failure modes each strategy handles well, when to give up vs keep retrying

# Show systems design thinking and reliability engineering depth."""
#     },

#     # Interview Q&A (3 docs)
#     {
#         "doc_title": "Interview Question: Tell Me About a Complex System You Built",
#         "personality_ns": "technical",
#         "content_type": "interview_qa",
#         "prompt": """Write a structured STAR-format response to "Tell me about a complex system you built." Use your RAG pipeline or agent orchestration work. Cover:

# - Situation: the business context, problem to solve, stakeholders involved
# - Task: your specific responsibility and scope (architecture design, implementation, evaluation)
# - Action: what you did step-by-step (design decisions, technologies chosen, challenges encountered and how you addressed them)
# - Result: measurable outcomes (performance metrics, user adoption, lessons learned)

# Be concrete with technical details: specific technologies, metrics, tradeoffs you made. Show ownership, structured thinking, and ability to deliver complex systems. Mention collaboration with other teams if applicable.

# Write in first person as if answering in an interview, balancing technical depth with clarity."""
#     },
#     {
#         "doc_title": "Interview Question: How Do You Evaluate ML Systems?",
#         "personality_ns": "technical",
#         "content_type": "interview_qa",
#         "prompt": """Write your response to "How do you evaluate ML systems?" Cover:

# - Your evaluation philosophy: metrics matter, but you need the right metrics for the problem
# - Different system types need different approaches: classification (accuracy, precision/recall, F1), retrieval (recall@k, ROUGE), generation (ROUGE, BLEU, LLM-as-judge), agents (task completion, tool call correctness)
# - Offline vs online evaluation: held-out test sets vs production monitoring
# - Concrete example from your work: RAG pipeline evaluation (retrieval quality + generation quality), agent evaluation (decision trace analysis)
# - How you iterate: metrics → error analysis → improvements → re-eval
# - What metrics don't capture: user satisfaction, edge case coverage, production drift
# - Lessons learned: premature metric optimization, importance of diverse eval sets

# Show your ML systems design expertise and evaluation rigor."""
#     },
#     {
#         "doc_title": "Interview Question: Describe a Technical Disagreement",
#         "personality_ns": "technical",
#         "content_type": "interview_qa",
#         "prompt": """Write a STAR response to "Describe a time you had a technical disagreement and how you resolved it." Ground this in your traits (intellectual honesty, structured reasoning, high ownership). Cover:

# - Situation: the technical context, team involved, what you disagreed about (e.g., architecture decision, evaluation approach, technology choice)
# - Task: your position and the other person's position, why it mattered
# - Action: how you approached the disagreement (gathered data, ran experiments, structured the tradeoff analysis, communicated your reasoning clearly, listened to counterarguments)
# - Result: how the disagreement resolved (consensus, experiment-driven decision, compromise), what the outcome was, what you learned

# Show intellectual honesty (admitting uncertainty, changing your mind based on evidence), structured communication, and collaborative problem-solving. Make it specific and authentic to your style.

# Write in first person as if in an interview."""
#     },

#     # ────────────────────────────────────────────────────────────────────────────
#     # NONTECHNICAL (15 documents)
#     # ────────────────────────────────────────────────────────────────────────────

#     # Personal Reflections (4 docs)
#     {
#         "doc_title": "What Drives Me: Competence and Mastery",
#         "personality_ns": "nontechnical",
#         "content_type": "personal_reflection",
#         "prompt": """Write a reflective piece on what drives you, centered on competence and mastery. Cover:

# - Why competence matters to you: the satisfaction of understanding something deeply, being good at what you do, earning professional respect
# - How mastery shows up in your work: iterative refinement, not settling for surface-level understanding, pushing to understand failure modes
# - Connection to your technical work (ML systems, evaluation rigor) and nontechnical pursuits (debate, dance — both reward deliberate practice)
# - The tension: high internal standards are motivating but can create pressure
# - How you think about growth: competence isn't fixed, you can build it through structured effort
# - What "good enough" means to you and when to stop refining
# - Examples of pursuing mastery (learning a new technical domain, perfecting a dance routine, debugging a complex system)

# Write in your introspective, structured style with honest self-reflection."""
#     },
    
#     {
#         "doc_title": "Growth Edges I'm Working On",
#         "personality_ns": "nontechnical",
#         "content_type": "personal_reflection",
#         "prompt": """Write about the growth edges you're actively working on (from your traits: asking for help earlier, navigating career ambiguity, managing emotional response under uncertainty). Cover:

# - Asking for help earlier: why it's hard (high ownership, wanting to figure things out yourself), when it's cost you time, what you're trying instead (setting a time limit, recognizing when you're stuck)
# - Navigating career ambiguity: the discomfort with unclear paths, how you're building tolerance (structured reflection, experimenting with less-defined projects, asking for mentorship)
# - Managing emotional response under uncertainty: stress triggers (lack of structure, unclear evaluation criteria), what you're learning about yourself, strategies you're trying
# - Why these matter: growth requires confronting uncomfortable areas
# - Progress and setbacks: small wins, when you backslide, what helps

# Be honest and specific. Show active self-reflection and growth orientation."""
#     },
#     {
#         "doc_title": "Confidence vs Uncertainty: The Motivational Tension",
#         "personality_ns": "nontechnical",
#         "content_type": "personal_reflection",
#         "prompt": """Write about the tension between technical confidence and career uncertainty (from traits: "Strong technical self-belief paired with anxiety around long-term trajectory"). Cover:

# - Technical confidence: you know you're good at what you do (ML systems, architecture design, evaluation rigor), and that confidence is grounded in results
# - Career uncertainty: what comes next is less clear (which path to take, what trade-offs to make, how to evaluate options)
# - Why the contrast exists: technical competence is measurable, career trajectory is ambiguous
# - How this tension shows up: confidence in execution, anxiety about direction
# - What you're learning: structure helps with uncertainty (frameworks for career decisions, mentorship, experimentation)
# - How you're navigating: leaning into strengths while building comfort with ambiguity
# - What this teaches you about yourself: clarity and measurable progress are core to your motivation

# Write introspectively with honest self-awareness."""
#     },
#     {
#         "doc_title": "My Relationship With High Standards",
#         "personality_ns": "nontechnical",
#         "content_type": "personal_reflection",
#         "prompt": """Reflect on your high internal standards (from traits: "internal_standards: very high"). Cover:

# - Where high standards show up: code quality, system design, evaluation rigor, writing clarity, even dance performance
# - Why you care: quality work matters, it's how you respect yourself and others, it reflects competence
# - The upside: produces excellent outcomes, drives continuous improvement, earns credibility
# - The cost: perfectionism can slow you down, hard to declare something "done", can be exhausting
# - When to relax standards: iteration speed matters, "good enough" is context-dependent, not everything needs polish
# - How you're learning to calibrate: asking "what's the goal?" before refining, time-boxing polish work
# - Self-reflection: are these standards yours or imposed? How do they serve you?
# - Examples of navigating this (shipping a prototype vs polishing a production system)

# Write thoughtfully with nuanced self-awareness."""
#     },

#     # Interest Essays (5 docs)
#     {
#         "doc_title": "Why I Do Competitive Debate",
#         "personality_ns": "nontechnical",
#         "content_type": "interest_essay",
#         "prompt": """Write about your experience with competitive debate (MUN, parliamentary formats, DebSoc at NSUT). Cover:

# - What drew you to debate: structured argumentation, research synthesis, intellectual rigor
# - What you've learned: building arguments under pressure, anticipating counterarguments, clarity of communication, committee strategy
# - Specific experiences: AMIMUN'19, KMCMUN'19 (Special Mention), Thursday debate sessions, hosting Colloquium'19
# - Skills it developed: structured reasoning, position paper writing, identifying operational gaps, mentoring first-time debaters
# - How it shapes your thinking now: clearer reasoning, explicit tradeoff analysis, comfort with intellectual combat
# - Why you stayed involved: the challenge, continuous improvement, community
# - Connection to your identity: depth-seeking, analytical, enjoys structured frameworks

# Write in your thoughtful style with specific examples."""
#     },
#     {
#         "doc_title": "Dance: Discipline, Expression, and Performance",
#         "personality_ns": "nontechnical",
#         "content_type": "interest_essay",
#         "prompt": """Write about what dance means to you (contemporary, jazz, ballet; Capella at NSUT, Mélange production). Cover:

# - What you love about dance: physical expression, precision and elegance, storytelling through movement
# - Your dance background: core performing member at Capella (2018-2022), logistics lead, Mélange 2019-20 (thematic piece on racial discrimination)
# - Technical strengths: fast routine acquisition, movement precision, performing under pressure (IIT, IIM, DU circuit)
# - The discipline: long practice cycles, maintaining energy and enthusiasm, balancing performance and logistics roles
# - Mentoring juniors: what you've learned from teaching others
# - Why it's different from technical work: physical vs intellectual challenge, but both reward deliberate practice
# - How it connects to your identity: high standards, competence-driven, team collaboration
# - What dance has taught you about yourself

# Write with thoughtful reflection and specific experiences."""
#     },
    
#     {
#         "doc_title": "Books That Changed How I Think",
#         "personality_ns": "nontechnical",
#         "content_type": "interest_essay",
#         "prompt": """Write about your reading habits and books that have shaped your thinking. Cover:

# - What kinds of books you're drawn to: depth over breadth, interdisciplinary topics, systems thinking, sustainability, policy-tech intersections
# - Specific books that left an impact and why (be concrete about what changed in your thinking)
# - How reading fits into your intellectual life: building mental models, exploring outside your domain, structured learning
# - Connection to your interests: UN SDGs (Goals 9, 13, 16), echotechnology, institutional frameworks, sustainability
# - What you look for in a book: rigorous arguments, actionable insights, clarity of explanation
# - How books influence your work: new frameworks, different perspectives, cross-domain inspiration
# - Reading as a growth practice: intentional learning, reflection after finishing

# Be specific about books and ideas, not generic. Show your intellectual orientation."""
#     },
#     {
#         "doc_title": "Easy Healthy Recipes Every Busy Student Should Know",
#         "personality_ns": "nontechnical",
#         "content_type": "interest_essay",
#         "prompt": """Write about cooking for busy students: healthy, tasty, practical meals. Cover:

# - Why cooking matters: health, cost, autonomy, creativity
# - Your approach: simple recipes with few ingredients, minimal equipment, high taste-to-effort ratio
# - Specific recipes you recommend: breakfast (overnight oats, egg scrambles), lunch/dinner (one-pot meals, stir-fries, sheet pan dinners), snacks
# - Practical tips: batch cooking, ingredient versatility (one vegetable, multiple uses), pantry staples
# - How you think about nutrition: balanced meals, enough protein, vegetables, not obsessing over perfection
# - Constraints you optimize for: time (15-30 min), budget, dorm/limited kitchen equipment
# - Why you care: taking care of yourself, discipline, small everyday competence
# - Connection to your values: structured approach, practical optimization, self-sufficiency

# Write helpfully and concretely with actionable advice."""
#     },
#     {
#         "doc_title": "What I've Learned from Strength Training",
#         "personality_ns": "nontechnical",
#         "content_type": "interest_essay",
#         "prompt": """Write about your experience with strength training (Push-Pull-Legs program). Cover:

# - Why you started: physical health, discipline, measurable progress
# - Your program: PPL split, progressive overload, consistency over intensity
# - What you've learned: patience (strength builds slowly), importance of recovery, technique > ego lifting
# - Parallels to other pursuits: deliberate practice, incremental improvement, tracking progress (like ML model training, dance practice)
# - Challenges: staying consistent, managing fatigue, avoiding injury, balancing with other commitments
# - How it connects to your identity: competence-driven, measurable improvement, structured approach
# - Mental benefits: stress management, clear goals, sense of control
# - Lessons that transfer: discipline, long-term thinking, respecting the process

# Write reflectively with specific insights."""
#     },

#     # Opinion Pieces (3 docs)
#     {
#         "doc_title": "On Intellectual Honesty",
#         "personality_ns": "nontechnical",
#         "content_type": "opinion_piece",
#         "prompt": """Write about why intellectual honesty matters to you (core value from traits). Cover:

# - What you mean by intellectual honesty: admitting uncertainty, changing your mind based on evidence, not pretending to know things you don't
# - Why it matters: foundational to good thinking, earns trust, prevents bad decisions
# - Where you practice it: technical work (evaluation rigor, acknowledging model limitations), debate (steelmanning opponents), personal growth (honest self-assessment)
# - Challenges: social pressure to appear certain, ego investment in being right, discomfort with saying "I don't know"
# - Examples of intellectual honesty in action (admitting a design decision was wrong, changing your approach based on data, acknowledging gaps in your knowledge)
# - What happens when it's missing: hype-driven tech culture, surface-level thinking, fragile systems built on assumptions
# - How you cultivate it: structured reflection, seeking disagreement, valuing correctness over being right

# Write thoughtfully with conviction and examples."""
#     },
#     {
#         "doc_title": "The Problem With Hype in Tech",
#         "personality_ns": "nontechnical",
#         "content_type": "opinion_piece",
#         "prompt": """Write about your frustration with hype-driven tech culture (from style avoidances: "hype-driven explanations"). Cover:

# - What you mean by hype: surface-level enthusiasm, overselling capabilities, ignoring tradeoffs, "this will change everything" rhetoric
# - Why it bothers you: obscures real understanding, leads to poor decisions, devalues depth and rigor
# - Examples: AI hype cycles, overpromised product launches, "revolutionary" claims for incremental improvements
# - The cost of hype: misallocated resources, disillusionment when reality doesn't match promises, erosion of trust
# - What's missing: honest tradeoff analysis, acknowledgment of limitations, clarity about when a technology actually fits
# - How you think instead: depth over breadth, explicit tradeoffs, grounded evaluation
# - When excitement is warranted: genuine breakthroughs backed by evidence, not marketing
# - What you value: technical rigor, intellectual honesty, thoughtful skepticism

# Write with conviction but avoid being preachy. Be specific with examples."""
#     },
    
{
        "doc_title": "Navigating Career Ambiguity with Structured Thinking",
        "personality_ns": "nontechnical",
        "content_type": "opinion_piece",
        "prompt": """Write about how you approach career ambiguity using structured frameworks (growth edge + strength). Cover:

- The problem: career paths are messy, options are unclear, evaluation criteria are subjective
- Your discomfort with ambiguity: you prefer structure, measurable progress, clear goals (stress triggers: lack of structure, unclear evaluation)
- Structured approaches that help: decision frameworks (pros/cons, tradeoff matrices), informational interviews, experimentation (try things, gather data), mentorship
- How you're building tolerance for ambiguity: recognizing it's inherent to career decisions, practicing comfort with uncertainty
- What you've learned: perfect information is impossible, you can structure the unstructured, action reduces ambiguity
- Balancing analysis and action: when to think more vs when to just try something
- Examples of navigating this: choosing between roles, evaluating career paths, making tradeoffs
- What helps: frameworks, data, talking to people, small experiments

Write thoughtfully with practical advice grounded in your experience."""
    },

    # Life Experiences (3 docs)
    {
        "doc_title": "A Formative Team Experience: Leading Capella's Annual Production",
        "personality_ns": "nontechnical",
        "content_type": "life_experience",
        "prompt": """Write about co-managing Capella's annual production (from skills: performing + logistics lead). Cover:

- The context: annual dance production, performing member + operational lead, constrained budget and timeline, team structure (performers vs infra)
- Your dual role: dancing in the production while handling attendance, logistics, infra coordination, mentoring juniors
- Specific challenges: injury substitutions, exam schedule clashes, costume delays, funding strategy (alumni, sponsorships, competition winnings)
- A hard decision you made: cutting choreographer cost in 2021-22 when competition certainty was low (explicit tradeoff reasoning under resource pressure)
- What you learned about collaboration: multi-role context switching, team structure design, roadblock navigation
- What you learned about yourself: high ownership, constrained project execution, balancing performance quality and operational needs
- Formative lessons: how to lead while also performing, how to make hard tradeoffs, importance of clear communication

Write narratively with specific stories and reflection on what it taught you."""
    },
    {
        "doc_title": "Learning to Ask for Help: A Growth Edge in Action",
        "personality_ns": "nontechnical",
        "content_type": "life_experience",
        "prompt": """Write about a specific experience where you struggled to ask for help and what you learned. Cover:

- The situation: a problem you were stuck on (technical bug, project challenge, personal struggle)
- Why you didn't ask: high ownership, wanting to figure it out yourself, not wanting to appear incompetent
- The cost: time wasted, stress, worse outcome than if you'd asked earlier
- The turning point: what finally made you ask (hit a deadline, someone offered, you recognized you were stuck)
- What happened when you did ask: faster resolution, learned something new, realized people were willing to help
- What you learned: asking for help is a skill, not a weakness; it's about knowing when you're stuck, not giving up
- How you're practicing this now: setting time limits, recognizing patterns of being stuck, proactively reaching out
- Why it's still hard: the growth edge isn't "fixed", it's a practice

Write honestly and specifically with vulnerable reflection."""
    },
    {
        "doc_title": "A Moment That Tested My Resilience",
        "personality_ns": "nontechnical",
        "content_type": "life_experience",
        "prompt": """Write about a challenging experience that tested your resilience (use stress triggers: career ambiguity, lack of structure, unclear evaluation). Cover:

- The situation: what was happening (high-pressure project, uncertain career moment, difficult team dynamic)
- Why it was hard for you specifically: hit your stress triggers (ambiguity, unclear expectations, lack of control)
- How you responded initially: emotional reaction (anxiety, frustration), what you tried first
- What you did to navigate it: structured problem-solving, seeking support, breaking the problem into pieces, managing your emotional response
- What helped: frameworks, mentorship, self-reflection, action
- The outcome: how it resolved, what you learned about yourself
- Resilience lessons: how you bounce back, what strategies work for you, building tolerance for discomfort
- How it changed you: new perspectives, capabilities, self-awareness

Write with honest emotion and reflection. Show growth and self-awareness."""
    },
]


def generate_document(client, spec, persona_block):
    """Generate a single document using GPT-4o-mini."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
        temperature=0.7,  # Balanced creativity for natural variation
        messages=[
            {"role": "system", "content": persona_block},
            {"role": "user", "content": spec["prompt"]},
        ],
    )
    return {
        "doc_title": spec["doc_title"],
        "source_url": spec.get("source_url", ""),
        "personality_ns": spec["personality_ns"],
        "content_type": spec["content_type"],
        "body": response.choices[0].message.content.strip(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic documents for digital twin"
    )
    parser.add_argument(
        "--output-dir",
        default="data/sources",
        help="Directory to save generated documents",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load persona context
    persona_block = load_persona_context()

    # Initialize OpenAI client (uses OPENAI_API_KEY env var)
    client = OpenAI(api_key=OPENAI_API_KEY)


    print(f"Synthetic Data Generation")
    print(f"Output directory: {output_dir}")
    print(f"Total documents: {len(DOCUMENT_SPECS)}")


    # Generate each document
    count = 0
    for i, spec in enumerate(DOCUMENT_SPECS):
        print(f"[{i+1}/{len(DOCUMENT_SPECS)}] Generating: {spec['doc_title']}")
        try:
            if (count == 5):
                break
            
            doc = generate_document(client, spec, persona_block)

            # Create filename: {namespace}_{content_type}_{index}.json
            filename = f"{spec['personality_ns']}_{spec['content_type']}_{spec['doc_title']}.json"
            filepath = output_dir / filename

            # Save document
            filepath.write_text(json.dumps(doc, indent=2))
            print(f"  ✓ Saved: {filename}")
            count+=1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    print(f"Generation complete! {len(DOCUMENT_SPECS)} documents saved to {output_dir}")


if __name__ == "__main__":
    main()
