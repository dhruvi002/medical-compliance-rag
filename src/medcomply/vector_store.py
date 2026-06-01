from typing import Dict, List

from .settings import Settings


def _rrf_merge(
    dense_hits: List[Dict],
    sparse_hits: List[Dict],
    k: int,
) -> List[Dict]:
    """Reciprocal Rank Fusion over two ranked hit lists.

    Each hit must have a 'id' key. Returns merged list sorted by descending
    RRF score, preserving the payload from whichever list first supplied the id.
    """
    scores: Dict[str, float] = {}
    payloads: Dict[str, Dict] = {}

    for rank, hit in enumerate(dense_hits):
        hit_id = hit["id"]
        scores[hit_id] = scores.get(hit_id, 0.0) + 1.0 / (k + rank + 1)
        payloads.setdefault(hit_id, hit)

    for rank, hit in enumerate(sparse_hits):
        hit_id = hit["id"]
        scores[hit_id] = scores.get(hit_id, 0.0) + 1.0 / (k + rank + 1)
        payloads.setdefault(hit_id, hit)

    merged = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    return [payloads[i] for i in merged]


class VectorStore:
    """Qdrant-backed hybrid retrieval with dense + sparse + rerank + RBAC."""

    def __init__(self, settings: Settings, qdrant_url: str = ":memory:", qdrant_api_key: str = ""):
        from fastembed import SparseTextEmbedding
        from qdrant_client import QdrantClient
        from sentence_transformers import CrossEncoder, SentenceTransformer

        self._settings = settings
        self._client = QdrantClient(qdrant_url, api_key=qdrant_api_key or None)
        self._dense = SentenceTransformer(settings.dense_model)
        self._sparse = SparseTextEmbedding(settings.sparse_model)
        self._reranker = CrossEncoder(settings.reranker_model)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        from qdrant_client.models import Distance, SparseVectorParams, VectorParams

        existing = [c.name for c in self._client.get_collections().collections]
        if self._settings.collection_name not in existing:
            self._client.create_collection(
                collection_name=self._settings.collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=self._settings.embedding_dim,
                        distance=Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(),
                },
            )

    def upsert(self, chunks: List[Dict]) -> None:
        from qdrant_client.models import PointStruct, SparseVector

        texts = [c["content"] for c in chunks]
        dense_vecs = self._dense.encode(texts, show_progress_bar=False).tolist()
        sparse_vecs = list(self._sparse.embed(texts))

        points = []
        for i, chunk in enumerate(chunks):
            sv = sparse_vecs[i]
            points.append(
                PointStruct(
                    id=i,
                    vector={
                        "dense": dense_vecs[i],
                        "sparse": SparseVector(
                            indices=sv.indices.tolist(),
                            values=sv.values.tolist(),
                        ),
                    },
                    payload={
                        "chunk_id": chunk.get("chunk_id", str(i)),
                        "source_file": chunk.get("source_file", ""),
                        "content": chunk["content"],
                        "allowed_roles": chunk.get("allowed_roles", ["admin", "manager", "staff"]),
                    },
                )
            )

        self._client.upsert(
            collection_name=self._settings.collection_name,
            points=points,
        )

    def query(self, text: str, role: str, settings: Settings) -> List[Dict]:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchAny,
            NamedSparseVector,
            NamedVector,
        )

        rbac_filter = Filter(
            must=[
                FieldCondition(
                    key="allowed_roles",
                    match=MatchAny(any=[role]),
                )
            ]
        )

        dense_vec = self._dense.encode([text], show_progress_bar=False)[0].tolist()
        sparse_vec_list = list(self._sparse.embed([text]))
        sv = sparse_vec_list[0]

        from qdrant_client.models import SparseVector

        dense_hits = self._client.search(
            collection_name=settings.collection_name,
            query_vector=NamedVector(name="dense", vector=dense_vec),
            query_filter=rbac_filter,
            limit=settings.top_k_retrieve,
            with_payload=True,
        )

        sparse_hits = self._client.search(
            collection_name=settings.collection_name,
            query_vector=NamedSparseVector(
                name="sparse",
                vector=SparseVector(
                    indices=sv.indices.tolist(),
                    values=sv.values.tolist(),
                ),
            ),
            query_filter=rbac_filter,
            limit=settings.top_k_retrieve,
            with_payload=True,
        )

        def _to_hit(r) -> Dict:
            p = r.payload or {}
            return {
                "id": str(r.id),
                "chunk_id": p.get("chunk_id", str(r.id)),
                "source_file": p.get("source_file", ""),
                "content": p.get("content", ""),
                "allowed_roles": p.get("allowed_roles", []),
            }

        merged = _rrf_merge(
            [_to_hit(r) for r in dense_hits],
            [_to_hit(r) for r in sparse_hits],
            k=settings.rrf_k,
        )

        candidates = merged[: settings.top_k_retrieve]
        if not candidates:
            return []

        pairs = [[text, c["content"]] for c in candidates]
        scores = self._reranker.predict(pairs)
        ranked = sorted(
            zip(scores, candidates),
            key=lambda x: x[0],
            reverse=True,
        )
        return [c for _, c in ranked[: settings.top_k_final]]
