import os

import streamlit as st

from medcomply.audit_logger import AuditLogger
from medcomply.auth import get_current_user, load_authenticator
from medcomply.llm_client import get_llm_client
from medcomply.rag_system import RAGSystem
from medcomply.settings import Settings
from medcomply.vector_store import VectorStore

st.set_page_config(
    page_title="Medical Compliance RAG Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

_DISCLAIMER = (
    "> **Educational/portfolio project. Not a clinical tool. "
    "Do not use for actual medical decisions.**"
)


def _get_secret(key: str, default: str = "") -> str:
    env_val = os.environ.get(key)
    if env_val:
        return env_val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


@st.cache_resource
def _build_resources():
    qdrant_url = _get_secret("QDRANT_URL", ":memory:")
    qdrant_api_key = _get_secret("QDRANT_API_KEY", "")
    llm_backend = _get_secret("LLM_BACKEND", "groq")

    settings = Settings(
        llm_backend=llm_backend,
        qdrant_url=qdrant_url,
    )
    vector_store = VectorStore(settings, qdrant_url=qdrant_url, qdrant_api_key=qdrant_api_key)
    llm_client = get_llm_client(settings)
    audit_logger = AuditLogger()
    rag_system = RAGSystem(settings, vector_store, llm_client, audit_logger)
    return settings, vector_store, audit_logger, rag_system


def _page_rag_assistant(rag_system: RAGSystem, username: str, role: str):
    st.title("Medical Compliance Assistant")
    st.markdown(_DISCLAIMER)
    st.markdown("---")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.expander("Sample questions", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("What should I do after a needlestick injury?"):
                st.session_state.pending_query = "What should I do immediately after a needlestick injury?"
            if st.button("What are HIPAA privacy requirements?"):
                st.session_state.pending_query = "What are the HIPAA privacy rule requirements?"
        with col2:
            if st.button("How do I dispose of sharps?"):
                st.session_state.pending_query = "How should I dispose of contaminated sharps?"
            if st.button("When should I perform hand hygiene?"):
                st.session_state.pending_query = "What are the hand hygiene requirements in healthcare?"

    query = st.text_input(
        "Ask your question:",
        value=st.session_state.get("pending_query", ""),
        placeholder="e.g., What are the requirements for bloodborne pathogen training?",
    )

    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        ask = st.button("Ask", type="primary", use_container_width=True)
    with col2:
        if st.button("Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.pop("pending_query", None)
            st.rerun()

    if ask and query:
        st.session_state.pop("pending_query", None)
        with st.spinner("Searching knowledge base..."):
            try:
                result = rag_system.query(query, user_id=username, role=role)
                st.session_state.chat_history.append({"query": query, "result": result})
            except Exception as exc:
                st.error(f"Error processing query: {exc}")

    if st.session_state.chat_history:
        st.markdown("---")
        for item in reversed(st.session_state.chat_history):
            st.markdown(f"**Q:** {item['query']}")
            res = item["result"]
            if res.get("truncated"):
                st.warning("Response was truncated due to token limit.")
            st.info(res["answer"])
            with st.expander(f"Sources ({len(res['sources'])})"):
                for src in res["sources"]:
                    st.code(src)
            st.markdown("---")


def _page_analytics(audit_logger: AuditLogger):
    st.title("Analytics")
    st.markdown(_DISCLAIMER)
    st.markdown("---")

    stats = audit_logger.stats()
    if stats["total_queries"] == 0:
        st.info("No query data yet.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Queries", stats["total_queries"])
    with col2:
        st.metric("Unique Users", stats["unique_users"])
    with col3:
        avg_s = stats["avg_latency_ms"] / 1000
        st.metric("Avg Latency", f"{avg_s:.1f}s")

    st.markdown("---")
    st.subheader("Recent Queries")
    recent = audit_logger.recent(20)
    for row in recent:
        st.markdown(
            f"**{row['timestamp'][:19]}** | `{row['user_id']}` ({row['role']}) | "
            f"{row['latency_ms']:.0f}ms"
        )
        st.caption(f"> {row['query']}")


def _page_about(settings: Settings, vector_store: VectorStore, audit_logger: AuditLogger):
    st.title("About")
    st.markdown(_DISCLAIMER)
    st.markdown("---")

    st.markdown(
        "A Retrieval-Augmented Generation system for healthcare compliance questions. "
        "Answers are grounded in synthetic compliance documents covering HIPAA, OSHA, "
        "infection control, medical waste, and documentation training."
    )

    st.subheader("Live System Stats")
    col1, col2, col3 = st.columns(3)

    try:
        chunk_count = vector_store._client.count(
            collection_name=settings.collection_name
        ).count
    except Exception:
        chunk_count = 0

    stats = audit_logger.stats()
    with col1:
        st.metric("Chunks indexed", chunk_count)
    with col2:
        st.metric("Queries served", stats["total_queries"])
    with col3:
        st.metric("Unique users", stats["unique_users"])

    st.markdown("---")
    st.subheader("Technology Stack")
    st.markdown("""
| Concern | Choice |
|---|---|
| Vector DB | Qdrant (hybrid dense + sparse, RBAC payload filter) |
| Dense embeddings | `BAAI/bge-base-en-v1.5` (768-dim) |
| Sparse retrieval | SPLADE via `fastembed` |
| Reranker | `BAAI/bge-reranker-v2-m3` |
| Fusion | Reciprocal Rank Fusion (RRF) |
| LLM (hosted) | Groq free tier |
| LLM (local) | Ollama — Llama 3.1 8B |
| Auth | `streamlit-authenticator` (bcrypt) |
| Audit | SQLite + `uuid.uuid4()` |
| Packaging | `src/medcomply/` layout, `uv` |
""")

    st.markdown("---")
    st.caption("Dhruvi Shah — portfolio project. Code: github.com/dhruvi002/medical-compliance-rag")


def main():
    try:
        authenticator = load_authenticator()
    except FileNotFoundError:
        st.error(
            "Auth config not found. Run `python scripts/create_auth_config.py` to generate it."
        )
        st.stop()

    authenticator.login()
    auth_status = st.session_state.get("authentication_status")
    username = st.session_state.get("username", "")

    if auth_status is False:
        st.error("Incorrect username or password.")
        st.stop()
    if not auth_status:
        st.stop()

    user = get_current_user(auth_status, username)
    if user is None:
        st.error("Could not resolve user role. Contact an administrator.")
        st.stop()

    username, role = user

    settings, vector_store, audit_logger, rag_system = _build_resources()

    with st.sidebar:
        st.markdown(f"**{username}** — `{role}`")
        authenticator.logout("Logout")
        st.markdown("---")
        page = st.radio(
            "Navigate",
            ["RAG Assistant", "Analytics", "About"],
            label_visibility="collapsed",
        )

    if page == "RAG Assistant":
        _page_rag_assistant(rag_system, username, role)
    elif page == "Analytics":
        _page_analytics(audit_logger)
    else:
        _page_about(settings, vector_store, audit_logger)


if __name__ == "__main__":
    main()
