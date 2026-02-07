import json
import os
import glob

def merge_qa_batches():
    """Combine all synthetic Q&A batches into one file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    processed_dir = os.path.join(script_dir, '../data/processed')
    
    # Find all synthetic_qa files
    pattern = os.path.join(processed_dir, 'synthetic_*.json')
    qa_files = glob.glob(pattern)
    
    if not qa_files:
        print("❌ No synthetic Q&A files found!")
        return
    
    print(f"Found {len(qa_files)} Q&A batch files:")
    
    all_qa = []
    for filepath in qa_files:
        filename = os.path.basename(filepath)
        print(f"  - {filename}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            batch = json.load(f)
            all_qa.extend(batch)
    
    # Save combined file
    output_file = os.path.join(processed_dir, 'synthetic_qa_combined.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_qa, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n✅ Combined {len(all_qa)} total Q&A pairs")
    
    # Category breakdown
    categories = {}
    for qa in all_qa:
        cat = qa.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📊 Breakdown by category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    
    print(f"\n📁 Saved to: {output_file}")

if __name__ == '__main__':
    merge_qa_batches()