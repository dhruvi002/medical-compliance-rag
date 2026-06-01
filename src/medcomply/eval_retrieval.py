import math
from typing import Dict, List


def hit_rate_at_k(results: List[List[str]], relevant: List[List[str]], k: int) -> float:
    """Fraction of queries where at least one relevant chunk appears in top-k."""
    if not results:
        return 0.0
    hits = 0
    for retrieved, rel_set in zip(results, relevant):
        top_k = retrieved[:k]
        if any(r in rel_set for r in top_k):
            hits += 1
    return hits / len(results)


def mrr_at_k(results: List[List[str]], relevant: List[List[str]], k: int) -> float:
    """Mean Reciprocal Rank: average of 1/rank of first relevant hit within top-k."""
    if not results:
        return 0.0
    total = 0.0
    for retrieved, rel_set in zip(results, relevant):
        top_k = retrieved[:k]
        for rank, chunk_id in enumerate(top_k, start=1):
            if chunk_id in rel_set:
                total += 1.0 / rank
                break
    return total / len(results)


def ndcg_at_k(results: List[List[str]], relevant: List[List[str]], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k (binary relevance)."""
    if not results:
        return 0.0

    def _dcg(retrieved: List[str], rel_set: List[str], k: int) -> float:
        score = 0.0
        for rank, chunk_id in enumerate(retrieved[:k], start=1):
            if chunk_id in rel_set:
                score += 1.0 / math.log2(rank + 1)
        return score

    def _ideal_dcg(rel_set: List[str], k: int) -> float:
        n_ideal = min(len(rel_set), k)
        return sum(1.0 / math.log2(i + 2) for i in range(n_ideal))

    total = 0.0
    for retrieved, rel_set in zip(results, relevant):
        ideal = _ideal_dcg(rel_set, k)
        if ideal == 0.0:
            continue
        total += _dcg(retrieved, rel_set, k) / ideal
    return total / len(results)


def run_retrieval_eval(
    vector_store,
    eval_set: List[Dict],
    settings,
    role: str = "admin",
) -> Dict:
    """
    Run Hit Rate, MRR, and nDCG at k=5 and k=10 against the labeled eval set.

    Returns dict with keys hit_rate@5, mrr@5, ndcg@5, hit_rate@10, mrr@10, ndcg@10, n_queries.
    """
    retrieved_lists: List[List[str]] = []
    relevant_lists: List[List[str]] = []

    for entry in eval_set:
        chunks = vector_store.query(entry["query"], role=role, settings=settings)
        retrieved_ids = [c.get("chunk_id", "") for c in chunks]
        retrieved_lists.append(retrieved_ids)
        relevant_lists.append(entry["relevant_chunk_ids"])

    return {
        "hit_rate@5": hit_rate_at_k(retrieved_lists, relevant_lists, k=5),
        "mrr@5": mrr_at_k(retrieved_lists, relevant_lists, k=5),
        "ndcg@5": ndcg_at_k(retrieved_lists, relevant_lists, k=5),
        "hit_rate@10": hit_rate_at_k(retrieved_lists, relevant_lists, k=10),
        "mrr@10": mrr_at_k(retrieved_lists, relevant_lists, k=10),
        "ndcg@10": ndcg_at_k(retrieved_lists, relevant_lists, k=10),
        "n_queries": len(eval_set),
    }
