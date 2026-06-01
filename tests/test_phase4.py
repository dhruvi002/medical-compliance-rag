"""Unit tests for Phase 4: retrieval metrics, skill-gap NLP, eval set schema."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from medcomply.eval_retrieval import hit_rate_at_k, mrr_at_k, ndcg_at_k
from medcomply.settings import Settings

EVAL_SET_PATH = Path(__file__).resolve().parent.parent / "data" / "eval" / "eval_set.json"


# ---------------------------------------------------------------------------
# hit_rate_at_k
# ---------------------------------------------------------------------------


def test_hit_rate_perfect():
    results = [["a", "b", "c"], ["x", "y", "z"]]
    relevant = [["a"], ["x"]]
    assert hit_rate_at_k(results, relevant, k=5) == 1.0


def test_hit_rate_zero():
    results = [["a", "b", "c"], ["x", "y", "z"]]
    relevant = [["d"], ["w"]]
    assert hit_rate_at_k(results, relevant, k=5) == 0.0


# ---------------------------------------------------------------------------
# mrr_at_k
# ---------------------------------------------------------------------------


def test_mrr_first_hit():
    results = [["a", "b", "c"]]
    relevant = [["a"]]
    assert mrr_at_k(results, relevant, k=5) == pytest.approx(1.0)


def test_mrr_second_hit():
    results = [["a", "b", "c"]]
    relevant = [["b"]]
    assert mrr_at_k(results, relevant, k=5) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# ndcg_at_k
# ---------------------------------------------------------------------------


def test_ndcg_perfect():
    results = [["a", "b", "c"]]
    relevant = [["a"]]
    assert ndcg_at_k(results, relevant, k=5) == pytest.approx(1.0)


def test_ndcg_worst():
    # Relevant chunk is last in a list of 5; nDCG should be well below ideal
    results = [["x", "y", "z", "w", "a"]]
    relevant = [["a"]]
    score = ndcg_at_k(results, relevant, k=5)
    assert score < 0.5


# ---------------------------------------------------------------------------
# eval_generation — error path (no LLM available)
# ---------------------------------------------------------------------------


def test_generation_eval_no_llm(monkeypatch, tmp_path):
    """run_generation_eval returns an error dict when no LLM judge is available."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    from medcomply.eval_generation import run_generation_eval

    mock_rag = MagicMock()
    mock_rag.query.return_value = {
        "answer": "test answer",
        "sources": [],
        "truncated": False,
        "latency_ms": 10.0,
    }

    eval_set = [
        {
            "query_id": "q001",
            "query": "What is HIPAA?",
            "relevant_chunk_ids": ["hipaa_000"],
            "reference_answer": "HIPAA is a privacy law.",
        }
    ]

    # Patch _build_judge_llm to return None (simulates no API key and no Ollama)
    with patch("medcomply.eval_generation._build_judge_llm", return_value=None):
        result = run_generation_eval(mock_rag, eval_set, Settings())

    assert "error" in result
    assert result["n_queries"] == 1


# ---------------------------------------------------------------------------
# SkillGapAnalyzer — unit tests with mocked embeddings
# ---------------------------------------------------------------------------


def _make_analyzer_with_mock_model(mock_encode):
    """Patch SentenceTransformer so no model is downloaded."""
    from medcomply.skill_gap_analyzer import SkillGapAnalyzer

    with patch("medcomply.skill_gap_analyzer.SentenceTransformer") as MockST:
        instance = MagicMock()
        instance.encode.side_effect = mock_encode
        MockST.return_value = instance
        analyzer = SkillGapAnalyzer(Settings())
    analyzer._model = instance
    return analyzer


def test_analyze_employee_weak_categories():
    import numpy as np

    # category A: employee vec orthogonal to canonical → low similarity
    # category B: employee vec identical to canonical → high similarity
    a_emp = np.array([1.0, 0.0])
    a_can = np.array([0.0, 1.0])
    b_emp = np.array([1.0, 0.0])
    b_can = np.array([1.0, 0.0])

    responses = [
        {"question": "q1", "canonical_answer": "c1", "employee_answer": "e1", "category": "A"},
        {"question": "q2", "canonical_answer": "c2", "employee_answer": "e2", "category": "B"},
    ]

    # encode is called once with all texts: [e1, c1, e2, c2]
    def mock_encode(texts, show_progress_bar=False):
        mapping = {"e1": a_emp, "c1": a_can, "e2": b_emp, "c2": b_can}
        return np.array([mapping[t] for t in texts])

    analyzer = _make_analyzer_with_mock_model(mock_encode)
    result = analyzer.analyze_employee("emp1", responses)

    assert "A" in result["weak_categories"]
    assert "B" not in result["weak_categories"]


def test_cohort_themes_empty_when_no_weaknesses():
    import numpy as np

    analyses = [
        {"employee_id": "e1", "weak_categories": []},
        {"employee_id": "e2", "weak_categories": []},
        {"employee_id": "e3", "weak_categories": []},
    ]

    def mock_encode(texts, show_progress_bar=False):
        return np.zeros((len(texts), 2))

    analyzer = _make_analyzer_with_mock_model(mock_encode)
    assert analyzer.cohort_themes(analyses) == []


# ---------------------------------------------------------------------------
# SkillGapAnalyzer — slow tests (require model download)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_score_answer_identical():
    from medcomply.skill_gap_analyzer import SkillGapAnalyzer

    analyzer = SkillGapAnalyzer(Settings())
    text = "The HIPAA minimum necessary standard limits PHI disclosure."
    score = analyzer.score_answer(text, text)
    assert score > 0.95


@pytest.mark.slow
def test_score_answer_unrelated():
    from medcomply.skill_gap_analyzer import SkillGapAnalyzer

    analyzer = SkillGapAnalyzer(Settings())
    score = analyzer.score_answer(
        "HIPAA privacy rule protects patient health information",
        "Sharps disposal procedure: use puncture-resistant containers",
    )
    assert score < 0.5


# ---------------------------------------------------------------------------
# Eval set schema validation
# ---------------------------------------------------------------------------


def test_eval_set_schema():
    assert EVAL_SET_PATH.exists(), f"eval_set.json not found at {EVAL_SET_PATH}"
    with open(EVAL_SET_PATH) as f:
        raw = json.load(f)
    entries = raw["entries"] if isinstance(raw, dict) else raw
    assert len(entries) >= 50, f"Expected ≥50 entries, got {len(entries)}"
    required = {"query_id", "query", "relevant_chunk_ids", "reference_answer"}
    for entry in entries:
        missing = required - set(entry.keys())
        assert not missing, f"{entry.get('query_id', '?')} missing fields: {missing}"
        assert isinstance(entry["relevant_chunk_ids"], list)
        assert len(entry["relevant_chunk_ids"]) >= 1
