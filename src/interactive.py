# src/interactive.py
import os
from vector_store import VectorStore
from rag_system import RAGSystem

def print_header():
    """Print welcome header"""
    print("\n" + "="*60)
    print("MEDICAL COMPLIANCE RAG ASSISTANT")
    print("="*60)
    print("Ask questions about medical compliance, HIPAA, OSHA, etc.")
    print("Type 'quit' or 'exit' to end the session")
    print("Type 'sources' to toggle source display")
    print("="*60 + "\n")

def print_answer(result: dict, show_sources: bool = True):
    """Pretty print the answer"""
    print(f"\n{'─'*60}")
    print("ANSWER:")
    print(f"{'─'*60}")
    print(result['answer'])
    
    if show_sources:
        print(f"\n{'─'*60}")
        print(f"SOURCES ({result['num_sources']} documents):")
        print(f"{'─'*60}")
        for i, source in enumerate(result['sources'], 1):
            print(f"{i}. {source['file']}")
    
    print()

def main():
    """Interactive query loop"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize system
    print("Loading RAG system...")
    persist_dir = os.path.join(script_dir, '../chroma_db')
    vector_store = VectorStore(persist_directory=persist_dir)
    rag = RAGSystem(vector_store, model_name="llama3.1:8b", n_results=5)
    
    stats = vector_store.get_stats()
    print(f"✓ Ready! ({stats['total_chunks']} chunks indexed)")
    
    print_header()
    
    show_sources = True
    
    while True:
        # Get user input
        try:
            question = input("💬 Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break
        
        # Handle commands
        if question.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break
        
        if question.lower() == 'sources':
            show_sources = not show_sources
            status = "ON" if show_sources else "OFF"
            print(f"\n✓ Source display: {status}\n")
            continue
        
        if not question:
            continue
        
        # Process question
        print("\n🔍 Searching knowledge base...")
        result = rag.query(question, verbose=False)
        
        print_answer(result, show_sources=show_sources)

if __name__ == '__main__':
    main()