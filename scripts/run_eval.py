"""
Evaluation runner: populates an in-memory Qdrant instance with synthetic compliance
chunks, then runs retrieval and generation metrics against data/eval/eval_set.json.

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --skip-generation   # skip RAGAS (no API key required)
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

# Make the installed package importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medcomply.audit_logger import AuditLogger
from medcomply.eval_generation import run_generation_eval
from medcomply.eval_retrieval import run_retrieval_eval
from medcomply.llm_client import get_llm_client
from medcomply.rag_system import RAGSystem
from medcomply.settings import Settings
from medcomply.vector_store import VectorStore


def load_eval_set(path: str):
    with open(path) as f:
        raw = json.load(f)
    # Support both bare list and {entries: [...]} formats
    if isinstance(raw, list):
        return raw
    return raw["entries"]


def load_synthetic_chunks(data_dir: str):
    """
    Load synthetic compliance docs and convert each Q-A entry to a chunk dict.
    chunk_id follows pattern {domain}_{index:03d} — must match eval_set.json labels.
    """
    files = {
        "hipaa": "synthetic_hipaa.json",
        "osha": "synthetic_osha.json",
        "infection_control": "synthetic_infection_control.json",
        "medical_waste": "synthetic_medical_waste.json",
        "documentation_training": "synthetic_documentation_training.json",
        "edge_cases": "synthetic_edge_cases.json",
    }
    chunks = []
    for domain, fname in files.items():
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            print(f"[warn] missing {fpath}, skipping")
            continue
        with open(fpath) as f:
            items = json.load(f)
        for i, item in enumerate(items):
            chunks.append(
                {
                    "chunk_id": f"{domain}_{i:03d}",
                    "content": item["answer"],
                    "source_file": fname,
                    "allowed_roles": ["admin", "manager", "staff"],
                }
            )
    return chunks


def write_reports(retrieval: dict, generation: dict, reports_dir: str):
    today = date.today().isoformat()
    json_path = os.path.join(reports_dir, f"eval_{today}.json")
    md_path = os.path.join(reports_dir, f"eval_{today}.md")

    combined = {"date": today, "retrieval": retrieval, "generation": generation}
    with open(json_path, "w") as f:
        json.dump(combined, f, indent=2)

    n_ret = retrieval.get("n_queries", 0)
    n_gen = generation.get("n_queries", 0)
    gen_error = generation.get("error", "")

    def fmt(val):
        return f"{val:.2f}" if isinstance(val, float) else str(val)

    judge_label = "groq/llama-3.1-8b-instant" if not gen_error else "n/a"

    lines = [
        f"# Evaluation Report — {today}",
        "",
        f"## Retrieval (n={n_ret})",
        "| Metric | @5 | @10 |",
        "|---|---|---|",
        f"| Hit Rate | {fmt(retrieval.get('hit_rate@5', 0))} | {fmt(retrieval.get('hit_rate@10', 0))} |",
        f"| MRR | {fmt(retrieval.get('mrr@5', 0))} | {fmt(retrieval.get('mrr@10', 0))} |",
        f"| nDCG | {fmt(retrieval.get('ndcg@5', 0))} | {fmt(retrieval.get('ndcg@10', 0))} |",
        "",
        f"## Generation (n={n_gen}, judge: {judge_label})",
        "| Metric | Score |",
        "|---|---|",
    ]

    if gen_error:
        lines.append(f"| — | skipped: {gen_error} |")
    else:
        lines += [
            f"| Faithfulness | {fmt(generation.get('faithfulness', 0))} |",
            f"| Answer Relevancy | {fmt(generation.get('answer_relevancy', 0))} |",
            f"| Context Precision | {fmt(generation.get('context_precision', 0))} |",
            f"| Context Recall | {fmt(generation.get('context_recall', 0))} |",
        ]

    lines += [
        "",
        "## Notes",
        "Retrieval run against in-memory Qdrant populated with synthetic compliance chunks.",
        "Chunk IDs match data/eval/eval_set.json ground-truth labels.",
    ]

    with open(md_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return json_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-generation", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    eval_set_path = repo_root / "data" / "eval" / "eval_set.json"
    data_dir = repo_root / "data" / "processed"
    reports_dir = repo_root / "reports"
    reports_dir.mkdir(exist_ok=True)

    print("Loading eval set...")
    eval_set = load_eval_set(str(eval_set_path))
    print(f"  {len(eval_set)} queries")

    settings = Settings()

    print("Loading synthetic chunks and building in-memory index...")
    chunks = load_synthetic_chunks(str(data_dir))
    print(f"  {len(chunks)} chunks")

    vector_store = VectorStore(settings, qdrant_url=":memory:")
    vector_store.upsert(chunks)
    print("  VectorStore ready")

    print("Running retrieval evaluation...")
    retrieval_results = run_retrieval_eval(vector_store, eval_set, settings)
    print(f"  Hit Rate@5={retrieval_results['hit_rate@5']:.3f}  MRR@5={retrieval_results['mrr@5']:.3f}  nDCG@5={retrieval_results['ndcg@5']:.3f}")

    generation_results: dict = {"n_queries": len(eval_set)}
    if args.skip_generation:
        generation_results["error"] = "skipped via --skip-generation"
    else:
        print("Running generation evaluation (RAGAS)...")
        tmp_db = str(reports_dir / "eval_audit_tmp.db")
        audit_logger = AuditLogger(db_path=tmp_db)
        llm_client = get_llm_client(settings)
        rag_system = RAGSystem(settings, vector_store, llm_client, audit_logger)
        generation_results = run_generation_eval(rag_system, eval_set, settings)
        if "error" in generation_results:
            print(f"  Generation eval skipped: {generation_results['error']}")
        else:
            print(f"  Faithfulness={generation_results['faithfulness']:.3f}  AnswerRelevancy={generation_results['answer_relevancy']:.3f}")

    json_path, md_path = write_reports(retrieval_results, generation_results, str(reports_dir))
    print(f"\nReports written:")
    print(f"  {json_path}")
    print(f"  {md_path}")


if __name__ == "__main__":
    main()
