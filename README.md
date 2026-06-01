# Medical Compliance RAG System

A Retrieval-Augmented Generation system for answering healthcare compliance questions across HIPAA, OSHA, and infection-control domains.

---

## Status

| Component | Status |
|---|---|
| Package structure (`src/medcomply/`) | Implemented |
| Dependency management (`uv` + `pyproject.toml`) | Implemented |
| Linting (`ruff`) | Implemented |
| Test suite (`pytest`) | Implemented |
| Vector store (Qdrant, hybrid dense + sparse + rerank + RBAC) | Implemented |
| Dense embeddings (`BAAI/bge-base-en-v1.5`) | Implemented |
| Sparse retrieval / hybrid search (SPLADE via `fastembed`) | Implemented |
| Reranker (`BAAI/bge-reranker-v2-m3`) | Implemented |
| Auth (`streamlit-authenticator`, bcrypt) | Implemented |
| Audit logging (SQLite + UUID) | Implemented |
| Evaluation (RAGAS + retrieval metrics) | Implemented — Hit Rate / MRR / nDCG + RAGAS generation metrics |
| Skill-gap analysis | Implemented — semantic similarity scoring (cosine distance over `bge-base-en-v1.5` embeddings) with KMeans cohort theme detection |
| Local LLM (Ollama) | Implemented |
| Live demo (Qdrant Cloud + Groq, real inference) | Implemented |
| About/Analytics stats computed from live DB | Implemented |
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
| Orchestration | Custom `RAGSystem` (no framework dependency) |
| Local LLM | Ollama — Llama 3.1 8B / Qwen 2.5 7B |
| Hosted LLM | Groq free tier |
| Auth | `streamlit-authenticator` (bcrypt) |
| Audit / IDs | SQLite + `uuid.uuid4()` |
| Evaluation | RAGAS + Hit Rate@k / MRR@k / nDCG@k |
| Deployment | Streamlit Cloud + Qdrant Cloud + Groq |

---

## Dataset

The index is populated from synthetic compliance documents generated to match the structure and terminology of real HIPAA, OSHA, and infection-control regulations. No actual PHI or proprietary data is used.

| Source | Files |
|---|---|
| Synthetic HIPAA compliance text | `data/processed/synthetic_hipaa.json` |
| Synthetic OSHA compliance text | `data/processed/synthetic_osha.json` |
| Synthetic infection-control text | `data/processed/synthetic_infection_control.json` |
| Synthetic medical-waste text | `data/processed/synthetic_medical_waste.json` |
| Synthetic documentation/training text | `data/processed/synthetic_documentation_training.json` |
| Synthetic edge-case scenarios | `data/processed/synthetic_edge_cases.json` |
| Labeled evaluation Q&A pairs | `data/eval/eval_set.json` (60 pairs) |

---

## Evaluation

Evaluated on a hand-labeled set of 60 query→chunk pairs derived from the same synthetic documents used to populate the index. Numbers reflect performance on the synthetic corpus and have not been benchmarked against external datasets.

**Retrieval** (n=60, in-memory Qdrant):

| Metric | @5 | @10 |
|---|---|---|
| Hit Rate | 0.7333 | 0.8167 |
| MRR | 0.6083 | 0.6394 |
| nDCG | 0.6612 | 0.7031 |

**Generation** (n=60, judge: `groq/llama-3.1-8b-instant`):

| Metric | Score |
|---|---|
| Faithfulness | 0.8124 |
| Answer Relevancy | 0.7643 |
| Context Precision | 0.6912 |
| Context Recall | 0.7388 |

Full report: [`reports/eval_2026-06-01.md`](reports/eval_2026-06-01.md). To reproduce: `uv run python scripts/run_eval.py`.

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
