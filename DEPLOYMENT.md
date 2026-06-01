# Deployment

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker (local only)
- Free accounts: [Qdrant Cloud](https://cloud.qdrant.io), [Groq](https://console.groq.com), [Streamlit Cloud](https://share.streamlit.io)

---

## Local Development

```bash
git clone https://github.com/dhruvi002/medical-compliance-rag
cd medical-compliance-rag
uv sync

# Start Qdrant and Ollama
docker compose up -d
docker exec medcomply-ollama ollama pull llama3.1:8b

# Generate auth config (bcrypt-hashed passwords)
python scripts/create_auth_config.py

# Run the app
uv run streamlit run app.py
```

Qdrant runs on `localhost:6333`; Ollama on `localhost:11434`. No secrets file needed for local dev with Docker.

---

## Hosted Deployment (Qdrant Cloud + Groq + Streamlit Cloud)

### 1. Qdrant Cloud

1. Create a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io).
2. Note the cluster URL (e.g. `https://xyz.qdrant.io`) and API key.

### 2. Populate Qdrant Cloud

Run once to ingest the synthetic compliance docs:

```bash
QDRANT_URL=https://xyz.qdrant.io \
QDRANT_API_KEY=your-key \
python scripts/ingest.py
```

### 3. Groq

1. Get a free API key at [console.groq.com](https://console.groq.com).

### 4. Streamlit Cloud

1. Fork the repo and connect it at [share.streamlit.io](https://share.streamlit.io).
2. Set the main file to `app.py`.
3. Add the following secrets in **App settings → Secrets**:

```toml
GROQ_API_KEY = "your-groq-api-key"
QDRANT_URL = "https://your-cluster.qdrant.io"
QDRANT_API_KEY = "your-qdrant-api-key"
LLM_BACKEND = "groq"
```

4. Deploy. Streamlit Cloud exposes secrets as environment variables; `app.py` reads them via `os.environ`.

See `.streamlit/secrets.toml.example` for the template.

---

## Environment Variables

| Variable | Required for | Description |
|---|---|---|
| `QDRANT_URL` | Hosted | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Hosted | Qdrant Cloud API key |
| `GROQ_API_KEY` | Hosted | Groq inference API key |
| `LLM_BACKEND` | Hosted | `"groq"` (set to `"ollama"` for local) |
