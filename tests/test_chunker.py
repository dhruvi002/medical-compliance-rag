"""Unit tests for TokenChunker — includes finding #7 regression."""
import random

import tiktoken

from medcomply.chunker import TokenChunker

_ENC = tiktoken.get_encoding("cl100k_base")


def _make_text(n_tokens: int) -> str:
    """Return text of approximately n_tokens tokens with sentence boundaries."""
    sentences = []
    total = 0
    i = 0
    while total < n_tokens:
        s = f"Regulation {i} requires that all personnel maintain proper documentation."
        t = len(_ENC.encode(s + " "))
        sentences.append(s)
        total += t
        i += 1
    return " ".join(sentences)


def test_empty_input():
    chunker = TokenChunker(chunk_size=500, chunk_overlap=50)
    assert chunker.chunk_text("", {}) == []


def test_single_short_paragraph():
    chunker = TokenChunker(chunk_size=500, chunk_overlap=50)
    text = "This is a short paragraph about medical compliance."
    result = chunker.chunk_text(text, {})
    assert len(result) == 1
    assert result[0]["content"] == text


def test_oversized_paragraph():
    chunker = TokenChunker(chunk_size=500, chunk_overlap=50)
    # Single paragraph (no double-newlines) longer than chunk_size
    text = _make_text(700)
    assert "\n\n" not in text
    result = chunker.chunk_text(text, {})
    assert len(result) > 1
    for chunk in result:
        assert chunker.count_tokens(chunk["content"]) <= chunker.chunk_size


def test_chunk_size_invariant():
    chunker = TokenChunker(chunk_size=200, chunk_overlap=30)
    rng = random.Random(42)
    for _ in range(50):
        n = rng.randint(100, 1500)
        text = _make_text(n)
        for chunk in chunker.chunk_text(text, {}):
            assert chunker.count_tokens(chunk["content"]) <= chunker.chunk_size


def test_overlap_token_budget():
    chunker = TokenChunker(chunk_size=100, chunk_overlap=20)
    text = _make_text(350)
    chunks = chunker.chunk_text(text, {})
    assert len(chunks) >= 2

    for i in range(len(chunks) - 1):
        units_i = chunks[i]["content"].split("\n\n")
        units_next = chunks[i + 1]["content"].split("\n\n")
        # Find longest suffix of units_i that equals a prefix of units_next
        shared = 0
        for k in range(1, min(len(units_i), len(units_next)) + 1):
            if units_i[-k:] == units_next[:k]:
                shared = k
        if shared:
            overlap_text = "\n\n".join(units_i[-shared:])
            # Allow a tolerance of 5 tokens for boundary edge cases
            assert chunker.count_tokens(overlap_text) <= chunker.chunk_overlap + 5


def test_finding_7_regression():
    # Finding #7: the old DocumentChunker had a control-flow bug in chunk_text.
    # When an oversized paragraph was sentence-split, a bare `continue` (line 79)
    # skipped the paragraph-level overlap logic entirely. Leftover sentences
    # remained in current_chunk, and the next paragraph accumulated into them
    # without a token-count check. Additionally, overlap kept a full paragraph
    # (arbitrary size) rather than a fixed token budget, so chunk 2 could exceed
    # chunk_size when a large overlap paragraph was prepended.
    # TokenChunker fixes this via _get_units (recursive splitter) and a
    # token-budget-bounded overlap window; overlap is dropped entirely if it plus
    # the incoming unit would exceed chunk_size.
    chunker = TokenChunker(chunk_size=500, chunk_overlap=50)

    large_para = _make_text(600)
    normal_para_1 = _make_text(200)
    normal_para_2 = _make_text(200)
    text = f"{large_para}\n\n{normal_para_1}\n\n{normal_para_2}"

    chunks = chunker.chunk_text(text, {})
    assert chunks, "expected at least one chunk"
    for chunk in chunks:
        token_count = chunker.count_tokens(chunk["content"])
        assert token_count <= chunker.chunk_size, (
            f"chunk exceeds chunk_size={chunker.chunk_size}: got {token_count} tokens"
        )


def test_metadata_preserved():
    chunker = TokenChunker(chunk_size=100, chunk_overlap=10)
    meta = {"doc_id": "abc", "source": "hipaa"}
    text = _make_text(350)
    chunks = chunker.chunk_text(text, meta)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["metadata"]["doc_id"] == "abc"
    # Mutating one chunk's metadata must not affect the others
    chunks[0]["metadata"]["doc_id"] = "MUTATED"
    for chunk in chunks[1:]:
        assert chunk["metadata"]["doc_id"] == "abc"


def test_unsplittable_unit_emitted_as_chunk():
    # chunk_size=3 forces _get_units to exhaust all splitters and return a large unit as-is
    # (line 46 in chunker.py). chunk_text then emits it via the defensive path.
    chunker = TokenChunker(chunk_size=3, chunk_overlap=1)
    # "hello world hello world" has no \n\n, \n, or sentence boundaries and is > 3 tokens
    text = "hello world hello world"
    assert chunker.count_tokens(text) > 3
    result = chunker.chunk_text(text, {})
    assert len(result) >= 1
    assert result[0]["content"] == text


def test_overlap_dropped_when_too_large():
    # With high overlap relative to chunk_size, overlap + incoming unit can exceed chunk_size.
    # The chunker drops the overlap entirely in that case (lines 85-87).
    chunker = TokenChunker(chunk_size=30, chunk_overlap=25)
    # Generate text whose units are ~20 tokens each: overlap (≤25) + next unit (20) > 30
    text = _make_text(120)
    chunks = chunker.chunk_text(text, {})
    for chunk in chunks:
        assert chunker.count_tokens(chunk["content"]) <= chunker.chunk_size


def test_chunk_ids_unique():
    chunker = TokenChunker(chunk_size=200, chunk_overlap=30)
    documents = [
        {"content": _make_text(600), "filename": f"doc_{i}"}
        for i in range(5)
    ]
    all_chunks = chunker.process_documents(documents)
    ids = [c["metadata"]["chunk_id"] for c in all_chunks]
    assert len(ids) == len(set(ids))
