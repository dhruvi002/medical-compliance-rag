# src/vector_store.py
import json
import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import time

class VectorStore:
    """Manage ChromaDB vector database for RAG"""
    
    def __init__(self, persist_directory='./chroma_db', collection_name='medical_compliance'):
        """
        Initialize ChromaDB client and collection
        
        Args:
            persist_directory: Where to store the database
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Medical compliance documents for RAG"}
        )
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print("✓ Embedding model loaded")
    
    def generate_embeddings(self, texts: List[str], batch_size=32) -> List[List[float]]:
        """Generate embeddings for texts in batches"""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.embedding_model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_embeddings.tolist())
            
            if (i + batch_size) % 100 == 0:
                print(f"  Generated embeddings for {min(i+batch_size, len(texts))}/{len(texts)} chunks")
        
        return embeddings
    
    def add_chunks(self, chunks: List[Dict]):
        """
        Add document chunks to vector store
        
        Args:
            chunks: List of dicts with 'content' and 'metadata'
        """
        print(f"\nAdding {len(chunks)} chunks to vector store...")
        
        # Prepare data
        ids = [chunk['metadata']['chunk_id'] for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.generate_embeddings(documents)
        
        # Add to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            self.collection.add(
                ids=ids[i:i+batch_size],
                embeddings=embeddings[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )
            print(f"  Added batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
        
        print(f"✅ Successfully added {len(chunks)} chunks to vector store")
    
    def query(self, query_text: str, n_results=5) -> Dict:
        """
        Query the vector store
        
        Args:
            query_text: Question to search for
            n_results: Number of results to return
        
        Returns:
            Dict with documents, metadatas, distances
        """
        # Generate embedding for query
        query_embedding = self.embedding_model.encode([query_text])[0].tolist()
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return results
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector store"""
        count = self.collection.count()
        return {
            'total_chunks': count,
            'collection_name': self.collection_name,
            'persist_directory': self.persist_directory
        }


def main():
    """Initialize vector store with chunks"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load chunks
    chunks_file = os.path.join(script_dir, '../data/processed/chunks.json')
    print(f"Loading chunks from {chunks_file}...")
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"Loaded {len(chunks)} chunks")
    
    # Initialize vector store
    persist_dir = os.path.join(script_dir, '../chroma_db')
    vector_store = VectorStore(persist_directory=persist_dir)
    
    # Check if already populated
    stats = vector_store.get_stats()
    if stats['total_chunks'] > 0:
        print(f"\n⚠️  Vector store already contains {stats['total_chunks']} chunks")
        response = input("Do you want to replace it? (yes/no): ")
        if response.lower() != 'yes':
            print("Skipping vector store creation")
            return
        
        # Delete and recreate collection
        vector_store.client.delete_collection(vector_store.collection_name)
        vector_store.collection = vector_store.client.create_collection(
            name=vector_store.collection_name,
            metadata={"description": "Medical compliance documents for RAG"}
        )
    
    # Add chunks to vector store
    start_time = time.time()
    vector_store.add_chunks(chunks)
    elapsed = time.time() - start_time
    
    # Print final stats
    stats = vector_store.get_stats()
    print(f"\n{'='*60}")
    print("VECTOR STORE CREATED")
    print(f"{'='*60}")
    print(f"Total chunks indexed: {stats['total_chunks']}")
    print(f"Time taken: {elapsed:.2f} seconds")
    print(f"Database location: {stats['persist_directory']}")
    
    # Test query
    print(f"\n{'='*60}")
    print("TESTING RETRIEVAL")
    print(f"{'='*60}")
    test_query = "What should I do after a needlestick injury?"
    print(f"Query: {test_query}")
    
    results = vector_store.query(test_query, n_results=3)
    
    print(f"\nTop 3 results:")
    for i, doc in enumerate(results['documents'][0]):
        print(f"\n[{i+1}] Source: {results['metadatas'][0][i]['source_file']}")
        print(f"    Preview: {doc[:150]}...")


if __name__ == '__main__':
    main()