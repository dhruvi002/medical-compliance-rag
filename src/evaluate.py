# src/evaluate.py
import json
import os
from vector_store import VectorStore
from rag_system import RAGSystem
from typing import List, Dict
import time

def load_test_questions(filepath: str) -> List[Dict]:
    """Load synthetic Q&A pairs"""
    with open(filepath, 'r', encoding='utf-8') as f:
        qa_pairs = json.load(f)
    return qa_pairs

def evaluate_rag(rag: RAGSystem, qa_pairs: List[Dict], sample_size: int = None) -> Dict:
    """
    Evaluate RAG system on Q&A pairs
    
    Args:
        rag: RAGSystem instance
        qa_pairs: List of Q&A dicts
        sample_size: If set, only test this many questions
    
    Returns:
        Evaluation results dict
    """
    if sample_size:
        qa_pairs = qa_pairs[:sample_size]
    
    print(f"\n{'='*60}")
    print(f"EVALUATING RAG SYSTEM")
    print(f"{'='*60}")
    print(f"Test set size: {len(qa_pairs)} questions")
    print(f"Model: {rag.model_name}")
    print(f"Retrieval: Top-{rag.n_results} chunks")
    print(f"{'='*60}\n")
    
    results = []
    categories = {}
    
    start_time = time.time()
    
    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        expected_answer = qa.get('answer', '')
        category = qa.get('category', 'Unknown')
        
        print(f"[{i}/{len(qa_pairs)}] {category}: {question[:60]}...")
        
        # Query RAG system
        result = rag.query(question, verbose=False)
        
        # Track by category
        if category not in categories:
            categories[category] = []
        categories[category].append(result)
        
        # Store result
        results.append({
            'question': question,
            'category': category,
            'difficulty': qa.get('difficulty', 'unknown'),
            'expected_answer': expected_answer,
            'generated_answer': result['answer'],
            'sources': result['sources'],
            'num_sources': result['num_sources']
        })
        
        # Brief pause to avoid overwhelming Ollama
        time.sleep(0.5)
    
    elapsed_time = time.time() - start_time
    
    # Summary stats
    print(f"\n{'='*60}")
    print("EVALUATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total questions: {len(results)}")
    print(f"Time taken: {elapsed_time:.2f} seconds")
    print(f"Avg time per question: {elapsed_time/len(results):.2f} seconds")
    print(f"\nQuestions by category:")
    for cat, cat_results in sorted(categories.items()):
        print(f"  {cat}: {len(cat_results)}")
    
    return {
        'results': results,
        'categories': categories,
        'total_questions': len(results),
        'elapsed_time': elapsed_time,
        'avg_time': elapsed_time / len(results)
    }

def save_evaluation_results(evaluation: Dict, output_file: str):
    """Save evaluation results to JSON"""
    # Create simplified version for JSON serialization
    save_data = {
        'total_questions': evaluation['total_questions'],
        'elapsed_time': evaluation['elapsed_time'],
        'avg_time': evaluation['avg_time'],
        'results': evaluation['results']
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Results saved to: {output_file}")

def print_sample_results(results: List[Dict], n=3):
    """Print sample Q&A results"""
    print(f"\n{'='*60}")
    print(f"SAMPLE RESULTS (showing {n} examples)")
    print(f"{'='*60}")
    
    for i, result in enumerate(results[:n], 1):
        print(f"\n{'─'*60}")
        print(f"EXAMPLE {i}")
        print(f"{'─'*60}")
        print(f"Category: {result['category']}")
        print(f"Question: {result['question']}")
        print(f"\nGenerated Answer:")
        print(result['generated_answer'])
        print(f"\nSources: {result['num_sources']} documents")
        for j, source in enumerate(result['sources'][:3], 1):
            print(f"  {j}. {source['file']}")

def main():
    """Run evaluation"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load test Q&As
    qa_file = os.path.join(script_dir, '../data/processed/synthetic_qa_combined.json')
    print(f"Loading test questions from {qa_file}...")
    qa_pairs = load_test_questions(qa_file)
    print(f"✓ Loaded {len(qa_pairs)} Q&A pairs")
    
    # Initialize RAG system
    print("\nInitializing RAG system...")
    persist_dir = os.path.join(script_dir, '../chroma_db')
    vector_store = VectorStore(persist_directory=persist_dir)
    rag = RAGSystem(vector_store, model_name="llama3.1:8b", n_results=5)
    print("✓ RAG system ready")
    
    # Run evaluation (start with sample for testing)
    print("\n" + "="*60)
    response = input("Run full evaluation (60 questions) or sample (10)? [full/sample]: ")
    
    if response.lower() == 'sample':
        sample_size = 10
    else:
        sample_size = None
    
    evaluation = evaluate_rag(rag, qa_pairs, sample_size=sample_size)
    
    # Print sample results
    print_sample_results(evaluation['results'], n=3)
    
    # Save results
    output_file = os.path.join(script_dir, '../data/processed/evaluation_results.json')
    save_evaluation_results(evaluation, output_file)
    
    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print("1. Review the sample results above")
    print("2. Check full results in: data/processed/evaluation_results.json")
    print("3. If quality is good, run full evaluation with all 60 questions")
    print("4. Use results to measure system performance for your portfolio")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()