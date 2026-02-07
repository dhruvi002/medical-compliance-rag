# Medical Compliance RAG System

🔗 **[Live Demo](https://medical-compliance-rag.streamlit.app/)** ← Try it now!

A Retrieval-Augmented Generation (RAG) system for answering medical compliance questions. 

## 🎯 Project Overview

This project builds a comprehensive AI assistant for healthcare compliance questions, combining:
- **RAG architecture** for accurate, source-grounded responses
- **Local LLM inference** using Ollama (zero API costs)
- **Vector search** with ChromaDB
- **NLP-based skill gap analysis** (upcoming)
- **Impact measurement dashboards** (upcoming)

**Target users:** ~100 healthcare workers  
**Budget constraint:** $0 (all open-source/free tier)  

---

## 📊 Project Status

### ✅ Phase 1: Data Collection & Preparation (COMPLETE)

**Accomplishments:**
- Collected and processed **158 compliance documents**
- Extracted **~288,500 words** of authoritative content
- Generated **60 synthetic Q&A pairs** for testing
- Set up development environment with Ollama + Python stack

**Dataset Breakdown:**

| Source | Count | Words | Description |
|--------|-------|-------|-------------|
| Government PDFs | 88 | ~274,857 | OSHA, HIPAA, CDC guidelines |
| Wikipedia Articles | 10 | ~13,645 | Supplementary context |
| Synthetic Q&A | 60 | N/A | Testing dataset (14 categories) |
| **TOTAL** | **158** | **~288,502** | Complete corpus |

**Document Categories:**
- HIPAA privacy and security rules
- OSHA bloodborne pathogen standards
- Infection control protocols (CDC)
- Medical waste disposal procedures
- PPE requirements and protocols
- Workplace safety regulations
- Employee training requirements
- Documentation and record-keeping

---

## 🛠️ Technical Stack

### Infrastructure
- **LLM:** Ollama (llama3.1:8b, mistral:7b)
- **Embeddings:** nomic-embed-text (274MB, local)
- **Vector DB:** ChromaDB (planned)
- **Orchestration:** LangChain (planned)
- **Frontend:** Streamlit (planned)

### Development
- **Language:** Python 3.x
- **Environment:** Virtual environment (venv)
- **Libraries:** 
  - Document processing: PyPDF2, BeautifulSoup4
  - ML/AI: langchain, chromadb, sentence-transformers
  - Data handling: requests, json

---

## 📁 Project Structure
```
medical-rag-system/
├── data/
│   ├── raw/                    # 88 original PDF files
│   ├── processed/              # Cleaned, structured data
│   │   ├── documents.json              # All PDFs as text
│   │   ├── wikipedia_compliance.json   # Wikipedia articles
│   │   └── synthetic_qa_combined.json  # Test Q&As
│   └── synthetic/              # Q&A batch files
├── scripts/
│   ├── pdf_processor_v2.py     # Extract text from PDFs
│   ├── scraper.py              # Wikipedia scraping
│   ├── merge_qa_batches.py     # Combine Q&A files
│   └── check_data.py           # Data verification
├── src/                        # RAG system code (Week 2)
├── venv/                       # Python virtual environment
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

---

## 🚀 Getting Started

### Prerequisites
```bash
# Install Ollama
brew install ollama

# Pull LLM models
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull nomic-embed-text
```

### Setup
```bash
# Clone/navigate to project
cd medical-rag-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Verify Data
```bash
python scripts/check_data.py
```

Expected output:
```
✅ Processed PDFs: 88 documents, ~274,857 words
✅ Wikipedia articles: 10 articles, ~13,645 words
✅ Synthetic Q&A: 60 pairs
```

---

## 📈 Roadmap

### Phase 1: Data Prep ✅ COMPLETE
- [x] Install Ollama and models
- [x] Collect 88+ government compliance documents
- [x] Scrape 10 Wikipedia articles
- [x] Generate 60 synthetic Q&A pairs
- [x] Process all PDFs to text
- [x] Set up Python environment

### Phase 2: RAG System (In Progress)
- [ ] Set up ChromaDB vector database
- [ ] Generate embeddings for all documents
- [ ] Implement retrieval pipeline with LangChain
- [ ] Build query interface
- [ ] Test with synthetic Q&As

### Phase 3: Skill Gap Analyzer
- [ ] Create synthetic employee training data
- [ ] Build NLP analysis for skill gaps
- [ ] Implement recommendation engine

### Phase 4: Data Governance
- [ ] Add compliance tracking
- [ ] Implement audit trails
- [ ] Add data lineage documentation

### Phase 5: Impact Dashboard
- [ ] Build Streamlit dashboard
- [ ] Add usage analytics
- [ ] Create performance metrics

### Phase 6: Polish & Deploy
- [ ] Optimize performance
- [ ] Write documentation
- [ ] Deploy to Streamlit Cloud
- [ ] Create demo video

---

## 📊 Dataset Statistics

### PDF Processing Results
```
Successfully processed: 88/88 PDFs
Total words extracted: 274,857
Average words per document: 3,123
Encrypted PDFs: 0
Failed extractions: 0
```

### Synthetic Q&A Categories
- HIPAA: 10 pairs
- OSHA: 10 pairs
- Infection Control: 10 pairs
- Medical Waste: 10 pairs
- Documentation & Training: 10 pairs
- Complex/Multi-Regulation: 10 pairs

---

## 🎓 Learning Objectives

This project demonstrates:

1. **RAG System Design**
   - Document chunking strategies
   - Embedding generation and storage
   - Retrieval-augmented prompting
   - Source attribution and citations

2. **Data Engineering**
   - PDF text extraction at scale
   - Web scraping with error handling
   - Data cleaning and normalization
   - Synthetic data generation

3. **ML System Design**
   - Local LLM deployment (Ollama)
   - Vector database integration
   - Evaluation framework design
   - Cost optimization strategies

4. **Production Considerations**
   - Zero-cost architecture
   - Scalability for ~100 users
   - Error handling and logging
   - Data governance and compliance

---

## 📝 Data Sources

All data is publicly available:

- **OSHA:** https://www.osha.gov/publications
- **HIPAA:** https://www.hhs.gov/hipaa/for-professionals/
- **CDC:** https://www.cdc.gov/infection-control/
- **Wikipedia:** Medical compliance topics (CC BY-SA)
- **Synthetic Q&As:** Generated using ChatGPT free tier

---

## 🔜 Next Steps

**Immediate (Phase 2):**
1. Initialize ChromaDB vector store
2. Chunk documents (500-1000 tokens)
3. Generate embeddings using nomic-embed-text
4. Build LangChain retrieval chain
5. Create basic Streamlit UI

**See detailed Phase 2 plan in `/docs/Phase2_plan.md`** (coming soon)

---

## 👤 Author

**Dhruvi Shah**  
AI/ML Engineer  
Student- University of Massachusetts, Amherst
Masters in Computer Science
---

## 📄 License

This project is for educational/portfolio purposes.  
Government documents are public domain.  
Code is available for review.

---