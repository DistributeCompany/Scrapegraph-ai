from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from ollama import chat, ChatResponse
import pickle
import csv
import time
import os
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

@dataclass
class EssayItem:
    """Data class to store essay information"""
    essay_id: int
    title: str
    url: str
    summary: str
    study: Optional[str]
    author: str
    publication_time: str
    language: str
    ollama_response: str
    included: bool  # Whether it should be included based on Ollama
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class EssayScraper:
    def __init__(self, cache_file='essay_cache.pkl', csv_file='essays.csv', 
                 headless=True, wait_time=15):
        self.cache_file = cache_file
        self.csv_file = csv_file
        self.headless = headless
        self.wait_time = wait_time
        self.cache = self.load_cache()
        self.driver = None
        self.failed_ids = []
        
    def load_cache(self):
        """Load existing cache from pickle file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                print(f"✓ Loaded cache with {len(cache)} existing items")
                return cache
            except Exception as e:
                print(f"⚠ Could not load cache: {e}")
                return {}
        return {}
    
    def save_cache(self, items_dict):
        """Save cache to pickle file"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(items_dict, f)
            print(f"✓ Cache saved ({len(items_dict)} items)")
        except Exception as e:
            print(f"✗ Failed to save cache: {e}")
    
    def save_to_csv(self, items_dict):
        """Save all items to CSV file"""
        try:
            items = list(items_dict.values())
            if not items:
                return
            
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=asdict(items[0]).keys())
                writer.writeheader()
                for item in items:
                    writer.writerow(asdict(item))
            print(f"✓ CSV saved with {len(items)} items")
        except Exception as e:
            print(f"✗ Failed to save CSV: {e}")
    
    def setup_driver(self):
        """Set up Chrome WebDriver"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(self.wait_time)
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def scrape_essay_page(self, essay_id):
        """Scrape a single essay page"""
        url = f"https://essay.utwente.nl/#/view/{essay_id}"
        
        try:
            # Navigate to blank page first to force clean reload
            self.driver.get("about:blank")
            time.sleep(0.5)
            
            # Now navigate to target page
            self.driver.get(url)
            
            # Wait longer for SPA to load
            time.sleep(5)
            
            # Additional wait for dynamic content
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except:
                pass
            
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract title (h1)
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                return None, "No title found"
            
            print(f"Title: {title[:80]}..., url: {url}")  # Debug print
            
            # Extract paragraphs
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
            
            if not paragraphs:
                return None, "No paragraphs found"
            
            # Extract study (last paragraph if it contains Master or Bachelor)
            study = None
            if paragraphs and ('Master' in paragraphs[-1] or 'Bachelor' in paragraphs[-1]):
                study = paragraphs[-1]
                summary_paragraphs = paragraphs[:-1]
            else:
                summary_paragraphs = paragraphs
            
            # Create summary (exclude last item)
            summary = ' '.join(summary_paragraphs)
            
            # Extract author info
            try:
                author_element = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "div.mx-name-container2.row-left.spacing-outer-top span.mx-text.mx-name-text4"
                )
                author_text = author_element.text if author_element else ""
            except:
                author_text = ""
            
            if not author_text:
                return None, "No author information found"
            
            # Parse author information (format: "Author · Date · Language")
            parts = [part.strip() for part in author_text.split('·')]
            
            if len(parts) >= 3:
                author = parts[0]
                publication_time = parts[1]
                language = parts[2]
            elif len(parts) == 2:
                author = parts[0]
                publication_time = parts[1]
                language = "Unknown"
            else:
                author = author_text
                publication_time = "Unknown"
                language = "Unknown"
            
            return {
                'title': title,
                'url': url,
                'summary': summary,
                'study': study,
                'author': author,
                'publication_time': publication_time,
                'language': language
            }, None
            
        except Exception as e:
            return None, f"Scraping error: {str(e)}"       
        
    def ask_ollama(self, title, summary):
        """Ask Ollama if the essay is related to Transport & Logistics"""
        try:
            prompt = f"""Given the following text, only answer Yes for texts that are directly related to the domain of Transport & Logistics. First output a Yes or a No and then continue with the reasoning whether I should include it in a 'Transport and Logistics' repository.

Title: {title}

Summary: {summary[:5000]}"""  # Limit summary length
            
            response: ChatResponse = chat(
                model='llama3.2:latest',
                messages=[{'role': 'user', 'content': prompt}],
                stream=False,
            )
            
            response_text = response['message']['content']
            
            # Determine if it's a Yes
            response_lower = response_text.lower()
            included = 'yes' in response_lower[:10] and 'no' not in response_lower.split('yes')[0]
            
            return response_text.strip(), included
            
        except Exception as e:
            print(f"  ⚠ Ollama error: {e}")
            return f"Error: {str(e)}", False
    
    def process_essays(self, start_id=108670, count=100):
        """Process multiple essays"""
        print(f"\n{'='*60}")
        print(f"Starting essay processing")
        print(f"Start ID: {start_id}, Count: {count}")
        print(f"{'='*60}\n")
        
        # Determine which IDs to process
        ids_to_process = list(range(start_id, start_id - count, -1))
        
        # Filter out already processed IDs
        new_ids = [id for id in ids_to_process if id not in self.cache]
        
        if len(new_ids) < len(ids_to_process):
            print(f"ℹ Skipping {len(ids_to_process) - len(new_ids)} already processed IDs")
        
        if not new_ids:
            print("✓ All requested IDs are already in cache!")
            return
        
        print(f"Processing {len(new_ids)} new essays...\n")
        
        # Setup driver
        self.setup_driver()
        
        processed_count = 0
        included_count = 0
        
        try:
            for i, essay_id in enumerate(new_ids, 1):
                print(f"[{i}/{len(new_ids)}] Processing ID {essay_id}...", end=' ')
                
                # Scrape the essay
                essay_data, error = self.scrape_essay_page(essay_id)
                

                if error:
                    print(f"✗ {error}")
                    self.failed_ids.append((essay_id, error))
                    
                    # Create simple EssayItem
                    essay_item = EssayItem(
                        essay_id=essay_id,
                        title='N/A',
                        url='N/A',
                        summary='N/A',
                        study='N/A',
                        author='N/A',
                        publication_time='N/A',
                        language='N/A',
                        ollama_response='N/A',
                        included=False
                    )

                    # Add to cache
                    self.cache[essay_id] = essay_item
                    processed_count += 1
                    continue
                
                print(f"✓ Scraped", end=' ')
                
                # Ask Ollama
                ollama_response, included = self.ask_ollama(
                    essay_data['title'], 
                    essay_data['summary']
                )
                
                # Create EssayItem
                essay_item = EssayItem(
                    essay_id=essay_id,
                    title=essay_data['title'],
                    url=essay_data['url'],
                    summary=essay_data['summary'],
                    study=essay_data['study'],
                    author=essay_data['author'],
                    publication_time=essay_data['publication_time'],
                    language=essay_data['language'],
                    ollama_response=ollama_response,
                    included=included
                )
                
                # Add to cache
                self.cache[essay_id] = essay_item
                processed_count += 1
                
                if included:
                    included_count += 1
                    print(f"→ ✓ INCLUDED")
                else:
                    print(f"→ ✗ Excluded")
                
                # Save every 50 items
                if processed_count % 50 == 0:
                    print(f"\n→ Intermediate save at {processed_count} items...")
                    self.save_cache(self.cache)
                    self.save_to_csv(self.cache)
                    print()
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.5)
                
        finally:
            self.close_driver()
        
        # Final save
        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"Processed: {processed_count}")
        print(f"Included: {included_count}")
        print(f"Failed: {len(self.failed_ids)}")
        print(f"{'='*60}\n")
        
        if self.failed_ids:
            print("Failed IDs:")
            for essay_id, error in self.failed_ids:
                print(f"  - {essay_id}: {error}")
            print()
        
        # Save final results
        self.save_cache(self.cache)
        self.save_to_csv(self.cache)
        
        print(f"✓ Results saved to {self.cache_file} and {self.csv_file}")
    
    def get_included_essays(self):
        """Get all essays marked as included"""
        return [item for item in self.cache.values() if item.included]
    
    def print_statistics(self):
        """Print statistics about the cache"""
        if not self.cache:
            print("No items in cache")
            return
        
        total = len(self.cache)
        included = sum(1 for item in self.cache.values() if item.included)
        
        print(f"\n{'='*60}")
        print(f"Cache Statistics")
        print(f"{'='*60}")
        print(f"Total essays: {total}")
        print(f"Included (Transport & Logistics): {included}")
        print(f"Excluded: {total - included}")
        print(f"Inclusion rate: {included/total*100:.1f}%")
        print(f"{'='*60}\n")

# Main execution
if __name__ == "__main__":
    # Configuration
    START_ID = 108871
    COUNT = 5000
    CACHE_FILE = 'essay_cache.pkl'
    CSV_FILE = 'essays.csv'
    
    # Create scraper instance
    scraper = EssayScraper(
        cache_file=CACHE_FILE,
        csv_file=CSV_FILE,
        headless=True,
        wait_time=15
    )
    
    # Process essays
    scraper.process_essays(start_id=START_ID, count=COUNT)
    
    # Print statistics
    scraper.print_statistics()
    
    # Example: Get all included essays
    included_essays = scraper.get_included_essays()
    print(f"\nFound {len(included_essays)} essays related to Transport & Logistics")
    
    # Example: Print first few included essays
    if included_essays:
        print("\nFirst few included essays:")
        for essay in included_essays[:3]:
            print(f"\n- ID: {essay.essay_id}")
            print(f"  Title: {essay.title[:80]}...")
            print(f"  Author: {essay.author}")
            print(f"  Date: {essay.publication_time}")