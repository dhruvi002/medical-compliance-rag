from typing import Dict, List

from .audit_logger import AuditLogger
from .llm_client import LLMClient
from .settings import Settings
from .vector_store import VectorStore


class RAGSystem:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        llm_client: LLMClient,
        audit_logger: AuditLogger,
    ):
        self._settings = settings
        self._vector_store = vector_store
        self._llm_client = llm_client
        self._audit_logger = audit_logger

    def _build_prompt(self, query: str, chunks: List[Dict]) -> str:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source_file", "Unknown")
            context_parts.append(f"[Source {i}: {source}]\n{chunk['content']}")

        context = "\n\n".join(context_parts)
        return (
            "You are a medical compliance expert assistant. "
            "Answer the question based ONLY on the provided context.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            "ANSWER:"
        )

    def query(self, text: str, user_id: str, role: str) -> Dict:
        chunks = self._vector_store.query(text, role=role, settings=self._settings)
        prompt = self._build_prompt(text, chunks)
        llm_response = self._llm_client.complete(prompt, self._settings)
        sources = [c.get("chunk_id", "") for c in chunks]

        self._audit_logger.log(
            user_id=user_id,
            role=role,
            query=text,
            answer=llm_response.content,
            sources=sources,
            truncated=llm_response.truncated,
            latency_ms=llm_response.latency_ms,
        )

        return {
            "answer": llm_response.content,
            "sources": sources,
            "truncated": llm_response.truncated,
            "latency_ms": llm_response.latency_ms,
        }
