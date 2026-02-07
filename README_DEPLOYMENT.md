cat > README_DEPLOYMENT.md << 'EOF'
# Streamlit Cloud Deployment - IMPORTANT

## ⚠️ Known Limitation

**This app requires Ollama running locally**, which is NOT available on Streamlit Cloud's hosted environment.

## Deployment Options

### Option 1: Demo Mode (Recommended for Portfolio)

Deploy to Streamlit Cloud with **mock/cached responses**:

1. Modify `app.py` to use pre-generated answers
2. Load sample Q&A from `data/processed/evaluation_results.json`
3. Display cached responses instead of live LLM generation

### Option 2: Local Demo

Run locally and share via:
- Screen recording/demo video
- Screenshots in portfolio
- GitHub README with demo GIFs

### Option 3: Cloud VM Deployment

Deploy to cloud VM with Ollama:
- AWS EC2, Google Cloud, or Azure VM
- Install Ollama on the VM
- Run Streamlit on the VM
- Expose via public URL (ngrok or cloud load balancer)

## Recommended: Create Demo Video

Since live deployment requires infrastructure, create a compelling demo:

1. Run locally: `streamlit run app.py`
2. Record 2-3 minute demo showing:
   - RAG assistant answering questions
   - Analytics dashboard
   - Knowledge base overview
3. Upload to YouTube/Loom
4. Add link to README and resume

This is actually MORE impressive as it shows the full RAG system working!
EOF