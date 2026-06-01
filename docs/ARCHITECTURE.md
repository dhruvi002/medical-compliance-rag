# Architecture — Medical Compliance RAG

## Data Flow

### Ingest (offline)

```
data/processed/*.json
        │
        ▼
scripts/ingest.py
        │  TokenChunker (500-token chunks, 50-token overlap)
        ▼
VectorStore.upsert()
        │  dense:  BAAI/bge-base-en-v1.5  → 768-dim cosine vectors
        │  sparse: SPLADE (prithivida/Splade_PP_en_v1) → bag-of-tokens vectors
        ▼
Qdrant collection "medical_compliance"
  payload per point: chunk_id, source_file, content, allowed_roles
```

### Query (online)

```
User query (Streamlit)
        │
        ▼
VectorStore.query(text, role, settings)
        │
        ├── dense search  top-50  ──┐
        │   BAAI/bge-base-en-v1.5   │
        │                           ├── RBAC filter applied server-side
        └── sparse search top-50  ──┘   (FieldCondition: allowed_roles ∋ role)
                SPLADE
        │
        ▼
_rrf_merge()  (Reciprocal Rank Fusion, k=60)
        │  merged ranked list
        ▼
bge-reranker-v2-m3  (cross-encoder)
        │  top-50 candidates → scores → top-5
        ▼
RAGSystem._build_prompt()
        │  "Answer ONLY from context" prompt with numbered sources
        ▼
LLMClient.complete()
        │  Groq (hosted) or Ollama (local)
        ▼
AuditLogger.log()
        │  SQLite row: uuid4 id, timestamp, user_id, role,
        │              query, answer_snippet, sources, latency_ms
        ▼
{answer, sources, truncated, latency_ms}  →  Streamlit UI
```

---

## Component Inventory

| Module | Role | Key interface |
|---|---|---|
| `settings.py` | Single source of truth for all tunables | `Settings(BaseModel)` |
| `vector_store.py` | Hybrid retrieval + RBAC | `VectorStore(settings, qdrant_url, qdrant_api_key)` |
| `llm_client.py` | LLM abstraction (Ollama / Groq) | `LLMClient.complete(prompt, settings) → LLMResponse` |
| `rag_system.py` | End-to-end RAG pipeline | `RAGSystem.query(text, user_id, role) → dict` |
| `audit_logger.py` | SQLite audit trail | `log()`, `recent()`, `stats()` |
| `auth.py` | Streamlit auth + RBAC role mapping | `load_authenticator()`, `get_current_user()` |
| `chunker.py` | Document chunking | `TokenChunker`, `SemanticChunker` |
| `eval_retrieval.py` | IR metrics | `run_retrieval_eval(vector_store, eval_set, settings)` |
| `eval_generation.py` | RAGAS generation metrics | `run_generation_eval(rag_system, eval_set, settings)` |
| `skill_gap_analyzer.py` | Semantic competency scoring | `score_answer()`, `cohort_themes()` |

---

## Decisions & Tradeoffs

### Qdrant over ChromaDB

Qdrant supports native server-side hybrid search — dense and sparse vectors are queried in a single request, with RBAC payload filters applied inside the index before results are returned. ChromaDB requires client-side post-filtering and has no native sparse vector support, which means a client could bypass RBAC filters by querying the underlying store directly. Qdrant also supports scalar and product quantization for memory-efficient serving.

### Hybrid retrieval (dense + sparse)

Dense vectors (`bge-base-en-v1.5`) capture semantic similarity but blur exact lexical tokens. Compliance work frequently requires exact recall of codes and section identifiers — "HIPAA §164.312" or "OSHA 29 CFR 1910.1030" can map to semantically similar but wrong passages in dense-only search. SPLADE sparse vectors behave like a learned BM25 and recover exact term matches. RRF merges the two ranked lists by reciprocal rank without requiring tuned interpolation weights.

### Cross-encoder rerank

Bi-encoders (the dense retrieval model) encode query and passage independently, so the query representation cannot attend to passage tokens. Cross-encoders receive the concatenated pair and score it jointly, which is significantly more accurate at the cost of O(n) inference calls. Retrieving top-50 with the bi-encoder then reranking to top-5 with `bge-reranker-v2-m3` keeps total latency manageable while applying cross-encoder quality at the cutoff that matters.

### `bge-base-en-v1.5` (768-dim) over larger embedding models

The base model runs on CPU in under 100ms per batch. Its MTEB BEIR score is competitive for a base-sized model, and the 512-token context window is sufficient for 500-token chunks with 50-token overlap. A 7B parameter embedder would require a GPU and add 10–20× latency with marginal quality gains on this domain.

### Groq for hosted inference

Streamlit Cloud has no GPU; Ollama cannot run there. Groq's free tier serves the same open-weight models (Llama 3.1 8B) used in local development via an OpenAI-compatible API, making the switch transparent. The `LLMClient` ABC means the backend is swappable by changing one settings field — `llm_backend: "groq"` vs `"ollama"`.

### Framework-free orchestration

The pipeline has four ordered steps: retrieve → rerank → build_prompt → generate. A heavyweight orchestration framework (LangChain, LlamaIndex) would add indirection, implicit state, and dependency churn without reducing the implementation surface at this scale. Every component is a plain Python class with a typed interface, which makes the data flow auditable and the decisions explainable without framework-specific knowledge.

### `streamlit-authenticator` (bcrypt) over dropdown auth

The original system let users select any identity from a dropdown — audit logs could be spoofed by selecting a different username. `streamlit-authenticator` stores bcrypt-hashed credentials in `config/auth.yaml`; identity is bound to a verified session cookie, not a UI choice. This makes `user_id` in the audit log a meaningful attestation rather than user-supplied data.

### SQLite for audit

SQLite is stdlib, zero-config, and transactional. It supports `COUNT`, `AVG`, and `DISTINCT` queries directly, which is all the analytics page requires. `uuid.uuid4()` PRIMARY KEYs prevent collision under rapid identical queries; the original MD5-truncated IDs could collide. There is no delete API on `AuditLogger` — rows are append-only at the application layer.

---

## Threat Model

### What the auth and audit setup protects

- Passwords are bcrypt-hashed in `config/auth.yaml`. The plaintext is never stored or transmitted to the application.
- Session tokens are tied to a verified login via `streamlit-authenticator` cookies. A user cannot impersonate another by changing a UI value.
- Qdrant payload filters enforce RBAC server-side. A `staff`-role user cannot retrieve `admin`-only chunks regardless of what they send to the query endpoint — the `FieldCondition` filter is applied inside Qdrant before results are returned to the application.
- Every query is logged with the authenticated `user_id`, `role`, query text, answer snippet, source chunk IDs, and latency. The `AuditLogger` class exposes no delete method; records are append-only at the application layer.

### What it does not protect

- This is a single-process Streamlit app with no separate API server. A principal with direct Python access to the running process can bypass all application-layer auth.
- `config/auth.yaml` contains bcrypt hashes. If that file is exfiltrated, an attacker can attempt offline dictionary attacks against weak passwords.
- The SQLite audit database is a local file. There is no tamper-evidence mechanism (e.g., hash chaining). Any principal with filesystem access can modify or delete log records.
- There is no rate limiting, brute-force lockout, or session expiry enforcement beyond the `streamlit-authenticator` cookie TTL.
- **This system is not HIPAA-compliant and is not suitable for real PHI. It is a portfolio and educational project.**
