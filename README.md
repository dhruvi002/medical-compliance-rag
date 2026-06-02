# Medical Compliance RAG System

A question-answering system for healthcare compliance, built with Retrieval-Augmented Generation (RAG). Staff ask plain-English questions about HIPAA, OSHA, infection control, and medical waste policy — the system retrieves the relevant policy excerpts and generates a grounded answer, citing its sources. Every query is logged, access is role-controlled, and answers are evaluated for factual faithfulness against the source documents.

> **Portfolio / educational project. Not a clinical tool. Not HIPAA-compliant. Do not use with real patient data.**

---

## What problem does it solve?

Healthcare organisations navigate overlapping compliance regimes — HIPAA privacy rules, OSHA bloodborne pathogen standards, infection control protocols, medical waste regulations. Staff with questions typically search lengthy PDF documents or wait for a compliance officer. This system lets any authenticated staff member ask questions in plain English and get answers drawn directly from the policy corpus, with source citations attached so the answer can be verified.

The project demonstrates a production-quality RAG pipeline: hybrid retrieval with role-based access control, a cross-encoder reranker, LLM-generated answers, a full evaluation harness, and an automated CI pipeline — all deployed on free infrastructure.

---

## Live application

Deployed on Streamlit Cloud (Qdrant Cloud + Groq inference). Authenticate with the demo credentials in the sidebar to try it.

**Roles:**
| Role | Access |
|---|---|
| `admin` | All policy domains |
| `manager` | HIPAA, OSHA, infection control |
| `staff` | Infection control and general guidance only |

The same question asked by a `staff` user and an `admin` user will return different chunks, because RBAC filtering happens inside the vector database before results are returned to the application.

---

## How it works

### The retrieval-augmented generation loop

A user submits a question. The system doesn't search by keyword — it understands the *meaning* of the question and finds the most relevant policy passages. It then hands those passages to a language model, which writes a concise answer in plain English. The answer is grounded strictly in retrieved text; the model is instructed not to add information from outside the documents.

```
User question
      │
      ▼
VectorStore.query()
      ├── Dense search (semantic)   ─┐
      │   bge-base-en-v1.5           ├── RBAC filter applied inside Qdrant
      └── Sparse search (lexical)  ─┘   (staff cannot retrieve admin-only chunks)
            SPLADE
      │
      ▼
Reciprocal Rank Fusion   (merges the two ranked lists)
      │
      ▼
Cross-encoder reranker   (bge-reranker-v2-m3, top-50 → top-5)
      │
      ▼
RAGSystem._build_prompt()   ("Answer ONLY from the context below…")
      │
      ▼
LLM (Groq / Ollama)
      │
      ▼
AuditLogger   (SQLite: user_id, role, query, answer, sources, latency)
      │
      ▼
Answer + cited sources  →  Streamlit UI
```

### Why hybrid retrieval?

Dense (semantic) search finds passages with similar *meaning* to the question. Sparse (lexical) search finds passages that contain the exact *words* in the question. Compliance work needs both: "what does OSHA 29 CFR 1910.1030 require?" is a semantic question about bloodborne pathogen standards, but the code `1910.1030` must match exactly. Using only dense search would miss exact regulatory citations; using only sparse search would miss paraphrased concepts. Reciprocal Rank Fusion combines both ranked lists without needing to tune interpolation weights.

### Why a reranker on top of retrieval?

The retrieval models (bi-encoders) encode the query and each document separately and compare their vector representations. This is fast but imprecise — the query has no visibility into the specific tokens in the document during encoding. The reranker (a cross-encoder) reads the query and each candidate passage *together* in a single forward pass, scoring the pair jointly. It is significantly more accurate but too slow to run on the full corpus. Running it on the top 50 candidates from hybrid retrieval gives cross-encoder quality at the 5 results that actually reach the user.

---

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Vector database | Qdrant | Native hybrid search; RBAC filters applied server-side inside the index — a client cannot bypass them by querying the store directly |
| Dense embeddings | `BAAI/bge-base-en-v1.5` (768-dim) | Competitive MTEB BEIR score at base size; runs on CPU in <100ms; 512-token context matches the 500-token chunk size |
| Sparse retrieval | SPLADE via `fastembed` | Learned sparse vectors behave like a tuned BM25 — precise lexical recall for regulatory codes and section identifiers |
| Reranker | `BAAI/bge-reranker-v2-m3` | Cross-encoder joint scoring; applied to top-50 → top-5 to keep latency manageable |
| Fusion | Reciprocal Rank Fusion (RRF) | Combines dense and sparse ranked lists by reciprocal rank; no interpolation weights to tune |
| Orchestration | Custom `RAGSystem` class | Four ordered steps (retrieve → rerank → prompt → generate); no framework dependency, fully auditable |
| Local LLM | Ollama — Llama 3.1 8B | Runs in Docker; same open-weight model used in production via Groq |
| Hosted LLM | Groq free tier | Streamlit Cloud has no GPU; Groq serves the same Llama 3.1 8B via OpenAI-compatible API — backend is swappable by changing one setting |
| Auth | `streamlit-authenticator` (bcrypt) | Passwords are hashed; identity is bound to a verified session cookie, not a UI dropdown that could be spoofed |
| Audit logging | SQLite + `uuid.uuid4()` | Stdlib, zero-config, transactional; UUID primary keys prevent collision; `AuditLogger` exposes no delete method — log is append-only |
| Data models | `pydantic` v2 | Typed, validated settings and payloads |
| Dependency management | `uv` + `pyproject.toml` + `uv.lock` | Reproducible installs; significantly faster than pip |
| Linting | `ruff` | Replaces black + flake8 + isort in a single tool |
| Testing | `pytest` + `pytest-cov` | 65 tests; 99% coverage; gate enforced in CI |
| Deployment | Streamlit Cloud + Qdrant Cloud + Groq | All free tiers; no infrastructure to manage |

---

## Evaluation

The system is evaluated against a hand-labeled set of 60 query→chunk pairs derived from the same synthetic documents loaded into the index. Two evaluation passes are run: one for retrieval quality and one for generation quality.

### Retrieval

Measures whether the relevant policy chunk appears in the top results. Hit Rate answers "did the right chunk appear at all?"; MRR answers "how high up was it?"; nDCG weighs both presence and rank.

| Metric | @5 | @10 |
|---|---|---|
| Hit Rate | 0.73 | 0.82 |
| MRR | 0.61 | 0.64 |
| nDCG | 0.66 | 0.70 |

*73% of questions have a relevant chunk in the top 5 results; 82% in the top 10.*

### Generation

Measures answer quality using [RAGAS](https://docs.ragas.io), with a second LLM acting as an automatic judge.

| Metric | Score | What it means |
|---|---|---|
| Faithfulness | 0.81 | 81% of claims in the answer are directly supported by the retrieved passages |
| Answer Relevancy | 0.76 | Answers are on-topic relative to the question |
| Context Precision | 0.69 | Retrieved passages are mostly relevant (low noise) |
| Context Recall | 0.74 | Most information needed to answer the question was retrieved |

*Judge model: `groq/llama-3.1-8b-instant`. Full report: [`reports/eval_2026-06-01.md`](reports/eval_2026-06-01.md)*

Evaluation is re-run weekly by a GitHub Actions workflow (`eval.yml`) and results are checked against minimum thresholds (`hit_rate@5 ≥ 0.70`, `faithfulness ≥ 0.78`, `context_precision ≥ 0.66`).

---

## Project quality

| Measure | Detail |
|---|---|
| Test suite | 65 tests across 6 test files |
| Coverage | 99% (`pytest-cov`); CI fails below 90% |
| CI | GitHub Actions on every push: `uv sync` → `ruff check` → `pytest --cov-fail-under=90` |
| Eval gate | Weekly GitHub Actions run; exits non-zero if retrieval or generation metrics fall below baseline |
| Linting | `ruff` — zero warnings |

---

## Dataset

Synthetic compliance documents were generated to match the structure and terminology of real regulatory text. No actual PHI or proprietary policy documents are used.

| Domain | File |
|---|---|
| HIPAA privacy and security rules | `data/processed/synthetic_hipaa.json` |
| OSHA bloodborne pathogen standards | `data/processed/synthetic_osha.json` |
| Infection control protocols | `data/processed/synthetic_infection_control.json` |
| Medical waste disposal | `data/processed/synthetic_medical_waste.json` |
| Documentation and training requirements | `data/processed/synthetic_documentation_training.json` |
| Edge-case scenarios | `data/processed/synthetic_edge_cases.json` |
| Labeled evaluation pairs | `data/eval/eval_set.json` (60 Q→chunk pairs) |

Documents are chunked into 500-token segments with 50-token overlap using a `TokenChunker`, then indexed into Qdrant with both dense and sparse vectors.

---

## Getting started (local)

**Prerequisites:** Docker, [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

```bash
git clone https://github.com/dhruvi002/medical-compliance-rag
cd medical-compliance-rag
uv sync

# Start Qdrant (vector database) and Ollama (local LLM)
docker compose up -d
docker exec medcomply-ollama ollama pull llama3.1:8b

# Generate auth config (creates bcrypt-hashed credentials)
python scripts/create_auth_config.py

# Index the compliance documents
python scripts/ingest.py

# Run the app
uv run streamlit run app.py
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for hosted deployment (Qdrant Cloud + Groq + Streamlit Cloud).

---

## Development

```bash
uv run ruff check                                    # lint
uv run pytest                                        # tests
uv run pytest --cov=medcomply --cov-fail-under=90   # tests with coverage gate
uv run python scripts/run_eval.py                    # run full eval (requires GROQ_API_KEY)
```

---

## Repository layout

```
src/medcomply/        installable package
  settings.py         all tunables (pydantic BaseModel)
  vector_store.py     hybrid retrieval + RBAC (Qdrant)
  llm_client.py       LLM abstraction — OllamaClient / GroqClient
  rag_system.py       end-to-end pipeline (retrieve → rerank → prompt → generate)
  audit_logger.py     SQLite query log
  auth.py             bcrypt auth + role resolution
  chunker.py          TokenChunker / SemanticChunker
  eval_retrieval.py   Hit Rate / MRR / nDCG metrics
  eval_generation.py  RAGAS faithfulness / relevancy / precision / recall
  skill_gap_analyzer.py  cosine-similarity competency scoring + KMeans cohort themes

app.py                Streamlit frontend (RAG Assistant / Analytics / About)
scripts/
  ingest.py           chunk and index compliance documents into Qdrant
  run_eval.py         run retrieval + generation eval, write reports/
  check_eval_gate.py  assert eval metrics above threshold (used in CI)
  create_auth_config.py  generate config/auth.yaml with hashed passwords
data/
  processed/          synthetic compliance documents (JSON)
  eval/               labeled evaluation set
reports/              eval output (JSON + Markdown)
tests/                65 tests
.github/workflows/
  ci.yml              push/PR gate: lint + test
  eval.yml            weekly eval + metric threshold check
```

---

## Author

Dhruvi Shah — AI/ML Engineer, University of Massachusetts Amherst

## License

Code available for review. Regulatory text is public domain.
