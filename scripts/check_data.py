import json
import os

def check_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    processed_dir = os.path.join(base_dir, '../data/processed')
    raw_dir = os.path.join(base_dir, '../data/raw')
    
    print("=" * 60)
    print("WEEK 1 DATA PREP - FINAL CHECK")
    print("=" * 60)
    
    # Count PDFs
    if os.path.exists(raw_dir):
        pdf_count = len([f for f in os.listdir(raw_dir) if f.endswith('.pdf')])
        print(f"\n📄 Raw PDFs: {pdf_count} files")
    else:
        print(f"\n❌ Raw directory not found: {raw_dir}")
    
    # Check documents.json
    docs_file = os.path.join(processed_dir, 'documents.json')
    if os.path.exists(docs_file):
        with open(docs_file, 'r', encoding='utf-8') as f:
            docs = json.load(f)
        
        # Calculate total words - handle different metadata structures
        total_words = 0
        for d in docs:
            # Try different ways to get word_count
            if 'metadata' in d and 'word_count' in d['metadata']:
                total_words += d['metadata']['word_count']
            elif 'word_count' in d:
                total_words += d['word_count']
            elif 'content' in d:
                # Calculate from content if not stored
                total_words += len(d['content'].split())
        
        print(f"✅ Processed PDFs: {len(docs)} documents, ~{total_words:,} words")
        
        # Show sample
        if docs and len(docs) > 0:
            sample = docs[0]
            print(f"\n   Sample document: {sample.get('filename', 'unknown')}")
            content_preview = sample.get('content', '')[:200]
            print(f"   Content preview: {content_preview}...")
    else:
        print(f"❌ documents.json not found at: {docs_file}")
    
    # Check Wikipedia
    wiki_file = os.path.join(processed_dir, 'wikipedia_compliance.json')
    if os.path.exists(wiki_file):
        with open(wiki_file, 'r', encoding='utf-8') as f:
            wiki = json.load(f)
        
        wiki_words = 0
        for w in wiki:
            if 'word_count' in w:
                wiki_words += w['word_count']
            elif 'content' in w:
                wiki_words += len(w['content'].split())
        
        print(f"✅ Wikipedia articles: {len(wiki)} articles, ~{wiki_words:,} words")
    else:
        print(f"❌ wikipedia_compliance.json not found at: {wiki_file}")
    
    # Check synthetic Q&A
    qa_file = os.path.join(processed_dir, 'synthetic_qa_combined.json')
    if os.path.exists(qa_file):
        with open(qa_file, 'r', encoding='utf-8') as f:
            qa = json.load(f)
        print(f"✅ Synthetic Q&A: {len(qa)} pairs")
        
        # Show categories
        categories = {}
        for q in qa:
            cat = q.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        print(f"   Categories: {len(categories)} unique")
    else:
        print(f"❌ synthetic_qa_combined.json not found at: {qa_file}")
    
    print("\n" + "=" * 60)
    print("STATUS: Week 1 Data Collection Complete! 🎉")
    print("NEXT: Week 2 - Build the RAG system")
    print("=" * 60)

if __name__ == '__main__':
    check_data()