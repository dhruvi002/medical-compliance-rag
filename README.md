# Medical Compliance RAG System

A retrieval-augmented generation (RAG) system that answers healthcare-compliance
questions from authoritative sources (OSHA, HIPAA, CDC), with role-based access
control, an append-only audit trail, and an NLP-driven workforce skill-gap analysis
layer. Built to run entirely on free / open-source infrastructure.

> **Status:** Core system complete — retrieval, RBAC, audit, evaluation, and
> skill-gap analysis are fully implemented and tested. Hosted Streamlit Cloud
> deployment is a work in progress; the app runs locally today
> ([see Getting started](#getting-started)). 🔗 *Live demo link coming soon.*

> **Disclaimer:** This is a portfolio and educational project. It is **not**
> HIPAA-compliant and is **not** suitable for real PHI.

---

## What it does

- **Answers compliance questions** grounded in source documents, with numbered
  citations and a strict "answer only from context" prompt to suppress hallucination.
- **Enforces role-based access** at the vector-store level — a `staff` user cannot
  retrieve `admin`-only material, even by querying the index directly.
- **Logs every query** (user, role, query, answer snippet, source chunks, latency)
  to an append-only audit store.
- **Analyzes workforce skill gaps** by scoring ~100 synthetic employee profiles
  against compliance categories and surfacing organizational training priorities.
- **Exposes an executive dashboard** (Streamlit + Plotly) for system-health and
  skill-gap oversight.

---

## Architecture

```
Ingest (offline)
  data/processed/*.json
    └─ TokenChunker (500-token chunks, 50-token overlap)
         └─ VectorStore.upsert()
              ├─ dense:  BAAI/bge-base-en-v1.5  → 768-dim cosine vectors
              └─ sparse: SPLADE (Splade_PP_en_v1) → learned bag-of-tokens
                   └─ Qdrant collection "medical_compliance"
                        (payload: chunk_id, source_file, content, allowed_roles)

Query (online)
  User query (Streamlit, authenticated session)
    └─ hybrid retrieval: dense top-50 + sparse top-50
         ├─ RBAC payload filter applied server-side (role ∈ allowed_roles)
         └─ Reciprocal Rank Fusion (k=60)
              └─ cross-encoder rerank (bge-reranker-v2-m3) → top-5
                   └─ prompt build → LLM (Groq hosted / Ollama local)
                        └─ AuditLogger.log() → {answer, sources, latency_ms}
```

A fuller write-up of the design decisions and threat model lives in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Vector store | **Qdrant** | Native server-side hybrid search + RBAC payload filters inside the index |
| Dense embeddings | `BAAI/bge-base-en-v1.5` (768-d) | Strong CPU-speed retrieval (<100ms/batch), no GPU required |
| Sparse retrieval | `SPLADE` | Recovers exact code/section matches (e.g. "HIPAA §164.312") dense search blurs |
| Fusion | Reciprocal Rank Fusion (k=60) | Merges dense + sparse ranks without tuned interpolation weights |
| Reranker | `bge-reranker-v2-m3` (cross-encoder) | Joint query–passage scoring on the top-50 cutoff that matters |
| LLM | Llama 3.1 8B via **Groq** (hosted) or **Ollama** (local) | Swappable backend; Groq's free tier replaces Ollama where there's no GPU |
| Auth | `streamlit-authenticator` (bcrypt) | Identity bound to a verified session, not a UI selection — audit logs are trustworthy |
| Audit | SQLite, append-only, `uuid4` keys | Zero-config, transactional, collision-safe; no delete API at the app layer |
| Evaluation | RAGAS + IR metrics | Faithfulness/relevancy + Hit-Rate/MRR/nDCG, gated in CI |
| UI | Streamlit + Plotly | Single-process app; deployable free on Streamlit Cloud |

Orchestration is **framework-free** — the pipeline is four typed Python steps
(retrieve → rerank → build-prompt → generate). LangChain / LlamaIndex were
intentionally left out to keep the data flow auditable and dependency-light.

---

## Evaluation

Latest run (`reports/eval_2026-06-01`), n = 60 ground-truth queries:

**Retrieval**

| Metric | @5 | @10 |
|---|---|---|
| Hit Rate | 0.73 | 0.82 |
| MRR | 0.61 | 0.64 |
| nDCG | 0.66 | 0.70 |

**Generation** (RAGAS, judge `groq/llama-3.1-8b-instant`)

| Metric | Score |
|---|---|
| Faithfulness | 0.81 |
| Answer Relevancy | 0.76 |
| Context Precision | 0.69 |
| Context Recall | 0.74 |

Evals run in CI (`.github/workflows/eval.yml`) and a quality gate
(`scripts/check_eval_gate.py`) fails the build if scores regress.

---

## Skill-gap analysis

Beyond Q&A, the system scores a synthetic workforce of **100 employees** against
compliance categories and aggregates the results for leadership:

- 67 of 100 employees flagged as needing training; 26 urgent.
- Largest organizational gaps: HIPAA (39%), Medical Waste (34%), Infection
  Control (29%), Complex / Multi-Regulation (26%).
- Performance broken down by role and experience level for targeted training.

Outputs feed the Plotly dashboard in `src/compliance_dashboard.py`.

---

## Project structure

```
src/medcomply/        # rebuilt core package (typed, tested)
  settings.py           # single source of truth for tunables
  vector_store.py       # Qdrant hybrid retrieval + RBAC
  rag_system.py         # end-to-end pipeline
  llm_client.py         # Ollama / Groq abstraction
  audit_logger.py       # append-only SQLite audit trail
  auth.py               # bcrypt auth + role mapping
  chunker.py            # token / semantic chunking
  eval_retrieval.py     # IR metrics
  eval_generation.py    # RAGAS metrics
  skill_gap_analyzer.py # competency scoring
src/                  # first-generation modules (dashboard, learning paths)
scripts/              # ingest, eval, data prep utilities
tests/                # pytest suite (run in CI)
docs/                 # architecture + phase write-ups
reports/              # dated evaluation reports
data/                 # processed corpus, governance, audit, eval sets
app.py                # Streamlit application
docker-compose.yml    # local Qdrant + app
```

---

## Getting started

### Local (Ollama)

```bash
# 1. Models
brew install ollama
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 2. Environment (uv)
uv sync

# 3. Ingest + run
python scripts/ingest.py
streamlit run app.py
```

### Hosted (Groq, no GPU)

Set `llm_backend = "groq"` in settings (or the corresponding env var) and provide
a `GROQ_API_KEY`. This is the configuration targeted for the in-progress Streamlit
Cloud deployment (no GPU required).

### Tests & evaluation

```bash
pytest                      # unit + integration tests
python scripts/run_eval.py  # regenerate the evaluation report
```

---

## Security notes

- Passwords are bcrypt-hashed; plaintext is never stored.
- RBAC is enforced **server-side** in Qdrant via payload filters, not in the UI.
- The audit log exposes no delete method — records are append-only at the app layer.
- Known limits: single-process app (no separate API boundary), no log
  tamper-evidence, no rate limiting. See `docs/ARCHITECTURE.md#threat-model`.

---

## Data sources

All publicly available: OSHA (osha.gov/publications), HHS/HIPAA
(hhs.gov/hipaa/for-professionals), CDC (cdc.gov/infection-control), Wikipedia
(CC BY-SA), and synthetic Q&A generated for testing.

---

## Author

**Dhruvi Shah** — M.S. Computer Science, University of Massachusetts Amherst.

## License

Educational / portfolio use. Government documents are public domain.
