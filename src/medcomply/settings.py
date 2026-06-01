from pydantic import BaseModel


class Settings(BaseModel):
    # Retrieval
    dense_model: str = "BAAI/bge-base-en-v1.5"
    sparse_model: str = "prithivida/Splade_PP_en_v1"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_dim: int = 768
    top_k_retrieve: int = 50
    top_k_final: int = 5
    rrf_k: int = 60
    collection_name: str = "medical_compliance"

    # Generation
    llm_backend: str = "ollama"  # "ollama" | "groq"
    ollama_model: str = "llama3.1:8b"
    groq_model: str = "llama-3.1-8b-instant"
    max_tokens: int = 512
    temperature: float = 0.1
    top_p: float = 0.9

    # Deployment
    qdrant_url: str = ":memory:"

    # Chunking (read by ingest scripts; not used at query time)
    chunk_size: int = 500
    chunk_overlap: int = 50
