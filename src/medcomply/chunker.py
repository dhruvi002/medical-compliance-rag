import json
import os
import re
from typing import Dict, List

import tiktoken


class TokenChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _get_units(self, text: str) -> List[str]:
        """Recursively split text into units that each fit within chunk_size.

        Split order: double-newline → single-newline → sentence boundary.
        If no splitter reduces the text, the unit is returned as-is.
        """
        text = text.strip()
        if not text:
            return []
        if self.count_tokens(text) <= self.chunk_size:
            return [text]

        for sep in ["\n\n", "\n"]:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) > 1:
                result: List[str] = []
                for p in parts:
                    result.extend(self._get_units(p))
                return result

        parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(parts) > 1:
            result = []
            for p in parts:
                result.extend(self._get_units(p))
            return result

        # Cannot split further — return as-is even if oversized
        return [text]

    def chunk_text(self, text: str, metadata: dict) -> List[Dict]:
        units = self._get_units(text)
        if not units:
            return []

        chunks = []
        buf: List[str] = []
        buf_tokens = 0

        for unit in units:
            unit_tokens = self.count_tokens(unit)

            # Defensive: a single unsplittable unit larger than chunk_size
            # is emitted as its own chunk without violating the accumulation logic.
            if unit_tokens > self.chunk_size:
                if buf:
                    chunks.append({"content": "\n\n".join(buf), "metadata": metadata.copy()})
                    buf = []
                    buf_tokens = 0
                chunks.append({"content": unit, "metadata": metadata.copy()})
                continue

            if buf and buf_tokens + unit_tokens > self.chunk_size:
                chunks.append({"content": "\n\n".join(buf), "metadata": metadata.copy()})

                # Carry overlap: walk back through buf, collecting units up to chunk_overlap tokens.
                overlap: List[str] = []
                overlap_tokens = 0
                for u in reversed(buf):
                    t = self.count_tokens(u)
                    if overlap_tokens + t <= self.chunk_overlap:
                        overlap.insert(0, u)
                        overlap_tokens += t
                    else:
                        break

                # Drop overlap entirely if it plus the incoming unit already exceeds chunk_size.
                if overlap_tokens + unit_tokens > self.chunk_size:
                    overlap = []
                    overlap_tokens = 0

                buf = overlap
                buf_tokens = overlap_tokens

            buf.append(unit)
            buf_tokens += unit_tokens

        if buf:
            chunks.append({"content": "\n\n".join(buf), "metadata": metadata.copy()})

        return chunks

    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        all_chunks: List[Dict] = []
        for i, doc in enumerate(documents):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            metadata["doc_index"] = i
            metadata["source_file"] = doc.get("filename") or doc.get("title", f"doc_{i}")
            chunks = self.chunk_text(content, metadata)
            for j, chunk in enumerate(chunks):
                chunk["metadata"]["chunk_index"] = j
                chunk["metadata"]["total_chunks"] = len(chunks)
                chunk["metadata"]["chunk_id"] = f"{metadata['source_file']}_chunk_{j}"
            all_chunks.extend(chunks)
            if (i + 1) % 10 == 0:  # pragma: no cover
                print(f"Processed {i + 1}/{len(documents)} documents...")
        return all_chunks


# Backward-compatibility alias
DocumentChunker = TokenChunker


class SemanticChunker:  # pragma: no cover
    # Uses all-MiniLM-L6-v2 rather than bge-base-en-v1.5 for chunking speed;
    # bge-base-en-v1.5 is reserved for retrieval embeddings.
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.3,
        chunk_size: int = 500,
    ):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.chunk_size = chunk_size
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _split_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def chunk_text(self, text: str, metadata: dict) -> List[Dict]:
        import numpy as np

        sentences = self._split_sentences(text)
        if not sentences:
            return []
        if len(sentences) == 1:
            return [{"content": sentences[0], "metadata": metadata.copy()}]

        embeddings = self.model.encode(sentences, normalize_embeddings=True)

        # Split where cosine distance between adjacent sentence embeddings exceeds threshold.
        split_at: List[int] = []
        for i in range(len(sentences) - 1):
            dist = 1.0 - float(np.dot(embeddings[i], embeddings[i + 1]))
            if dist > self.threshold:
                split_at.append(i + 1)

        groups: List[List[str]] = []
        prev = 0
        for idx in split_at:
            groups.append(sentences[prev:idx])
            prev = idx
        groups.append(sentences[prev:])

        return [
            {"content": " ".join(g), "metadata": metadata.copy()}
            for g in groups
            if g
        ]

    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        all_chunks: List[Dict] = []
        for i, doc in enumerate(documents):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            metadata["doc_index"] = i
            metadata["source_file"] = doc.get("filename") or doc.get("title", f"doc_{i}")
            chunks = self.chunk_text(content, metadata)
            for j, chunk in enumerate(chunks):
                chunk["metadata"]["chunk_index"] = j
                chunk["metadata"]["total_chunks"] = len(chunks)
                chunk["metadata"]["chunk_id"] = f"{metadata['source_file']}_chunk_{j}"
            all_chunks.extend(chunks)
        return all_chunks


def main():  # pragma: no cover
    script_dir = os.path.dirname(os.path.abspath(__file__))

    pdf_file = os.path.join(script_dir, "../data/processed/documents.json")
    with open(pdf_file, encoding="utf-8") as f:
        pdf_docs = json.load(f)

    wiki_file = os.path.join(script_dir, "../data/processed/wikipedia_compliance.json")
    with open(wiki_file, encoding="utf-8") as f:
        wiki_docs = json.load(f)

    all_docs = pdf_docs + wiki_docs
    print(f"Loaded {len(all_docs)} documents")

    chunker = TokenChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.process_documents(all_docs)

    print(f"Total chunks created: {len(chunks)}")
    if chunks:
        print(f"Sample chunk_id: {chunks[0]['metadata']['chunk_id']}")
        print(f"Token count: {chunker.count_tokens(chunks[0]['content'])}")

    output_file = os.path.join(script_dir, "../data/processed/chunks.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"Saved chunks to: {output_file}")


if __name__ == "__main__":  # pragma: no cover
    main()
