# Deployment

## Local

```bash
git clone https://github.com/dhruvi002/medical-compliance-rag
cd medical-compliance-rag
uv sync
docker compose up -d
docker exec medcomply-ollama ollama pull llama3.1:8b
uv run streamlit run app.py
```

Requires Docker for Qdrant and Ollama. `docker-compose.yml` defines both services with named volumes for persistence.

## Hosted (Streamlit Cloud + Qdrant Cloud + Groq)

Streamlit Cloud has no GPU, so inference is served by Groq (free tier, same open-weights models). Vector storage is Qdrant Cloud free tier.

### 1. Qdrant Cloud

1. Create a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io).
2. Copy the cluster URL and API key.
3. Add to Streamlit secrets:
   ```toml
   QDRANT_URL = "https://<cluster>.qdrant.io"
   QDRANT_API_KEY = "<key>"
   ```

### 2. Groq

1. Get a free API key at [console.groq.com](https://console.groq.com).
2. Add to Streamlit secrets:
   ```toml
   GROQ_API_KEY = "<key>"
   ```

### 3. Streamlit Cloud

1. Fork the repo and connect it at [share.streamlit.io](https://share.streamlit.io).
2. Set the main file to `app.py`.
3. Add the secrets above in the app settings.
4. Deploy.

## Environment Variables

| Variable | Required for | Description |
|---|---|---|
| `QDRANT_URL` | Hosted | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Hosted | Qdrant Cloud API key |
| `GROQ_API_KEY` | Hosted | Groq inference API key |

For local runs these are not needed — Qdrant runs in Docker on `localhost:6333` and Ollama on `localhost:11434`.
