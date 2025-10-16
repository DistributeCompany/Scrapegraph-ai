from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import time

def setup_driver(headless=True, wait_time=15):
    """
    Set up Chrome WebDriver with appropriate options
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # Additional options for better compatibility
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(wait_time)
    
    return driver

def extract_author_info(soup):
    """
    Extract author information from Mendix containers
    """
    author_info = {}
    
    # Look for the specific div with author information
    author_div = soup.find('div', class_='mx-name-container2 row-left spacing-outer-top')
    if author_div:
        text_span = author_div.find('span', class_='mx-text mx-name-text4')
        if text_span:
            author_text = text_span.get_text(strip=True)
            author_info['raw_text'] = author_text
            
            # Parse the text (format: "Author · Date · Language")
            parts = [part.strip() for part in author_text.split('·')]
            if len(parts) >= 3:
                author_info['author'] = parts[0]
                author_info['date'] = parts[1]
                author_info['language'] = parts[2]
            elif len(parts) == 2:
                author_info['author'] = parts[0]
                author_info['date_or_language'] = parts[1]
            else:
                author_info['content'] = author_text
    
    return author_info

def extract_mendix_containers(soup):
    """
    Extract all Mendix-related containers and components
    """
    containers = []
    
    # Find all divs with mx- classes
    mx_divs = soup.find_all('div', class_=lambda x: x and 'mx-' in str(x))
    
    for div in mx_divs:
        container = {
            'classes': div.get('class', []),
            'text': div.get_text(strip=True),
            'tag': div.name
        }
        
        # Get any child spans or other elements
        child_elements = []
        for child in div.find_all(['span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if child.get_text(strip=True):
                child_elements.append({
                    'tag': child.name,
                    'classes': child.get('class', []),
                    'text': child.get_text(strip=True)
                })
        
        if child_elements:
            container['children'] = child_elements
            
        if container['text']:  # Only add if there's actual content
            containers.append(container)
    
    return containers

def scrape_author_div_specifically(url, wait_time=15000, headless=True):
    """
    Specifically target and scrape the author information div
    """
    driver = None
    
    try:
        driver = setup_driver(headless=headless, wait_time=wait_time//1000)
        
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(3)
        
        # Try to find the specific div using multiple strategies
        author_info = {}
        
        # Strategy 1: Find by exact class combination
        try:
            author_element = driver.find_element(By.CSS_SELECTOR, 
                "div.mx-name-container2.row-left.spacing-outer-top span.mx-text.mx-name-text4")
            if author_element:
                author_info['method'] = 'exact_css_selector'
                author_info['text'] = author_element.text
        except:
            pass
        
        # Strategy 2: Find by partial class names
        if not author_info:
            try:
                author_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='mx-name-container2']")
                for elem in author_elements:
                    text = elem.text.strip()
                    if text and ('·' in text or 'April' in text or 'English' in text):
                        author_info['method'] = 'partial_class_search'
                        author_info['text'] = text
                        break
            except:
                pass
        
        # Strategy 3: Search for text patterns
        if not author_info:
            try:
                # Look for elements containing the expected pattern
                elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Gerrits') or contains(text(), 'April 2016') or contains(text(), 'English')]")
                for elem in elements:
                    text = elem.text.strip()
                    if '·' in text:
                        author_info['method'] = 'xpath_text_search'
                        author_info['text'] = text
                        author_info['element_tag'] = elem.tag_name
                        author_info['element_classes'] = elem.get_attribute('class')
                        break
            except:
                pass
        
        # Get full page source for BeautifulSoup analysis
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Use BeautifulSoup as backup
        if not author_info:
            bs_result = extract_author_info(soup)
            if bs_result:
                author_info.update(bs_result)
                author_info['method'] = 'beautifulsoup_backup'
        
        # Also get all Mendix containers for context
        #mendix_containers = extract_mendix_containers(soup)
        mendix_containers = ""
        result = {
            "url": url,
            "target_div_found": bool(author_info),
            "author_info": author_info,
            "all_mendix_containers": mendix_containers,
            "page_title": soup.title.string if soup.title else "No title"
        }
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to scrape {url}: {str(e)}"}
    
    finally:
        if driver:
            driver.quit()
            
def scrape_with_selenium(url, wait_for_element="#content", wait_time=15000, headless=True):
    """
    Scrape a website using Selenium and BeautifulSoup
    
    Args:
        url: Target URL
        wait_for_element: CSS selector to wait for (default: "#content")
        wait_time: Time to wait in milliseconds (default: 15000)
        headless: Run browser in headless mode (default: True)
    """
    driver = None
    
    try:
        # Setup driver
        driver = setup_driver(headless=headless, wait_time=wait_time//1000)
        
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for specific element if provided
        if wait_for_element:
            try:
                print(f"Waiting for element: {wait_for_element}")
                wait = WebDriverWait(driver, wait_time//1000)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element)))
                print("Element found!")
            except Exception as e:
                print(f"Warning: Could not find element {wait_for_element}, continuing anyway...")
        
        # Additional wait to ensure JavaScript execution
        time.sleep(2)
        
        # Get page source after JavaScript execution
        page_source = driver.page_source
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract comprehensive information
        result = analyze_website_content(soup, url)
        
        return result
        
    except Exception as e:
        return {"error": f"Failed to scrape {url}: {str(e)}"}
    
    finally:
        if driver:
            driver.quit()

def analyze_website_content(soup, url):
    """
    Analyze the website content and return structured information
    """
    result = {
        "url": url,
        "title": soup.title.string.strip() if soup.title and soup.title.string else "No title found",
        "meta_description": "",
        "headings": {
            "h1": [h.get_text(strip=True) for h in soup.find_all('h1') if h.get_text(strip=True)],
            "h2": [h.get_text(strip=True) for h in soup.find_all('h2') if h.get_text(strip=True)],
            "h3": [h.get_text(strip=True) for h in soup.find_all('h3') if h.get_text(strip=True)],
            "h4": [h.get_text(strip=True) for h in soup.find_all('h4') if h.get_text(strip=True)]
        },
        "main_content": "",
        "paragraphs": [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)],
        "lists": {
            "unordered": [ul.get_text(strip=True) for ul in soup.find_all('ul')],
            "ordered": [ol.get_text(strip=True) for ol in soup.find_all('ol')]
        },
        "links": [],
        "images": [],
        "forms": len(soup.find_all('form')),
        "scripts": len(soup.find_all('script')),
        "total_text_length": len(soup.get_text(strip=True)),
        "content_summary": ""
    }
    
    # Get meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        result["meta_description"] = meta_desc.get('content', '')
    
    # Extract main content (try different common containers)
    content_selectors = ['#content', '.content', 'main', 'article', '.main-content', '.post-content']
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            result["main_content"] = content_elem.get_text(strip=True)
            break
    
    # If no specific content container found, use body
    if not result["main_content"]:
        body = soup.find('body')
        if body:
            result["main_content"] = body.get_text(strip=True)[:1000] + "..." if len(body.get_text(strip=True)) > 1000 else body.get_text(strip=True)
    
    # Extract links
    for link in soup.find_all('a', href=True):
        link_text = link.get_text(strip=True)
        if link_text:  # Only include links with text
            result["links"].append({
                "text": link_text,
                "url": link['href']
            })
    
    # Extract images
    for img in soup.find_all('img'):
        if img.get('src'):
            result["images"].append({
                "src": img['src'],
                "alt": img.get('alt', ''),
                "title": img.get('title', '')
            })
    
    # Generate content summary
    all_text = soup.get_text(strip=True)
    if all_text:
        # Simple summary - first few sentences or paragraphs
        sentences = all_text.split('.')[:3]
        result["content_summary"] = '. '.join(sentences).strip() + '.' if sentences else "No content summary available"
    
    return result

# Main execution
if __name__ == "__main__":
    # Configuration (equivalent to your original graph_config)
    config = {
        "headless": True,
        "wait_for": "#content",
        "wait_time": 15000  # 15 seconds
    }
    
    # URL to scrape
    url = "https://essay.utwente.nl/#/view/108870"
    
    # Run the scraper
    print("Starting Selenium scraper...")
    result = scrape_with_selenium(
        url=url,
        wait_for_element=config["wait_for"],
        wait_time=config["wait_time"],
        headless=config["headless"]
    )
    
    # Print results
    print("\nScraping Results:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
    
    # Example: Specifically target the author div
    print("\n" + "="*50)
    print("TARGETING SPECIFIC AUTHOR DIV:")
    print("="*50)
    
    author_result = scrape_author_div_specifically(url)
    print("Author Div Results:")
    print(json.dumps(author_result, indent=4, ensure_ascii=False))