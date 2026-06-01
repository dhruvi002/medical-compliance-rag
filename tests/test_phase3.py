"""Unit tests for Phase 3: Settings, LLMClient, AuditLogger, auth, RAGSystem."""
from unittest.mock import MagicMock, patch

from medcomply.audit_logger import AuditLogger
from medcomply.auth import ROLE_DOC_CLASSES
from medcomply.llm_client import GroqClient, LLMResponse, OllamaClient
from medcomply.rag_system import RAGSystem
from medcomply.settings import Settings
from medcomply.vector_store import _rrf_merge

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def test_settings_defaults():
    s = Settings()
    assert isinstance(s.dense_model, str)
    assert isinstance(s.embedding_dim, int)
    assert isinstance(s.max_tokens, int)
    assert isinstance(s.temperature, float)
    assert s.top_k_retrieve > s.top_k_final


# ---------------------------------------------------------------------------
# OllamaClient truncation
# ---------------------------------------------------------------------------

def test_ollama_client_truncation_flag():
    fake_response = {
        "message": {"content": "some answer"},
        "done_reason": "length",
    }
    with patch("ollama.chat", return_value=fake_response):
        client = OllamaClient()
        resp = client.complete("test prompt", Settings())
    assert resp.truncated is True
    assert resp.content == "some answer"


def test_ollama_client_no_truncation():
    fake_response = {
        "message": {"content": "full answer"},
        "done_reason": "stop",
    }
    with patch("ollama.chat", return_value=fake_response):
        client = OllamaClient()
        resp = client.complete("test prompt", Settings())
    assert resp.truncated is False


# ---------------------------------------------------------------------------
# GroqClient truncation
# ---------------------------------------------------------------------------

def _make_groq_completion(finish_reason: str, content: str = "answer"):
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def test_groq_client_truncation_flag():
    completion = _make_groq_completion("length", "truncated answer")
    mock_groq_instance = MagicMock()
    mock_groq_instance.chat.completions.create.return_value = completion

    with patch("groq.Groq", return_value=mock_groq_instance):
        client = GroqClient()
        resp = client.complete("test prompt", Settings(llm_backend="groq"))
    assert resp.truncated is True
    assert resp.content == "truncated answer"


def test_groq_client_no_truncation():
    completion = _make_groq_completion("stop", "full answer")
    mock_groq_instance = MagicMock()
    mock_groq_instance.chat.completions.create.return_value = completion

    with patch("groq.Groq", return_value=mock_groq_instance):
        client = GroqClient()
        resp = client.complete("test prompt", Settings(llm_backend="groq"))
    assert resp.truncated is False


# ---------------------------------------------------------------------------
# Settings drive Ollama params
# ---------------------------------------------------------------------------

def test_settings_drives_ollama_params():
    settings = Settings(max_tokens=256, temperature=0.5, top_p=0.8)
    fake_response = {
        "message": {"content": "ok"},
        "done_reason": "stop",
    }
    with patch("ollama.chat", return_value=fake_response) as mock_chat:
        OllamaClient().complete("prompt", settings)
    call_kwargs = mock_chat.call_args
    options = call_kwargs.kwargs.get("options") or call_kwargs[1].get("options") or call_kwargs[0][2]
    assert options["num_predict"] == 256
    assert options["temperature"] == 0.5


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------

def _make_logger(tmp_path) -> AuditLogger:
    return AuditLogger(db_path=str(tmp_path / "audit.db"))


def test_audit_ids_unique(tmp_path):
    logger = _make_logger(tmp_path)
    ids = [
        logger.log("user", "staff", f"q{i}", "a", [], False, 10.0)
        for i in range(100)
    ]
    assert len(set(ids)) == 100


def test_audit_persists_across_instances(tmp_path):
    db = str(tmp_path / "audit.db")
    AuditLogger(db_path=db).log("alice", "admin", "query1", "ans", [], False, 5.0)
    rows = AuditLogger(db_path=db).recent(1)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "alice"


def test_audit_sqlite_not_jsonl(tmp_path):
    logger = _make_logger(tmp_path)
    assert logger._db_path.endswith(".db")
    assert not logger._db_path.endswith(".jsonl")


def test_audit_stats(tmp_path):
    logger = _make_logger(tmp_path)
    logger.log("alice", "admin", "q1", "a", [], False, 5.0)
    logger.log("bob", "staff", "q2", "a", [], False, 5.0)
    logger.log("alice", "admin", "q3", "a", [], False, 5.0)
    s = logger.stats()
    assert s["total_queries"] == 3
    assert s["unique_users"] == 2


# ---------------------------------------------------------------------------
# ROLE_DOC_CLASSES
# ---------------------------------------------------------------------------

def test_role_doc_classes_coverage():
    valid_roles = {"admin", "manager", "staff"}
    assert set(ROLE_DOC_CLASSES.keys()) <= valid_roles
    admin_docs = set(ROLE_DOC_CLASSES["admin"])
    for role, docs in ROLE_DOC_CLASSES.items():
        if role != "admin":
            assert set(docs) <= admin_docs, f"{role} has docs not in admin"


# ---------------------------------------------------------------------------
# RAGSystem logs authenticated identity
# ---------------------------------------------------------------------------

def test_rag_system_logs_authenticated_identity(tmp_path):
    settings = Settings()

    mock_vs = MagicMock()
    mock_vs.query.return_value = [
        {"chunk_id": "c1", "source_file": "doc.pdf", "content": "content"}
    ]

    mock_llm = MagicMock()
    mock_llm.complete.return_value = LLMResponse(
        content="answer", truncated=False, model="llama3.1:8b", latency_ms=100.0
    )

    mock_audit = MagicMock()

    rag = RAGSystem(
        settings=settings,
        vector_store=mock_vs,
        llm_client=mock_llm,
        audit_logger=mock_audit,
    )
    rag.query("test question", user_id="alice", role="staff")

    mock_audit.log.assert_called_once()
    call_kwargs = mock_audit.log.call_args
    assert call_kwargs.kwargs.get("user_id") == "alice" or call_kwargs[1].get("user_id") == "alice" or call_kwargs[0][0] == "alice"


# ---------------------------------------------------------------------------
# RRF merge
# ---------------------------------------------------------------------------

def test_rrf_merge():
    dense = [
        {"id": "a", "content": "A"},
        {"id": "b", "content": "B"},
        {"id": "c", "content": "C"},
    ]
    sparse = [
        {"id": "b", "content": "B"},
        {"id": "a", "content": "A"},
        {"id": "d", "content": "D"},
    ]
    merged = _rrf_merge(dense, sparse, k=60)
    ids = [h["id"] for h in merged]

    # "a" and "b" appear in both lists so they accumulate more RRF score
    assert ids[0] in {"a", "b"}
    assert ids[1] in {"a", "b"}
    # "c" and "d" appear in only one list each
    assert set(ids) == {"a", "b", "c", "d"}
