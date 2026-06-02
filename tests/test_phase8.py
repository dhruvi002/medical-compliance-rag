"""Phase 8 tests: coverage for eval_retrieval, eval_generation, skill_gap_analyzer, llm_client, auth."""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import yaml

from medcomply.eval_generation import _build_judge_llm, run_generation_eval
from medcomply.eval_retrieval import hit_rate_at_k, mrr_at_k, ndcg_at_k, run_retrieval_eval
from medcomply.llm_client import GroqClient, OllamaClient, get_llm_client
from medcomply.settings import Settings

# ---------------------------------------------------------------------------
# eval_retrieval.py — empty-results guards and run_retrieval_eval orchestration
# ---------------------------------------------------------------------------


def test_hit_rate_empty_results():
    assert hit_rate_at_k([], [], k=5) == 0.0


def test_mrr_empty_results():
    assert mrr_at_k([], [], k=5) == 0.0


def test_ndcg_empty_results():
    assert ndcg_at_k([], [], k=5) == 0.0


def test_ndcg_empty_relevant_set():
    # ideal DCG = 0.0 → continue branch
    assert ndcg_at_k([["a", "b"]], [[]], k=5) == 0.0


def test_run_retrieval_eval():
    mock_vs = MagicMock()
    mock_vs.query.return_value = [{"chunk_id": "hipaa_000"}]
    eval_set = [{"query": "What is HIPAA?", "relevant_chunk_ids": ["hipaa_000"]}]
    result = run_retrieval_eval(mock_vs, eval_set, Settings())
    assert result["hit_rate@5"] == 1.0
    assert result["n_queries"] == 1


# ---------------------------------------------------------------------------
# skill_gap_analyzer.py — empty-responses guard and cohort_themes clustering
# ---------------------------------------------------------------------------


def _make_analyzer_with_mock_model(mock_encode):
    from medcomply.skill_gap_analyzer import SkillGapAnalyzer

    with patch("medcomply.skill_gap_analyzer.SentenceTransformer") as MockST:
        instance = MagicMock()
        instance.encode.side_effect = mock_encode
        MockST.return_value = instance
        analyzer = SkillGapAnalyzer(Settings())
    analyzer._model = instance
    return analyzer


def test_analyze_employee_empty_responses():
    def mock_encode(texts, show_progress_bar=False):
        return np.zeros((len(texts), 2))

    analyzer = _make_analyzer_with_mock_model(mock_encode)
    result = analyzer.analyze_employee("emp1", [])
    assert result == {
        "employee_id": "emp1",
        "overall_score": 0.0,
        "category_scores": {},
        "weak_categories": [],
    }


def test_cohort_themes_clustering():
    analyses = [
        {"employee_id": "e1", "weak_categories": ["hipaa"]},
        {"employee_id": "e2", "weak_categories": ["osha"]},
        {"employee_id": "e3", "weak_categories": ["hipaa"]},
    ]

    rng = np.random.default_rng(seed=0)

    def mock_encode(texts, show_progress_bar=False):
        return rng.random((len(texts), 4)).astype(np.float32)

    analyzer = _make_analyzer_with_mock_model(mock_encode)
    themes = analyzer.cohort_themes(analyses)
    assert isinstance(themes, list)
    assert len(themes) <= 3


# ---------------------------------------------------------------------------
# llm_client.py — get_llm_client branch dispatch
# ---------------------------------------------------------------------------


def test_get_llm_client_groq():
    assert isinstance(get_llm_client(Settings(llm_backend="groq")), GroqClient)


def test_get_llm_client_ollama():
    assert isinstance(get_llm_client(Settings(llm_backend="ollama")), OllamaClient)


# ---------------------------------------------------------------------------
# auth.py — load_authenticator happy path (lines 23–26)
# ---------------------------------------------------------------------------


def test_load_authenticator_happy_path(monkeypatch, tmp_path):
    import medcomply.auth as auth_mod

    cfg = {
        "credentials": {"usernames": {}},
        "cookie": {"name": "medcomply", "key": "secret", "expiry_days": 1},
    }
    cfg_file = tmp_path / "auth.yaml"
    cfg_file.write_text(yaml.dump(cfg))

    monkeypatch.setattr(auth_mod, "_CONFIG_PATH", cfg_file)
    with patch("streamlit_authenticator.Authenticate") as mock_auth:
        auth_mod.load_authenticator()
        mock_auth.assert_called_once()


# ---------------------------------------------------------------------------
# eval_generation.py — _build_judge_llm branches and run_generation_eval happy path
# ---------------------------------------------------------------------------


def test_build_judge_llm_groq_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    mock_lgc = MagicMock()
    mock_ragas_llms = MagicMock()
    with patch.dict("sys.modules", {"langchain_groq": mock_lgc, "ragas.llms": mock_ragas_llms}):
        result = _build_judge_llm(Settings())
    assert result is not None


def test_build_judge_llm_all_imports_fail(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch.dict("sys.modules", {
        "langchain_groq": None,
        "langchain_community.chat_models": None,
    }):
        result = _build_judge_llm(Settings())
    assert result is None


def test_run_generation_eval_happy_path():
    mock_rag = MagicMock()
    mock_rag.query.return_value = {
        "answer": "PHI is protected.",
        "contexts": ["context"],
        "sources": [],
        "truncated": False,
        "latency_ms": 10.0,
    }
    eval_set = [
        {
            "query": "What is HIPAA?",
            "relevant_chunk_ids": ["hipaa_000"],
            "reference_answer": "HIPAA protects PHI.",
        }
    ]
    mock_eval_result = {
        "faithfulness": 0.9,
        "answer_relevancy": 0.85,
        "context_precision": 0.8,
        "context_recall": 0.75,
    }

    # ragas may not be importable in this env due to optional deps, so mock the
    # entire ragas namespace that run_generation_eval imports inside its try block.
    mock_ragas = MagicMock()
    mock_ragas.evaluate.return_value = mock_eval_result
    mock_ragas_metrics = MagicMock()

    with (
        patch("medcomply.eval_generation._build_judge_llm", return_value=MagicMock()),
        patch.dict("sys.modules", {"ragas": mock_ragas, "ragas.metrics": mock_ragas_metrics}),
    ):
        result = run_generation_eval(mock_rag, eval_set, Settings())

    assert result["faithfulness"] == pytest.approx(0.9)
    assert result["n_queries"] == 1
