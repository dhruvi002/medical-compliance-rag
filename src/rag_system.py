# src/rag_system.py
import os
from typing import List, Dict, Optional
from vector_store import VectorStore
import ollama

class RAGSystem:
    """Complete RAG system for medical compliance Q&A"""
    
    def __init__(self, 
                 vector_store: VectorStore,
                 model_name: str = "llama3.1:8b",
                 n_results: int = 5):
        """
        Initialize RAG system
        
        Args:
            vector_store: Initialized VectorStore instance
            model_name: Ollama model to use
            n_results: Number of chunks to retrieve
        """
        self.vector_store = vector_store
        self.model_name = model_name
        self.n_results = n_results
        
        # Test Ollama connection
        try:
            ollama.list()
            print(f"✓ Connected to Ollama (using {model_name})")
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            print("Make sure Ollama is running: `ollama serve`")
            raise
    
    def retrieve_context(self, query: str) -> tuple[List[str], List[Dict]]:
        """
        Retrieve relevant chunks for a query
        
        Returns:
            (documents, metadata) tuple
        """
        results = self.vector_store.query(query, n_results=self.n_results)
        
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        
        return documents, metadatas
    
    def build_prompt(self, query: str, context_docs: List[str], context_metadata: List[Dict]) -> str:
        """
        Build prompt with retrieved context
        
        Args:
            query: User question
            context_docs: Retrieved document chunks
            context_metadata: Metadata for each chunk
        
        Returns:
            Formatted prompt string
        """
        # Build context section with source citations
        context_parts = []
        for i, (doc, meta) in enumerate(zip(context_docs, context_metadata), 1):
            source = meta.get('source_file', 'Unknown')
            context_parts.append(f"[Source {i}: {source}]\n{doc}")
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        prompt = f"""You are a medical compliance expert assistant. Answer the question based ONLY on the provided context from official compliance documents.

CONTEXT:
{context}

QUESTION: {query}

INSTRUCTIONS:
1. Provide a clear, actionable answer based on the context above
2. Cite specific sources using [Source X] notation
3. If the context mentions specific regulations (e.g., OSHA 1910.1030, HIPAA Privacy Rule), include them
4. If the context doesn't contain enough information to fully answer the question, say so
5. Be concise but thorough
6. Use bullet points for multi-step procedures

ANSWER:"""
        
        return prompt
    
    def generate_answer(self, prompt: str, temperature: float = 0.1) -> Dict:
        """
        Generate answer using Ollama
        
        Args:
            prompt: Complete prompt with context
            temperature: LLM temperature (lower = more deterministic)
        
        Returns:
            Dict with 'answer' and 'model' keys
        """
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'num_predict': 500,  # Max tokens to generate
                }
            )
            
            return {
                'answer': response['response'],
                'model': self.model_name
            }
        
        except Exception as e:
            return {
                'answer': f"Error generating response: {str(e)}",
                'model': self.model_name
            }
    
    def query(self, question: str, verbose: bool = False) -> Dict:
        """
        Complete RAG pipeline: retrieve + generate
        
        Args:
            question: User's question
            verbose: If True, print intermediate steps
        
        Returns:
            Dict with answer, sources, and metadata
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"QUERY: {question}")
            print(f"{'='*60}")
        
        # Step 1: Retrieve relevant chunks
        if verbose:
            print("\n[1/3] Retrieving relevant documents...")
        
        context_docs, context_metadata = self.retrieve_context(question)
        
        if verbose:
            print(f"  ✓ Retrieved {len(context_docs)} relevant chunks")
            for i, meta in enumerate(context_metadata, 1):
                print(f"    {i}. {meta.get('source_file', 'Unknown')}")
        
        # Step 2: Build prompt
        if verbose:
            print("\n[2/3] Building prompt with context...")
        
        prompt = self.build_prompt(question, context_docs, context_metadata)
        
        if verbose:
            print(f"  ✓ Prompt built ({len(prompt)} characters)")
        
        # Step 3: Generate answer
        if verbose:
            print(f"\n[3/3] Generating answer with {self.model_name}...")
        
        result = self.generate_answer(prompt)
        
        if verbose:
            print(f"  ✓ Answer generated")
        
        # Compile full response
        return {
            'question': question,
            'answer': result['answer'],
            'sources': [
                {
                    'file': meta.get('source_file', 'Unknown'),
                    'chunk_id': meta.get('chunk_id', 'Unknown'),
                    'preview': doc[:200] + '...' if len(doc) > 200 else doc
                }
                for doc, meta in zip(context_docs, context_metadata)
            ],
            'model': result['model'],
            'num_sources': len(context_docs)
        }
    
    def batch_query(self, questions: List[str], verbose: bool = False) -> List[Dict]:
        """
        Process multiple questions
        
        Args:
            questions: List of questions
            verbose: Print progress
        
        Returns:
            List of response dicts
        """
        results = []
        
        for i, question in enumerate(questions, 1):
            if verbose:
                print(f"\n\n{'#'*60}")
                print(f"PROCESSING QUESTION {i}/{len(questions)}")
                print(f"{'#'*60}")
            
            result = self.query(question, verbose=verbose)
            results.append(result)
        
        return results


def main():
    """Test the RAG system"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Initialize vector store
    print("Initializing vector store...")
    persist_dir = os.path.join(script_dir, '../chroma_db')
    vector_store = VectorStore(persist_directory=persist_dir)
    
    stats = vector_store.get_stats()
    print(f"✓ Vector store loaded ({stats['total_chunks']} chunks)")
    
    # Initialize RAG system
    print("\nInitializing RAG system...")
    rag = RAGSystem(vector_store, model_name="llama3.1:8b", n_results=5)
    
    # Test questions
    test_questions = [
        "What should I do immediately after a needlestick injury?",
        "What are the hand hygiene requirements in healthcare settings?",
        "How should I dispose of contaminated sharps?",
    ]
    
    print(f"\n{'='*60}")
    print("TESTING RAG SYSTEM")
    print(f"{'='*60}")
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n\n{'='*60}")
        print(f"TEST {i}/{len(test_questions)}")
        print(f"{'='*60}")
        
        result = rag.query(question, verbose=True)
        
        print(f"\n{'─'*60}")
        print("ANSWER:")
        print(f"{'─'*60}")
        print(result['answer'])
        
        print(f"\n{'─'*60}")
        print("SOURCES:")
        print(f"{'─'*60}")
        for j, source in enumerate(result['sources'], 1):
            print(f"{j}. {source['file']}")


if __name__ == '__main__':
    main()