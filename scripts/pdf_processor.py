import PyPDF2
import os
import json

def extract_pdf_text(pdf_path):
    """Extract text from PDF file with better error handling"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                try:
                    reader.decrypt('')
                except:
                    return None, "encrypted"
            
            text = []
            total_pages = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text.append(page_text)
                except Exception as e:
                    print(f"    Warning: Could not extract page {i+1}")
                    continue
            
            full_text = '\n\n'.join(text)
            
            # Check if we got meaningful content
            if len(full_text.strip()) < 100:
                return None, "no_text"
            
            return full_text, "success"
            
    except Exception as e:
        return None, f"error: {str(e)}"

def process_all_pdfs(input_dir='../data/raw', output_dir='../data/processed'):
    """Process all PDFs in directory with detailed reporting"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, input_dir)
    output_path = os.path.join(script_dir, output_dir)
    
    os.makedirs(output_path, exist_ok=True)
    
    documents = []
    pdf_files = sorted([f for f in os.listdir(input_path) if f.endswith('.pdf')])
    
    print(f"Found {len(pdf_files)} PDF files\n")
    
    stats = {
        'success': 0,
        'no_text': 0,
        'encrypted': 0,
        'error': 0
    }
    
    for filename in pdf_files:
        print(f"Processing {filename}...")
        pdf_path = os.path.join(input_path, filename)
        text, status = extract_pdf_text(pdf_path)
        
        if text:
            word_count = len(text.split())
            doc = {
                'filename': filename,
                'source': 'government_compliance',
                'content': text,
                'metadata': {
                    'type': 'guideline',
                    'word_count': word_count,
                    'char_count': len(text)
                }
            }
            documents.append(doc)
            stats['success'] += 1
            print(f"  ✓ Extracted {word_count:,} words")
        else:
            stats[status.split(':')[0]] += 1
            print(f"  ✗ Failed: {status}")
    
    # Save as JSON
    output_file = os.path.join(output_path, 'documents.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {stats['success']}")
    print(f"⚠️  No text content found: {stats['no_text']}")
    print(f"🔒 Encrypted PDFs: {stats['encrypted']}")
    print(f"❌ Errors: {stats['error']}")
    
    if documents:
        total_words = sum(d['metadata']['word_count'] for d in documents)
        avg_words = total_words // len(documents)
        print(f"\n📊 Total words extracted: {total_words:,}")
        print(f"📊 Average words per document: {avg_words:,}")
    
    print(f"\n📁 Saved to: {output_file}")
    
    return documents

if __name__ == '__main__':
    process_all_pdfs()