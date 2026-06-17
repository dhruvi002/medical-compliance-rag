"""Phase 9 tests: close the 6 remaining uncovered lines to reach 100% coverage."""
from unittest.mock import MagicMock, patch

from medcomply.chunker import TokenChunker
from medcomply.eval_generation import _build_judge_llm, run_generation_eval
from medcomply.settings import Settings

# ---------------------------------------------------------------------------
# chunker.py lines 64-66 — if-buf branch in oversized-unit guard
# ---------------------------------------------------------------------------


def test_chunker_oversized_unit_flushes_buf():
    """Lines 64-66: when an oversized unit follows buffered content, the buffer
    is flushed as its own chunk before the oversized unit is emitted."""
    # chunk_size=10: "Normal sentence." fits in buf (~3 tokens).
    # The long word run cannot be split at any boundary and exceeds chunk_size,
    # triggering the if-buf flush on lines 64-66.
    chunker = TokenChunker(chunk_size=10, chunk_overlap=0)
    text = "Normal sentence.\n\n" + ("word " * 20).strip()
    chunks = chunker.chunk_text(text, {"source": "test"})

    assert len(chunks) >= 2
    assert "Normal sentence" in chunks[0]["content"]


# ---------------------------------------------------------------------------
# eval_generation.py line 31 — run_generation_eval returns early when llm is None
# (reached only after the ragas import block succeeds)
# ---------------------------------------------------------------------------


def test_run_generation_eval_no_llm_after_ragas_import():
    """Line 31: returns error dict when _build_judge_llm returns None, but only
    after the ragas import try-block at lines 18-27 succeeds."""
    mock_ragas = MagicMock()
    mock_ragas_metrics = MagicMock()
    eval_set = [{"query": "q", "relevant_chunk_ids": ["c1"], "reference_answer": "ans"}]

    with (
        patch.dict("sys.modules", {"ragas": mock_ragas, "ragas.metrics": mock_ragas_metrics}),
        patch("medcomply.eval_generation._build_judge_llm", return_value=None),
    ):
        result = run_generation_eval(MagicMock(), eval_set, Settings())

    assert "error" in result
    assert result["n_queries"] == 1


# ---------------------------------------------------------------------------
# eval_generation.py lines 84-86 — Ollama success path in _build_judge_llm
# ---------------------------------------------------------------------------


def test_build_judge_llm_ollama_success(monkeypatch):
    """Lines 84-86: Ollama branch succeeds when GROQ_API_KEY is absent and
    langchain_community.chat_models is importable."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    mock_lc = MagicMock()
    mock_ragas_llms = MagicMock()

    with patch.dict("sys.modules", {
        "langchain_community": MagicMock(),
        "langchain_community.chat_models": mock_lc,
        "ragas.llms": mock_ragas_llms,
    }):
        result = _build_judge_llm(Settings())

    assert result is not None
