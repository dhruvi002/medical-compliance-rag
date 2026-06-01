"""
Ingest synthetic compliance docs into a Qdrant instance.

Usage:
    QDRANT_URL=https://... QDRANT_API_KEY=... python scripts/ingest.py

Defaults to in-memory Qdrant if QDRANT_URL is not set (useful for smoke-testing).
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medcomply.settings import Settings
from medcomply.vector_store import VectorStore

_DOMAIN_FILES = {
    "hipaa": "synthetic_hipaa.json",
    "osha": "synthetic_osha.json",
    "infection_control": "synthetic_infection_control.json",
    "medical_waste": "synthetic_medical_waste.json",
    "documentation_training": "synthetic_documentation_training.json",
    "edge_cases": "synthetic_edge_cases.json",
}


def load_chunks(data_dir: Path) -> list[dict]:
    chunks = []
    for domain, fname in _DOMAIN_FILES.items():
        fpath = data_dir / fname
        if not fpath.exists():
            print(f"[warn] {fpath} not found, skipping")
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


def main():
    qdrant_url = os.environ.get("QDRANT_URL", ":memory:")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY", "")

    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data" / "processed"

    settings = Settings(qdrant_url=qdrant_url)

    print(f"Loading chunks from {data_dir} ...")
    chunks = load_chunks(data_dir)
    print(f"  {len(chunks)} chunks loaded")

    print(f"Connecting to Qdrant at {qdrant_url} ...")
    vector_store = VectorStore(settings, qdrant_url=qdrant_url, qdrant_api_key=qdrant_api_key)

    print("Upserting chunks ...")
    vector_store.upsert(chunks)
    print("Done.")


if __name__ == "__main__":
    main()
