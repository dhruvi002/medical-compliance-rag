# app_demo.py - Streamlit Cloud compatible version with cached responses
import streamlit as st
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Medical Compliance RAG Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (same as before)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .source-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .demo-notice {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Load cached Q&A
@st.cache_data
def load_demo_qa():
    """Load pre-generated Q&A for demo"""
    qa_pairs = {
        "What should I do immediately after a needlestick injury?": {
            "answer": """**Immediate Action After a Needlestick Injury**

Follow these critical steps:

1. **Wash the wound** with soap and water immediately [Source 1]
2. **Do not squeeze or scrub** the wound [Source 1]
3. **Report the incident** to your supervisor and occupational health within 2 hours [Source 2]
4. **Seek medical evaluation** - your employer must provide confidential evaluation at no cost [Source 2]

**Required Follow-up:**
- Baseline testing should occur within 2 hours (HIV, hepatitis panel) [Source 1]
- Post-exposure prophylaxis (PEP) may be needed depending on source patient status [Source 1]
- Document per OSHA 1910.1030(f) [Source 2]

**Time is Critical:** HIV PEP is most effective when started within hours of exposure.""",
            "sources": [
                {"file": "osha_bloodborne_pathogens.pdf", "preview": "Bloodborne pathogens standard requires immediate washing with soap and water following needlestick..."},
                {"file": "Needlestick_injury", "preview": "A needlestick injury is a percutaneous wound accidentally inflicted by a needle point..."},
                {"file": "exposure-risk-classification-factsheet.pdf", "preview": "Post-exposure prophylaxis should begin within 2 hours of exposure incident..."}
            ]
        },
        "What are the HIPAA privacy rule requirements?": {
            "answer": """**HIPAA Privacy Rule Requirements**

The HIPAA Privacy Rule establishes national standards for protecting individuals' medical records and personal health information (PHI).

**Core Requirements:**

1. **Minimum Necessary Standard** [Source 1]
   • Use/disclose only minimum PHI needed for purpose
   • Applies to all disclosures except treatment

2. **Patient Rights** [Source 2]
   • Right to access medical records
   • Right to request amendments
   • Right to accounting of disclosures
   • Right to request restrictions

3. **Authorization Requirements** [Source 1]
   • Written authorization required for most disclosures
   • Must specify: what information, to whom, purpose
   • Verbal permission is NOT sufficient

4. **Business Associate Agreements** [Source 2]
   • Required for third-party vendors with PHI access
   • Must include specific safeguards

5. **Breach Notification** [Source 3]
   • Notify individuals within 60 days
   • Report to HHS if >500 individuals affected""",
            "sources": [
                {"file": "hipaa_privacy_rule.pdf", "preview": "The HIPAA Privacy Rule requires covered entities to implement policies ensuring the confidentiality..."},
                {"file": "HIPAA", "preview": "The Health Insurance Portability and Accountability Act of 1996 is United States legislation..."},
                {"file": "Medical_Records-Access.pdf", "preview": "Patients have the right to access and obtain copies of their medical records under HIPAA..."}
            ]
        },
        "How should I dispose of contaminated sharps?": {
            "answer": """**Disposing of Contaminated Sharps**

Per OSHA regulations [Source 1], contaminated sharps must be disposed of immediately in containers that meet these requirements:

**Container Requirements:**
- Closable
- Puncture resistant  
- Leakproof on sides and bottom
- Labeled or color-coded (red/biohazard symbol)

**Step-by-Step Procedure:**

1. **Immediate Disposal** [Source 1]
   • Discard sharps immediately after use
   • Do NOT recap needles
   • Place directly in sharps container

2. **Container Placement** [Source 2]
   • Located close to where sharps are used
   • Easily accessible to personnel
   • Maintained upright during use

3. **Container Maintenance** [Source 2]
   • Replace when 3/4 full
   • Close immediately before removal
   • Do not overfill

4. **Final Disposal** [Source 3]
   • Autoclave or incineration
   • Never in regular trash
   • Follow state/local regulations

**CRITICAL:** Never attempt to retrieve items from sharps containers [Source 1]""",
            "sources": [
                {"file": "osha_bloodborne_pathogens.pdf", "preview": "Contaminated sharps shall be discarded immediately or as soon as feasible in containers that are..."},
                {"file": "Sharps_waste", "preview": "Sharps waste is a form of biomedical waste composed of used sharps which includes needles..."},
                {"file": "Medical_waste", "preview": "Medical waste, also known as clinical waste, is waste contaminated with blood and other bodily fluids..."}
            ]
        },
        "What are the hand hygiene requirements in healthcare?": {
            "answer": """**Hand Hygiene Requirements in Healthcare Settings**

Hand hygiene is the single most important practice to reduce transmission of infectious agents [Source 1].

**When to Perform Hand Hygiene (WHO 5 Moments):**

1. **Before touching a patient** [Source 2]
2. **Before clean/aseptic procedures**
3. **After body fluid exposure risk**
4. **After touching a patient**
5. **After touching patient surroundings**

**Technique Requirements:**

**Alcohol-Based Hand Rub** [Source 1]
- Preferred method when hands not visibly soiled
- Apply to palm, rub all surfaces
- Continue until hands dry (15-30 seconds)
- Use products with 60-95% alcohol

**Soap and Water** [Source 2]
- Required when hands visibly dirty/soiled
- Wet hands, apply soap
- Rub all surfaces for 15-30 seconds
- Rinse and dry completely

**Additional Requirements:**

- Remove jewelry before patient care [Source 1]
- Keep fingernails short (<0.5cm) [Source 2]
- No artificial nails when providing patient care [Source 2]
- Use hand lotion to prevent skin damage [Source 1]

**Compliance Monitoring:** Healthcare facilities must monitor and document hand hygiene compliance rates [Source 3]""",
            "sources": [
                {"file": "Guideline_for_Hand_Hygiene.pdf", "preview": "Hand hygiene is the single most important practice to reduce the transmission of infectious agents..."},
                {"file": "Hand_hygiene", "preview": "Hand hygiene is a way of cleaning one's hands that substantially reduces potential pathogens..."},
                {"file": "Infection_control", "preview": "Infection control prevents or stops the spread of infections in healthcare settings..."}
            ]
        }
    }
    return qa_pairs

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/1f77b4/ffffff?text=HealthCare+AI", width=150)
        st.markdown("---")
        
        st.info("🎬 **Demo Mode**\n\nThis is a demonstration version with cached responses.")
        
        st.markdown("---")
        
        # Navigation
        st.subheader("📋 Navigation")
        page = st.radio(
            "Go to:",
            ["🤖 RAG Assistant", "📊 Analytics", "ℹ️ About"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.caption("Medical Compliance RAG System")
        st.caption("Portfolio Project Demo")
    
    # Main content
    if page == "🤖 RAG Assistant":
        show_rag_assistant()
    elif page == "📊 Analytics":
        show_analytics()
    else:
        show_about()

def show_rag_assistant():
    """RAG Q&A Interface with cached responses"""
    st.markdown('<h1 class="main-header">🏥 Medical Compliance Assistant</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="demo-notice">
    <strong>📌 Demo Version:</strong> This deployment uses pre-generated responses. 
    The full system runs locally with Ollama for real-time LLM generation.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    Ask questions about medical compliance topics:
    - **HIPAA** privacy and security
    - **OSHA** workplace safety  
    - **Infection Control** protocols
    - **Medical Waste** disposal
    """)
    
    # Load cached Q&A
    qa_pairs = load_demo_qa()
    
    st.markdown("---")
    
    # Sample questions as buttons
    st.subheader("💡 Try These Questions:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        for q in list(qa_pairs.keys())[:2]:
            if st.button(q[:50] + "...", key=f"btn_{q[:20]}"):
                st.session_state.selected_question = q
    
    with col2:
        for q in list(qa_pairs.keys())[2:4]:
            if st.button(q[:50] + "...", key=f"btn_{q[:20]}"):
                st.session_state.selected_question = q
    
    # Process selected question
    if 'selected_question' in st.session_state:
        query = st.session_state.selected_question
        
        st.markdown("---")
        st.subheader("Question:")
        st.write(query)
        
        result = qa_pairs[query]
        
        st.subheader("Answer:")
        st.info(result['answer'])
        
        with st.expander(f"📚 Sources ({len(result['sources'])})"):
            for i, source in enumerate(result['sources'], 1):
                st.markdown(f"""
                <div class="source-box">
                    <strong>{i}. {source['file']}</strong><br>
                    <small>{source['preview']}</small>
                </div>
                """, unsafe_allow_html=True)

def show_analytics():
    """Mock analytics dashboard"""
    st.markdown('<h1 class="main-header">📊 System Analytics</h1>', unsafe_allow_html=True)
    
    st.subheader("📈 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Queries", "347")
    with col2:
        st.metric("Active Users", "67")
    with col3:
        st.metric("Avg Response", "14.2s")
    with col4:
        st.metric("Success Rate", "94%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 Top Sources")
        data = {
            'Source': ['HIPAA Privacy Rule', 'OSHA Bloodborne', 'Hand Hygiene Guide', 'Sharps Disposal', 'Infection Control'],
            'References': [89, 67, 54, 48, 42]
        }
        fig = px.bar(data, x='References', y='Source', orientation='h')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("👥 User Engagement")
        fig = go.Figure(data=[go.Pie(
            labels=['Active & Engaged', 'Never Queried'],
            values=[52, 15],
            hole=.3
        )])
        st.plotly_chart(fig, use_container_width=True)

def show_about():
    """About page"""
    st.markdown('<h1 class="main-header">ℹ️ About This System</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ## Medical Compliance RAG Assistant
    
    A production-ready RAG system for healthcare compliance.
    
    ### 🎯 Key Features
    
    - **1,425 Knowledge Chunks** from 98 official documents
    - **Local LLM** (Ollama llama3.1:8b) - zero API costs
    - **Source Attribution** - every answer cites documents
    - **Audit Logging** - full query tracking
    - **Access Control** - role-based permissions
    - **Governance Dashboard** - compliance monitoring
    
    ### 🛠️ Tech Stack
    
    - **LLM**: Ollama (llama3.1:8b)
    - **Vector DB**: ChromaDB  
    - **Embeddings**: sentence-transformers
    - **Framework**: LangChain
    - **UI**: Streamlit
    
    ### 📊 Scope
    
    - **Documents**: 88 PDFs + 10 Wikipedia articles
    - **Word Count**: ~288,500 words
    - **Users**: 101 (100 employees + 1 admin)
    - **Categories**: HIPAA, OSHA, Infection Control, Medical Waste, PPE, etc.
    
    ### 🎓 Portfolio Project
    
    **Built by:** Dhruvi Shah
    
    **Demonstrates:**
    - RAG architecture & implementation
    - NLP-based skill gap analysis  
    - Data governance & compliance tracking
    - Production ML system design
    
    ### 🔗 Links
    
    - [GitHub Repository](https://github.com/YOUR_USERNAME/medical-compliance-rag)
    - [Documentation](https://github.com/YOUR_USERNAME/medical-compliance-rag#readme)
    - [Demo Video](#) (Coming Soon)
    
    ### ⚠️ Note
    
    This is an educational/portfolio project demonstrating ML capabilities.
    Not intended for actual medical decision-making.
    """)

if __name__ == "__main__":
    main()