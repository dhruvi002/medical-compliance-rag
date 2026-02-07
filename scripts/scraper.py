# scripts/scraper.py
import requests
from bs4 import BeautifulSoup
import json
import os
import time

articles = [
    "https://en.wikipedia.org/wiki/HIPAA",
    "https://en.wikipedia.org/wiki/Occupational_Safety_and_Health_Administration",
    "https://en.wikipedia.org/wiki/Medical_waste",
    "https://en.wikipedia.org/wiki/Infection_control",
    "https://en.wikipedia.org/wiki/Needlestick_injury",
    "https://en.wikipedia.org/wiki/Personal_protective_equipment",
    "https://en.wikipedia.org/wiki/Hand_hygiene",
    "https://en.wikipedia.org/wiki/Healthcare-associated_infection",
    "https://en.wikipedia.org/wiki/Sharps_waste",
    "https://en.wikipedia.org/wiki/Universal_precautions"
]

def scrape_wikipedia(url):
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title - try multiple methods
        title = None
        if soup.find('h1', class_='firstHeading'):
            title = soup.find('h1', class_='firstHeading').text
        elif soup.find('h1'):
            title = soup.find('h1').text
        else:
            title = url.split('/')[-1].replace('_', ' ')
        
        # Extract main content paragraphs
        content = []
        # Focus on content div to avoid navigation text
        content_div = soup.find('div', class_='mw-parser-output')
        if content_div:
            paragraphs = content_div.find_all('p')
        else:
            paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            text = p.get_text().strip()
            # Filter out short paragraphs and remove citation brackets
            if len(text) > 100:
                # Clean up text
                text = text.replace('[edit]', '').strip()
                content.append(text)
        
        full_content = '\n\n'.join(content[:20])  # First 20 paragraphs
        
        return {
            'title': title,
            'source': url,
            'content': full_content,
            'word_count': len(full_content.split())
        }
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None

if __name__ == '__main__':
    # Get proper path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, '../data/processed')
    os.makedirs(output_dir, exist_ok=True)
    
    # Scrape and save
    docs = []
    print(f"Scraping {len(articles)} Wikipedia articles...\n")
    
    for i, url in enumerate(articles, 1):
        article_name = url.split('/')[-1].replace('_', ' ')
        print(f"[{i}/{len(articles)}] Scraping {article_name}...")
        doc = scrape_wikipedia(url)
        if doc:
            docs.append(doc)
            print(f"  ✓ Extracted {doc['word_count']} words")
        else:
            print(f"  ✗ Failed")
        time.sleep(1)  # Be polite to Wikipedia
    
    # Save to JSON
    output_file = os.path.join(output_dir, 'wikipedia_compliance.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Successfully scraped {len(docs)}/{len(articles)} articles")
    print(f"📁 Saved to: {output_file}")