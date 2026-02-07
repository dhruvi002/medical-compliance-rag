# app.py
import streamlit as st
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vector_store import VectorStore
from rag_system import RAGSystem
from access_control import AccessControlSystem
from compliance_dashboard import ComplianceDashboard
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="Medical Compliance RAG Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .source-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.rag_system = None
    st.session_state.chat_history = []
    st.session_state.current_user = None

@st.cache_resource
def load_rag_system():
    """Load RAG system (cached)"""
    try:
        script_dir = os.path.dirname(__file__)
        persist_dir = os.path.join(script_dir, 'chroma_db')
        
        # Check if chroma_db exists
        if not os.path.exists(persist_dir):
            st.error("⚠️ ChromaDB not found. Please run the setup scripts first.")
            return None
        
        vector_store = VectorStore(persist_directory=persist_dir)
        rag = RAGSystem(vector_store, model_name="llama3.1:8b", n_results=5, enable_audit=True)
        return rag
    except Exception as e:
        st.error(f"Error loading RAG system: {e}")
        return None

@st.cache_resource
def load_access_control():
    """Load access control system (cached)"""
    try:
        return AccessControlSystem()
    except:
        return None

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1f77b4/ffffff?text=HealthCare+AI", width=150)
        st.markdown("---")
        
        # User selection
        st.subheader("👤 User Login")
        
        access_control = load_access_control()
        if access_control:
            users = access_control.get_all_users()
            user_options = ["Select User"] + [f"{u['user_id']} - {u['role']}" for u in users[:20]]
            
            selected = st.selectbox("Choose User:", user_options)
            
            if selected != "Select User":
                user_id = selected.split(" - ")[0]
                st.session_state.current_user = user_id
                
                user_info = access_control.get_user_info(user_id)
                if user_info:
                    st.success(f"✓ Logged in as {user_id}")
                    st.caption(f"Role: **{user_info['role'].title()}**")
        else:
            st.session_state.current_user = "DEMO_USER"
            st.info("Running in demo mode")
        
        st.markdown("---")
        
        # Navigation
        st.subheader("📋 Navigation")
        page = st.radio(
            "Go to:",
            ["🤖 RAG Assistant", "📊 Analytics Dashboard", "📚 Knowledge Base", "ℹ️ About"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.caption("Medical Compliance RAG System")
        st.caption("Built with Streamlit + Ollama")
    
    # Main content
    if page == "🤖 RAG Assistant":
        show_rag_assistant()
    elif page == "📊 Analytics Dashboard":
        show_analytics_dashboard()
    elif page == "📚 Knowledge Base":
        show_knowledge_base()
    else:
        show_about()

def show_rag_assistant():
    """RAG Q&A Interface"""
    st.markdown('<h1 class="main-header">🏥 Medical Compliance Assistant</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Ask questions about medical compliance topics including:
    - **HIPAA** privacy and security requirements
    - **OSHA** workplace safety regulations  
    - **Infection Control** protocols
    - **Medical Waste** disposal procedures
    - **PPE** requirements and best practices
    """)
    
    # Load RAG system
    rag = load_rag_system()
    
    if rag is None:
        st.error("⚠️ RAG system not available. Please ensure Ollama is running and ChromaDB is initialized.")
        return
    
    # Chat interface
    st.markdown("---")
    
    # Sample questions
    with st.expander("💡 Sample Questions", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("What should I do after a needlestick injury?"):
                st.session_state.sample_q = "What should I do immediately after a needlestick injury?"
            if st.button("What are HIPAA privacy requirements?"):
                st.session_state.sample_q = "What are the HIPAA privacy rule requirements?"
        with col2:
            if st.button("How do I dispose of sharps?"):
                st.session_state.sample_q = "How should I dispose of contaminated sharps?"
            if st.button("When should I perform hand hygiene?"):
                st.session_state.sample_q = "What are the hand hygiene requirements in healthcare?"
    
    # Query input
    query = st.text_input(
        "Ask your question:",
        value=st.session_state.get('sample_q', ''),
        placeholder="e.g., What are the requirements for bloodborne pathogen training?",
        key="query_input"
    )
    
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        ask_button = st.button("🔍 Ask", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_button:
        st.session_state.chat_history = []
        st.session_state.sample_q = ''
        st.rerun()
    
    # Process query
    if ask_button and query:
        with st.spinner("🔍 Searching knowledge base..."):
            user_id = st.session_state.get('current_user', 'DEMO_USER')
            
            try:
                result = rag.query(query, user_id=user_id, verbose=False)
                
                # Add to chat history
                st.session_state.chat_history.append({
                    'query': query,
                    'result': result,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                })
                
            except Exception as e:
                st.error(f"Error processing query: {e}")
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("💬 Conversation History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.container():
                st.markdown(f"**Q{len(st.session_state.chat_history)-i}:** {chat['query']}")
                st.markdown(f"*{chat['timestamp']}*")
                
                # Answer
                st.markdown("**Answer:**")
                st.info(chat['result']['answer'])
                
                # Sources
                with st.expander(f"📚 Sources ({len(chat['result']['sources'])})"):
                    for j, source in enumerate(chat['result']['sources'], 1):
                        st.markdown(f"""
                        <div class="source-box">
                            <strong>{j}. {source['file']}</strong><br>
                            <small>{source['preview'][:150]}...</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("---")

def show_analytics_dashboard():
    """Analytics Dashboard"""
    st.markdown('<h1 class="main-header">📊 Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    try:
        dashboard = ComplianceDashboard()
        summary = dashboard.generate_executive_summary(days=30)
        
        # Key Metrics
        st.subheader("📈 Key Metrics (Last 30 Days)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Queries",
                summary['system_health']['total_queries'],
                delta=None
            )
        
        with col2:
            st.metric(
                "Active Users",
                summary['user_engagement']['active_users'],
                delta=None
            )
        
        with col3:
            st.metric(
                "Avg Response Time",
                f"{summary['system_health']['avg_response_time']:.1f}s",
                delta=None
            )
        
        with col4:
            st.metric(
                "Success Rate",
                f"{summary['system_health']['success_rate']:.0%}",
                delta=None
            )
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📚 Top Referenced Sources")
            if summary['top_sources']:
                sources_df = {
                    'Source': [s['source'][:30] + '...' if len(s['source']) > 30 else s['source'] for s in summary['top_sources']],
                    'References': [s['times_referenced'] for s in summary['top_sources']]
                }
                
                fig = px.bar(
                    sources_df,
                    x='References',
                    y='Source',
                    orientation='h',
                    title="Most Referenced Documents"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No query data available yet")
        
        with col2:
            st.subheader("👥 User Engagement")
            
            engagement = summary['user_engagement']
            
            fig = go.Figure(data=[go.Pie(
                labels=['Active & Engaged', 'Never Queried'],
                values=[
                    engagement['active_users'] - engagement['never_queried'],
                    engagement['never_queried']
                ],
                hole=.3
            )])
            fig.update_layout(title="User Activity Distribution")
            st.plotly_chart(fig, use_container_width=True)
        
        # Alerts
        if summary['alerts']:
            st.markdown("---")
            st.subheader("🚨 Alerts")
            
            for alert in summary['alerts']:
                if alert['severity'] == 'critical':
                    st.error(f"🔴 {alert['message']}")
                elif alert['severity'] == 'warning':
                    st.warning(f"⚠️ {alert['message']}")
                else:
                    st.info(f"ℹ️ {alert['message']}")
        
        # Knowledge Base Stats
        st.markdown("---")
        st.subheader("📖 Knowledge Base")
        
        col1, col2, col3 = st.columns(3)
        
        kb = summary['knowledge_base']
        
        with col1:
            st.metric("Total Documents", kb['total_documents'])
        with col2:
            st.metric("Active Documents", kb['active_documents'])
        with col3:
            freshness = ((kb['active_documents'] - kb['stale_documents']) / kb['active_documents'] * 100) if kb['active_documents'] > 0 else 0
            st.metric("Freshness", f"{freshness:.0f}%")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.info("Run the governance scripts first to generate analytics data.")

def show_knowledge_base():
    """Knowledge Base Overview"""
    st.markdown('<h1 class="main-header">📚 Knowledge Base</h1>', unsafe_allow_html=True)
    
    try:
        from document_registry import DocumentRegistry
        
        registry = DocumentRegistry()
        report = registry.get_usage_report()
        
        st.subheader("📊 Overview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", report['total_documents'])
        with col2:
            st.metric("Active", report['active_documents'])
        with col3:
            st.metric("Archived", report['archived_documents'])
        
        st.markdown("---")
        
        # Document types
        st.subheader("📁 Documents by Type")
        
        type_df = {
            'Type': list(report['by_type'].keys()),
            'Count': list(report['by_type'].values())
        }
        
        fig = px.pie(
            type_df,
            values='Count',
            names='Type',
            title="Distribution by Document Type"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Most referenced
        st.markdown("---")
        st.subheader("🔥 Most Referenced Documents")
        
        if report['most_referenced']:
            for i, doc in enumerate(report['most_referenced'][:10], 1):
                if doc['times_referenced'] > 0:
                    st.markdown(f"{i}. **{doc['document_id']}** - {doc['times_referenced']} references")
        else:
            st.info("No usage data available yet")
        
    except Exception as e:
        st.error(f"Error loading knowledge base: {e}")

def show_about():
    """About Page"""
    st.markdown('<h1 class="main-header">ℹ️ About This System</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ## Medical Compliance RAG Assistant
    
    A Retrieval-Augmented Generation system for healthcare compliance questions.
    
    ### 🎯 Features
    
    - **RAG Q&A System**: Ask questions, get answers from official compliance documents
    - **Source Attribution**: Every answer cites specific documents
    - **Audit Logging**: All queries tracked for compliance
    - **Access Control**: Role-based permissions (employee, trainer, admin)
    - **Analytics Dashboard**: Monitor usage and system health
    
    ### 📚 Knowledge Base
    
    - **98 Documents**: 88 government PDFs + 10 Wikipedia articles
    - **1,425 Chunks**: Semantically segmented for optimal retrieval
    - **Topics Covered**:
        - HIPAA Privacy & Security
        - OSHA Workplace Safety
        - Infection Control Protocols
        - Medical Waste Disposal
        - PPE Requirements
        - Bloodborne Pathogens
        - Hand Hygiene
        - Emergency Procedures
    
    ### 🛠️ Technology Stack
    
    - **LLM**: Ollama (llama3.1:8b) - Local inference, zero API costs
    - **Vector DB**: ChromaDB with sentence-transformers embeddings
    - **Framework**: LangChain for RAG orchestration
    - **UI**: Streamlit
    - **Governance**: Custom audit logging, access control, document registry
    
    ### 📊 System Stats
    
    - **Documents Processed**: ~288,500 words
    - **Vector Embeddings**: 1,425 chunks
    - **Users**: 101 (100 employees + 1 admin)
    - **Average Response Time**: ~15-20 seconds
    
    ### 🎓 Built By
    
    **Dhruvi Shah**  
    Portfolio project demonstrating:
    - RAG system architecture
    - NLP-based skill gap analysis
    - Data governance & compliance
    - Production-ready ML systems
    
    ### 📝 Documentation
    
    - Phase 1: Data Collection & Processing
    - Phase 2: RAG System Implementation
    - Phase 3: Skill Gap Analysis
    - Phase 4: Data Governance
    - Phase 5: Streamlit Deployment (current)
    
    ### ⚠️ Disclaimer
    
    This is an educational/portfolio project. Not intended for actual medical use.
    Always consult official compliance resources and legal counsel.
    """)
    
    st.markdown("---")
    st.caption("© 2026 - Medical Compliance RAG Assistant - Portfolio Project")

if __name__ == "__main__":
    main()