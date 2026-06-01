# Medical Compliance RAG System

A Retrieval-Augmented Generation system for answering healthcare compliance questions, grounded in official OSHA, HIPAA, and CDC documents.

---

## Status

| Component | Status |
|---|---|
| Package structure (`src/medcomply/`) | Implemented |
| Dependency management (`uv` + `pyproject.toml`) | Implemented |
| Linting (`ruff`) | Implemented |
| Test suite (`pytest`) | Implemented |
| Vector store (Qdrant) | Not present — ChromaDB used currently |
| Dense embeddings (`BAAI/bge-base-en-v1.5`) | Not present — `nomic-embed-text` used currently |
| Sparse retrieval / hybrid search (BM25 via `fastembed`) | Not present |
| Reranker (`BAAI/bge-reranker-v2-m3`) | Not present |
| Orchestration (LlamaIndex) | Not present |
| Auth (`streamlit-authenticator`) | Not present — simulated user list |
| Audit logging (SQLite + UUID) | Partial — flat-file JSON, no UUID constraint |
| Evaluation (RAGAS + retrieval metrics) | Implemented — Hit Rate / MRR / nDCG + RAGAS generation metrics |
| Skill-gap analysis | Implemented — semantic similarity scoring (cosine distance over `bge-base-en-v1.5` embeddings) with KMeans cohort theme detection |
| Local LLM (Ollama) | Implemented |
| Streamlit frontend | Implemented |

---

## Technical Stack

| Concern | Decision |
|---|---|
| Dependency management | `uv` + `pyproject.toml` + `uv.lock` |
| Linting / formatting | `ruff` |
| Testing | `pytest` + `pytest-cov` |
| Data models | `pydantic` v2 |
| Vector DB | Qdrant (native hybrid search, payload filtering for RBAC) |
| Dense embeddings | `BAAI/bge-base-en-v1.5` (768-dim) via `sentence-transformers` |
| Sparse retrieval | BM25 / SPLADE via `fastembed` |
| Reranker | `BAAI/bge-reranker-v2-m3` (cross-encoder, top-50 → top-5) |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Orchestration | LlamaIndex |
| Local LLM | Ollama — Llama 3.1 8B / Qwen 2.5 7B |
| Hosted LLM | Groq free tier |
| Auth | `streamlit-authenticator` (bcrypt) |
| Audit / IDs | SQLite + `uuid.uuid4()` |
| Evaluation | RAGAS + Hit Rate@k / MRR@k / nDCG@k |
| Deployment | Streamlit Cloud + Qdrant Cloud + Groq |

---

## Dataset

| Source | Count | Words |
|---|---|---|
| Government PDFs (OSHA, HIPAA, CDC) | 88 | ~274,857 |
| Wikipedia articles | 10 | ~13,645 |
| Synthetic Q&A pairs | 60 | — |
| **Total** | **158** | **~288,502** |

All source documents are publicly available government publications or CC BY-SA licensed Wikipedia content.

---

## Getting Started

**Prerequisites:** Docker, [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# Clone and install
git clone https://github.com/dhruvi002/medical-compliance-rag
cd medical-compliance-rag
uv sync

# Start Qdrant and Ollama
docker compose up -d

# Pull the LLM
docker exec medcomply-ollama ollama pull llama3.1:8b

# Run the app
uv run streamlit run app.py
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for hosted deployment instructions.

---

## Development

```bash
# Lint
uv run ruff check

# Tests
uv run pytest

# Tests with coverage
uv run pytest --cov=medcomply
```

---

## Author

Dhruvi Shah — AI/ML Engineer, University of Massachusetts Amherst

## License

Code available for review. Government documents are public domain.
