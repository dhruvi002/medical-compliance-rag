"""Phase 7 tests: auth.py and vector_store.py coverage."""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import yaml

from medcomply.settings import Settings
from medcomply.vector_store import _rrf_merge

# ---------------------------------------------------------------------------
# auth.py
# ---------------------------------------------------------------------------


def test_get_current_user_not_authenticated():
    import medcomply.auth as auth_mod

    assert auth_mod.get_current_user(False, "alice") is None


def test_get_current_user_no_config_file(monkeypatch, tmp_path):
    import medcomply.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_CONFIG_PATH", tmp_path / "no.yaml")
    assert auth_mod.get_current_user(True, "alice") is None


def test_get_current_user_unknown_username(monkeypatch, tmp_path):
    import medcomply.auth as auth_mod

    cfg_file = tmp_path / "auth.yaml"
    cfg_file.write_text(yaml.dump({"credentials": {"usernames": {}}}))
    monkeypatch.setattr(auth_mod, "_CONFIG_PATH", cfg_file)
    assert auth_mod.get_current_user(True, "ghost") is None


def test_get_current_user_returns_username_and_role(monkeypatch, tmp_path):
    import medcomply.auth as auth_mod

    cfg = {
        "credentials": {
            "usernames": {
                "alice": {"name": "Alice", "password": "hashed", "role": "admin"}
            }
        }
    }
    cfg_file = tmp_path / "auth.yaml"
    cfg_file.write_text(yaml.dump(cfg))
    monkeypatch.setattr(auth_mod, "_CONFIG_PATH", cfg_file)
    result = auth_mod.get_current_user(True, "alice")
    assert result == ("alice", "admin")


def test_get_current_user_defaults_to_staff_role(monkeypatch, tmp_path):
    import medcomply.auth as auth_mod

    # user entry with no 'role' key — should default to "staff"
    cfg = {
        "credentials": {
            "usernames": {"bob": {"name": "Bob", "password": "hashed"}}
        }
    }
    cfg_file = tmp_path / "auth.yaml"
    cfg_file.write_text(yaml.dump(cfg))
    monkeypatch.setattr(auth_mod, "_CONFIG_PATH", cfg_file)
    result = auth_mod.get_current_user(True, "bob")
    assert result == ("bob", "staff")


def test_load_authenticator_raises_when_config_missing(monkeypatch, tmp_path):
    import medcomply.auth as auth_mod

    monkeypatch.setattr(auth_mod, "_CONFIG_PATH", tmp_path / "missing.yaml")
    with pytest.raises(FileNotFoundError):
        auth_mod.load_authenticator()


# ---------------------------------------------------------------------------
# vector_store.py — VectorStore (mocked ML deps)
# ---------------------------------------------------------------------------


@pytest.fixture
def vs_settings():
    return Settings()


def _build_vs(settings):
    """Instantiate VectorStore with all heavy ML deps mocked."""
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []
    mock_dense = MagicMock()
    mock_sparse = MagicMock()
    mock_reranker = MagicMock()

    with (
        patch("qdrant_client.QdrantClient", return_value=mock_client),
        patch("sentence_transformers.SentenceTransformer", return_value=mock_dense),
        patch("sentence_transformers.CrossEncoder", return_value=mock_reranker),
        patch("fastembed.SparseTextEmbedding", return_value=mock_sparse),
    ):
        from medcomply.vector_store import VectorStore

        vs = VectorStore(settings)

    return vs, mock_client, mock_dense, mock_sparse, mock_reranker


def test_vector_store_creates_collection_when_absent(vs_settings):
    vs, mock_client, *_ = _build_vs(vs_settings)
    mock_client.create_collection.assert_called_once()
    call_kwargs = mock_client.create_collection.call_args
    assert (
        call_kwargs.kwargs.get("collection_name") == vs_settings.collection_name
        or call_kwargs[1].get("collection_name") == vs_settings.collection_name
        or call_kwargs[0][0] == vs_settings.collection_name
    )


def test_vector_store_skips_collection_when_present(vs_settings):
    mock_client = MagicMock()
    existing = MagicMock()
    existing.name = vs_settings.collection_name
    mock_client.get_collections.return_value.collections = [existing]

    with (
        patch("qdrant_client.QdrantClient", return_value=mock_client),
        patch("sentence_transformers.SentenceTransformer", return_value=MagicMock()),
        patch("sentence_transformers.CrossEncoder", return_value=MagicMock()),
        patch("fastembed.SparseTextEmbedding", return_value=MagicMock()),
    ):
        from medcomply.vector_store import VectorStore

        VectorStore(vs_settings)

    mock_client.create_collection.assert_not_called()


def _mock_sparse_vec():
    sv = MagicMock()
    sv.indices.tolist.return_value = [0, 1, 2]
    sv.values.tolist.return_value = [0.5, 0.3, 0.1]
    return sv


def test_vector_store_upsert_calls_client(vs_settings):
    vs, mock_client, mock_dense, mock_sparse, _ = _build_vs(vs_settings)

    mock_dense.encode.return_value = np.zeros((1, 768))
    mock_sparse.embed.return_value = [_mock_sparse_vec()]

    chunks = [
        {
            "content": "HIPAA requires PHI protection.",
            "chunk_id": "hipaa_001",
            "source_file": "hipaa.json",
        }
    ]
    vs.upsert(chunks)

    mock_client.upsert.assert_called_once()
    call_kwargs = mock_client.upsert.call_args
    used_collection = (
        call_kwargs.kwargs.get("collection_name")
        or call_kwargs[1].get("collection_name")
        or call_kwargs[0][0]
    )
    assert used_collection == vs_settings.collection_name


def test_vector_store_query_rbac_filter_uses_role(vs_settings):
    vs, mock_client, mock_dense, mock_sparse, mock_reranker = _build_vs(vs_settings)

    mock_dense.encode.return_value = np.zeros((1, 768))
    mock_sparse.embed.return_value = [_mock_sparse_vec()]

    mock_hit = MagicMock()
    mock_hit.id = 1
    mock_hit.payload = {
        "chunk_id": "c1",
        "source_file": "test.json",
        "content": "PHI must be encrypted.",
        "allowed_roles": ["admin", "manager", "staff"],
    }
    mock_client.search.return_value = [mock_hit]
    mock_reranker.predict.return_value = [0.9]

    results = vs.query("What is required for PHI?", role="admin", settings=vs_settings)

    # search called once for dense and once for sparse
    assert mock_client.search.call_count == 2

    first_call = mock_client.search.call_args_list[0]
    rbac_filter = first_call.kwargs.get("query_filter") or first_call[1].get("query_filter")
    assert rbac_filter is not None
    # FieldCondition key must target the RBAC payload field
    must_cond = rbac_filter.must[0]
    assert must_cond.key == "allowed_roles"

    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"


def test_vector_store_query_returns_empty_for_no_hits(vs_settings):
    vs, mock_client, mock_dense, mock_sparse, mock_reranker = _build_vs(vs_settings)

    mock_dense.encode.return_value = np.zeros((1, 768))
    mock_sparse.embed.return_value = [_mock_sparse_vec()]
    mock_client.search.return_value = []

    results = vs.query("unmatched query", role="staff", settings=vs_settings)
    assert results == []


# ---------------------------------------------------------------------------
# _rrf_merge — payload precedence
# ---------------------------------------------------------------------------


def test_rrf_merge_payload_first_list_wins():
    """When the same id appears in both lists, payload from the dense list is kept."""
    dense = [{"id": "x", "content": "from-dense"}]
    sparse = [{"id": "x", "content": "from-sparse"}]
    merged = _rrf_merge(dense, sparse, k=60)
    assert len(merged) == 1
    assert merged[0]["content"] == "from-dense"


def test_rrf_merge_overlap_scores_higher():
    """Ids in both lists rank above ids in only one list."""
    dense = [{"id": "a"}, {"id": "b"}]
    sparse = [{"id": "b"}, {"id": "c"}]
    merged = _rrf_merge(dense, sparse, k=60)
    ids = [h["id"] for h in merged]
    # "b" is in both lists — must be first
    assert ids[0] == "b"
