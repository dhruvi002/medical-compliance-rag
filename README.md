# Medical Compliance RAG System

A question-answering system for healthcare compliance policy. Staff ask questions
in plain English — about HIPAA, OSHA bloodborne-pathogen standards, infection
control, or medical waste — and the system retrieves the relevant policy passages
and writes a grounded answer with numbered source citations.

**Roles (local and hosted):**

| Role | Access |
|---|---|
| `admin` | All policy domains |
| `manager` | HIPAA, OSHA, infection control |
| `staff` | Infection control and general guidance only |

The same question asked by a `staff` user and an `admin` user returns different
chunks — RBAC filtering happens inside the vector database before results reach
the application.

---

## What it does

- **Answers compliance questions** grounded strictly in the source corpus; the
  model is instructed not to add information from outside the retrieved passages.
- **Enforces role-based access at the vector-store level** — a `staff` user
  cannot retrieve `admin`-only chunks, even by querying the index directly.
- **Logs every query** (user, role, query, answer snippet, retrieved chunk IDs,
  latency) to an append-only audit store with no delete API exposed.
- **Analyzes workforce skill gaps** — scores synthetic employee profiles using
  embedding-based cosine similarity per compliance category and surfaces
  organisational training priorities via KMeans cohort clustering.
- **Exposes an executive dashboard** (Streamlit + Plotly) for system-health
  monitoring and skill-gap oversight.

---

## Example

> **Q (staff role):** What should I do immediately after a needlestick injury?

> **A:** Wash the exposure site immediately with soap and water. Report to your
> supervisor and occupational health within two hours [Source 1]. Obtain baseline
> HIV and hepatitis testing [Source 1]. Initiate post-exposure prophylaxis (PEP)
> within one hour — effectiveness decreases significantly after 72 hours [Source 2].
> Document the date, time, route of exposure, and source-patient information as
> required under OSHA 1910.1030(f) [Source 3].
>
> *Sources: osha\_bloodborne\_pathogens, exposure\_risk\_factsheet, needlestick\_injury*

---

## How it works

A user submits a question. The system maps it into a vector space and finds the
most semantically similar policy passages, while also running a sparse lexical
search that preserves exact regulatory codes. Both ranked lists are fused and
re-scored by a cross-encoder before reaching the language model.

```
User question
      │
      ▼
VectorStore.query(text, role, settings)
      ├── Dense search   top-50  ──┐  BAAI/bge-base-en-v1.5 (semantic)
      └── Sparse search  top-50  ──┘  SPLADE / fastembed  (exact-term recall)
            │  RBAC payload filter applied server-side (role ∈ allowed_roles)
            ▼
      Reciprocal Rank Fusion  (k=60)
            │
            ▼
      bge-reranker-v2-m3  (cross-encoder, top-50 → top-5)
            │
            ▼
      RAGSystem._build_prompt()   "Answer ONLY from the context below…"
            │
            ▼
      LLMClient.complete()   Groq (hosted) or Ollama (local)
            │
            ▼
      AuditLogger.log()   SQLite row: uuid4, timestamp, user_id, role,
                          query, answer_snippet, sources, latency_ms
            │
            ▼
      {answer, sources, latency_ms}  →  Streamlit UI
```

### Why hybrid retrieval?

Dense (semantic) search finds passages with similar *meaning* to the question.
Sparse (lexical) search finds passages that contain the exact *words*. Compliance
work needs both: "what does OSHA 29 CFR 1910.1030 require?" is a semantic
question, but the code `1910.1030` must match exactly. Dense-only search blurs
exact regulatory identifiers; sparse-only search misses paraphrased concepts.
Reciprocal Rank Fusion merges both ranked lists by reciprocal rank without
requiring tuned interpolation weights.

### Why a reranker on top of retrieval?

Retrieval models (bi-encoders) encode the query and each document
*independently* — the query representation cannot attend to passage tokens at
encoding time. The reranker (a cross-encoder) reads the query and each candidate
passage *together* in a single forward pass, scoring them jointly. This is
significantly more accurate but scales as O(n) inference calls, making it too
slow to run on the full corpus. Running it on the top 50 candidates from hybrid
retrieval gives cross-encoder quality at the 5 results that actually reach the
user.

### Why no LangChain / LlamaIndex?

The pipeline has four ordered steps: retrieve → rerank → build-prompt → generate.
A framework adds indirection and dependency churn without reducing the
implementation surface at this scale. Every component is a plain Python class
with a typed interface — the data flow is directly auditable without
framework-specific knowledge.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Vector store | **Qdrant** | Native server-side hybrid search + RBAC payload filters inside the index; a client cannot bypass access control by querying the store directly |
| Dense embeddings | `BAAI/bge-base-en-v1.5` (768-d) | Competitive MTEB BEIR score at base size; <100 ms/batch on CPU; 512-token context window matches the 500-token chunk size |
| Sparse retrieval | SPLADE via `fastembed` (`Splade_PP_en_v1`) | Learned sparse vectors with BM25-like exact recall for regulatory codes and CFR section identifiers that dense search blurs |
| Fusion | Reciprocal Rank Fusion (k=60) | Merges dense + sparse ranked lists by reciprocal rank; no interpolation weights to tune |
| Reranker | `bge-reranker-v2-m3` (cross-encoder) | Joint query–passage scoring on the top-50 cutoff; significantly more accurate than bi-encoder similarity |
| LLM | Llama 3.1 8B via **Groq** (hosted) or **Ollama** (local) | Same open-weight model; Groq's free tier serves it where there's no GPU; switching backends requires one settings field change |
| Auth | `streamlit-authenticator` (bcrypt) | Identity bound to a verified session cookie — `user_id` in audit logs is an attestation, not a UI selection |
| Audit | SQLite, append-only, `uuid4` keys | Zero-config, transactional, collision-safe; no delete API at the application layer |
| Evaluation | RAGAS + IR metrics | Faithfulness/relevancy scored by a judge LLM; Hit Rate/MRR/nDCG measure retrieval quality; both gated in CI |
| UI | Streamlit + Plotly | Single-process app; deployable on Streamlit Cloud free tier |
| Packaging | `uv` + `pyproject.toml` + `uv.lock` | Reproducible installs; significantly faster than pip |
| Linting | `ruff` | Replaces black + flake8 + isort in a single tool |

---

## Evaluation

**Latest run** — `reports/eval_2026-06-01`, n = 60 ground-truth queries.

### Retrieval

| Metric | @5 | @10 |
|---|---|---|
| Hit Rate | 0.73 | 0.82 |
| MRR | 0.61 | 0.64 |
| nDCG | 0.66 | 0.70 |

*73% of questions have a relevant chunk in the top 5 results; 82% in the top 10.*

### Generation (RAGAS, judge: `groq/llama-3.1-8b-instant`)

| Metric | Score | What it means |
|---|---|---|
| Faithfulness | 0.81 | 81% of claims in the answer are directly supported by the retrieved passages |
| Answer Relevancy | 0.76 | Answers are on-topic relative to the question |
| Context Precision | 0.69 | Retrieved passages are mostly relevant (low noise) |
| Context Recall | 0.74 | Most information needed to answer the question was retrieved |

### CI quality gates

A weekly GitHub Actions workflow re-runs the full eval suite and exits non-zero
if scores fall below:

| Metric | Minimum threshold |
|---|---|
| Hit Rate @5 | ≥ 0.70 |
| Faithfulness | ≥ 0.78 |
| Context Precision | ≥ 0.66 |

Full report: [`reports/eval_2026-06-01.md`](reports/eval_2026-06-01.md)

---

## Skill-gap analysis

Beyond Q&A, the system scores a synthetic workforce of ~100 employees across
compliance categories and surfaces organisational training priorities.

Each employee's free-text answers are embedded with `bge-base-en-v1.5` and
scored against canonical reference answers via cosine similarity per category
(weak threshold = 0.60). KMeans clustering over per-employee weakness vectors
then surfaces cohort-level training themes for leadership review.

Results feed the Plotly dashboard in `app.py`.

---

## Project quality

| Measure | Detail |
|---|---|
| Test suite | 65 tests across 6 test files |
| Coverage | 99% line coverage; CI fails below 90% |
| CI | GitHub Actions on every push: `uv sync` → `ruff check` → `pytest --cov-fail-under=90` |
| Eval gate | Weekly GitHub Actions run; exits non-zero if retrieval or generation metrics fall below baseline thresholds |
| Linting | `ruff` — zero warnings |

---

## Getting started

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

### Hosted (Groq, no GPU required)

Set `llm_backend = "groq"` in settings (or via the corresponding env var) and
provide a `GROQ_API_KEY`. This is the configuration used for the Streamlit Cloud
deployment.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full hosted setup (Qdrant Cloud +
Groq + Streamlit Cloud).

### Tests and evaluation

```bash
uv run ruff check                                    # lint
uv run pytest                                        # tests
uv run pytest --cov=medcomply --cov-fail-under=90   # with coverage gate
uv run python scripts/run_eval.py                    # regenerate eval report (requires GROQ_API_KEY)
```

---

## Security notes

- Passwords are bcrypt-hashed in `config/auth.yaml`; plaintext is never stored
  or transmitted to the application.
- RBAC is enforced **server-side** in Qdrant via payload filters — not in the
  UI layer. A `staff`-role session cannot retrieve `admin`-only chunks regardless
  of what it sends to the query endpoint.
- The audit log exposes no delete method — records are append-only at the
  application layer.
- **Known limits:** single-process app (no separate API boundary), no log
  tamper-evidence (no hash chaining), no rate limiting or brute-force lockout.
  Full threat model in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Dataset

All documents in `data/processed/` are **synthetic** — generated to match the
structure and terminology of real regulatory text. No actual PHI or proprietary
policy documents are used.

| Domain | File |
|---|---|
| HIPAA privacy and security rules | `synthetic_hipaa.json` |
| OSHA bloodborne pathogen standards | `synthetic_osha.json` |
| Infection control protocols | `synthetic_infection_control.json` |
| Medical waste disposal | `synthetic_medical_waste.json` |
| Documentation and training requirements | `synthetic_documentation_training.json` |
| Edge-case scenarios | `synthetic_edge_cases.json` |
| Labeled evaluation pairs | `data/eval/eval_set.json` (60 Q→chunk pairs) |

---

## Repository layout

```
src/medcomply/          installable package
  settings.py             all tunables (pydantic v2 BaseModel)
  vector_store.py         Qdrant hybrid retrieval + RBAC
  rag_system.py           end-to-end pipeline (retrieve → rerank → prompt → generate)
  llm_client.py           LLM abstraction — OllamaClient / GroqClient
  audit_logger.py         append-only SQLite audit log
  auth.py                 bcrypt auth + role resolution
  chunker.py              TokenChunker / SemanticChunker
  eval_retrieval.py       Hit Rate / MRR / nDCG
  eval_generation.py      RAGAS faithfulness / relevancy / precision / recall
  skill_gap_analyzer.py   cosine-similarity competency scoring + KMeans cohort themes

app.py                  Streamlit frontend
scripts/
  ingest.py               chunk and index compliance documents into Qdrant
  run_eval.py             run retrieval + generation eval, write reports/
  check_eval_gate.py      assert eval metrics above threshold (used in CI)
  create_auth_config.py   generate config/auth.yaml with hashed passwords
data/
  processed/              synthetic compliance documents (JSON)
  eval/                   labeled evaluation set (60 Q→chunk pairs)
  audit/                  SQLite audit database
  governance/             document registry and compliance reports
reports/                  dated evaluation reports (JSON + Markdown)
tests/                    65 tests
docs/                     ARCHITECTURE.md + phase write-ups
.github/workflows/
  ci.yml                  push/PR gate: lint + test
  eval.yml                weekly eval + metric threshold check
```

---

## Author

**Dhruvi Shah** — M.S. Computer Science, University of Massachusetts Amherst  
[linkedin.com/in/dhruvi002](https://linkedin.com/in/dhruvi002) · [github.com/dhruvi002](https://github.com/dhruvi002)

## License

Code available for review. Synthetic regulatory text is for educational use.
