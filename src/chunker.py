# src/chunker.py
import json
import os
from typing import List, Dict
import tiktoken

class DocumentChunker:
    """Split documents into chunks for embedding"""
    
    def __init__(self, chunk_size=500, chunk_overlap=50):
        """
        Args:
            chunk_size: Target tokens per chunk
            chunk_overlap: Overlapping tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def chunk_text(self, text: str, metadata: dict) -> List[Dict]:
        """
        Split text into chunks with overlap
        
        Returns:
            List of dicts with 'content' and 'metadata'
        """
        # Split by paragraphs first (double newline)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_tokens = self.count_tokens(para)
            
            # If single paragraph is too long, split it
            if para_tokens > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append({
                        'content': '\n\n'.join(current_chunk),
                        'metadata': metadata.copy()
                    })
                    current_chunk = []
                    current_tokens = 0
                
                # Split long paragraph by sentences
                sentences = para.split('. ')
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    
                    sent_tokens = self.count_tokens(sent)
                    
                    if current_tokens + sent_tokens > self.chunk_size:
                        if current_chunk:
                            chunks.append({
                                'content': '. '.join(current_chunk) + '.',
                                'metadata': metadata.copy()
                            })
                        current_chunk = [sent]
                        current_tokens = sent_tokens
                    else:
                        current_chunk.append(sent)
                        current_tokens += sent_tokens
                
                continue
            
            # Check if adding paragraph exceeds chunk size
            if current_tokens + para_tokens > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append({
                        'content': '\n\n'.join(current_chunk),
                        'metadata': metadata.copy()
                    })
                
                # Start new chunk with overlap
                # Keep last paragraph from previous chunk for context
                if current_chunk:
                    current_chunk = [current_chunk[-1], para]
                    current_tokens = self.count_tokens('\n\n'.join(current_chunk))
                else:
                    current_chunk = [para]
                    current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append({
                'content': '\n\n'.join(current_chunk),
                'metadata': metadata.copy()
            })
        
        return chunks
    
    def process_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Process all documents into chunks
        
        Args:
            documents: List of docs with 'content' and 'metadata'
        
        Returns:
            List of chunks with metadata
        """
        all_chunks = []
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            # Add document-level metadata
            metadata['doc_index'] = i
            metadata['source_file'] = doc.get('filename') or doc.get('title', f'doc_{i}')
            
            # Chunk the document
            chunks = self.chunk_text(content, metadata)
            
            # Add chunk-specific metadata
            for j, chunk in enumerate(chunks):
                chunk['metadata']['chunk_index'] = j
                chunk['metadata']['total_chunks'] = len(chunks)
                chunk['metadata']['chunk_id'] = f"{metadata['source_file']}_chunk_{j}"
            
            all_chunks.extend(chunks)
            
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(documents)} documents...")
        
        return all_chunks


def main():
    """Test chunking on your data"""
    # Load processed documents
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load PDFs
    pdf_file = os.path.join(script_dir, '../data/processed/documents.json')
    with open(pdf_file, 'r', encoding='utf-8') as f:
        pdf_docs = json.load(f)
    
    # Load Wikipedia
    wiki_file = os.path.join(script_dir, '../data/processed/wikipedia_compliance.json')
    with open(wiki_file, 'r', encoding='utf-8') as f:
        wiki_docs = json.load(f)
    
    # Combine all documents
    all_docs = pdf_docs + wiki_docs
    
    print(f"Loaded {len(all_docs)} documents")
    print(f"Starting chunking process...\n")
    
    # Create chunker
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
    
    # Process documents
    chunks = chunker.process_documents(all_docs)
    
    print(f"\n{'='*60}")
    print(f"CHUNKING COMPLETE")
    print(f"{'='*60}")
    print(f"Total documents: {len(all_docs)}")
    print(f"Total chunks created: {len(chunks)}")
    print(f"Average chunks per document: {len(chunks) // len(all_docs)}")
    
    # Sample chunk
    if chunks:
        print(f"\nSample chunk:")
        print(f"Source: {chunks[0]['metadata']['source_file']}")
        print(f"Chunk ID: {chunks[0]['metadata']['chunk_id']}")
        print(f"Content preview: {chunks[0]['content'][:200]}...")
        print(f"Token count: {chunker.count_tokens(chunks[0]['content'])}")
    
    # Save chunks
    output_file = os.path.join(script_dir, '../data/processed/chunks.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Saved chunks to: {output_file}")


if __name__ == '__main__':
    main()