from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os

def setup_driver_with_downloads(download_path=None, headless=True, wait_time=15):
    """
    Set up Chrome WebDriver with download capabilities
    """
    if download_path is None:
        download_path = os.path.join(os.getcwd(), "downloads")
    
    # Create download directory if it doesn't exist
    os.makedirs(download_path, exist_ok=True)
    
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # Download preferences
    prefs = {
        "download.default_directory": download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "plugins.always_open_pdf_externally": True  # Download PDFs instead of opening in browser
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Additional options for better compatibility
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(wait_time)
    
    return driver, download_path

def click_pdf_download(url, download_path=None, wait_time=15000, headless=True):
    """
    Click on the PDF download button with classes 'mx-name-container10 far fa-file-pdf'
    """
    driver = None
    
    try:
        driver, actual_download_path = setup_driver_with_downloads(download_path, headless, wait_time//1000)
        
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(3)
        
        # Get initial file count in download directory
        initial_files = set(os.listdir(actual_download_path)) if os.path.exists(actual_download_path) else set()
        
        # Strategy 1: Find by exact class combination
        pdf_element = None
        method_used = None
        
        try:
            # Look for element with all the specified classes
            pdf_element = driver.find_element(By.CSS_SELECTOR, ".mx-name-container10.far.fa-file-pdf")
            method_used = "exact_class_selector"
            print("Found PDF element using exact class selector")
        except:
            print("Exact class selector failed, trying alternative methods...")
        
        # Strategy 2: Find by partial class names
        if not pdf_element:
            try:
                pdf_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='mx-name-container10']")
                for elem in pdf_elements:
                    classes = elem.get_attribute('class')
                    if 'fa-file-pdf' in classes:
                        pdf_element = elem
                        method_used = "partial_class_search"
                        print("Found PDF element using partial class search")
                        break
            except:
                pass
        
        # Strategy 3: Search for FontAwesome PDF icon
        if not pdf_element:
            try:
                pdf_elements = driver.find_elements(By.CSS_SELECTOR, ".fa-file-pdf")
                if pdf_elements:
                    pdf_element = pdf_elements[0]  # Take the first one
                    method_used = "fontawesome_icon_search"
                    print("Found PDF element using FontAwesome icon search")
            except:
                pass
        
        # Strategy 4: Look for any clickable element with PDF-related attributes
        if not pdf_element:
            try:
                # Look for links or buttons that might trigger PDF download
                pdf_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'pdf') or contains(@href, '.pdf') or contains(@onclick, 'pdf')]")
                if pdf_elements:
                    pdf_element = pdf_elements[0]
                    method_used = "pdf_attribute_search"
                    print("Found PDF element using attribute search")
            except:
                pass
        
        if pdf_element:
            print(f"PDF element found! Method: {method_used}")
            print(f"Element tag: {pdf_element.tag_name}")
            print(f"Element classes: {pdf_element.get_attribute('class')}")
            print(f"Element text: {pdf_element.text}")
            
            # Scroll to element to ensure it's visible
            driver.execute_script("arguments[0].scrollIntoView(true);", pdf_element)
            time.sleep(1)
            
            # Try to click the element
            try:
                # Wait for element to be clickable
                wait = WebDriverWait(driver, 10)
                clickable_element = wait.until(EC.element_to_be_clickable(pdf_element))
                
                print("Clicking PDF download button...")
                clickable_element.click()
                
                # Wait for download to start/complete
                print("Waiting for download to complete...")
                download_completed = False
                max_wait_time = 30  # seconds
                wait_time = 0
                
                while wait_time < max_wait_time:
                    time.sleep(1)
                    wait_time += 1
                    
                    current_files = set(os.listdir(actual_download_path)) if os.path.exists(actual_download_path) else set()
                    new_files = current_files - initial_files
                    
                    # Check if any new files appeared
                    if new_files:
                        # Check if download is complete (no .crdownload files)
                        complete_files = [f for f in new_files if not f.endswith('.crdownload')]
                        if complete_files:
                            download_completed = True
                            downloaded_file = list(complete_files)[0]
                            break
                    
                    if wait_time % 5 == 0:
                        print(f"Still waiting... ({wait_time}s)")
                
                result = {
                    "success": True,
                    "method_used": method_used,
                    "download_completed": download_completed,
                    "download_path": actual_download_path,
                    "wait_time": wait_time
                }
                
                if download_completed:
                    result["downloaded_file"] = downloaded_file
                    result["full_file_path"] = os.path.join(actual_download_path, downloaded_file)
                    print(f"Download completed: {downloaded_file}")
                else:
                    result["message"] = "Click successful but download completion couldn't be verified"
                    print("Click successful but download completion couldn't be verified")
                
                return result
                
            except Exception as click_error:
                return {
                    "success": False,
                    "error": f"Failed to click PDF element: {str(click_error)}",
                    "element_found": True,
                    "method_used": method_used
                }
        
        else:
            # If no PDF element found, return information about available elements
            all_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='mx-name-container']")
            available_elements = []
            
            for elem in all_elements:
                available_elements.append({
                    "tag": elem.tag_name,
                    "classes": elem.get_attribute('class'),
                    "text": elem.text.strip()[:50] if elem.text else ""
                })
            
            return {
                "success": False,
                "error": "PDF download element not found",
                "available_mx_elements": available_elements,
                "search_strategies_tried": [
                    "exact_class_selector (.mx-name-container10.far.fa-file-pdf)",
                    "partial_class_search ([class*='mx-name-container10'])",
                    "fontawesome_icon_search (.fa-file-pdf)",
                    "pdf_attribute_search (PDF-related attributes)"
                ]
            }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to access {url}: {str(e)}"}
    
    finally:
        if driver:
            driver.quit()

def download_pdf_with_retry(url, download_path=None, max_retries=1):
    """
    Attempt to download PDF with multiple retries
    """
    for attempt in range(max_retries):
        print(f"\nAttempt {attempt + 1} of {max_retries}")
        result = click_pdf_download(url, download_path)
        
        if result.get("success"):
            return result
        else:
            print(f"Attempt {attempt + 1} failed: {result.get('error', 'Unknown error')}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(2)
    
    return {"success": False, "error": f"Failed after {max_retries} attempts"}

# Usage example:
if __name__ == "__main__":
    url = "https://essay.utwente.nl/#/view/108726"
    
    # Simple usage
    result = click_pdf_download(url)
    print("Download result:", result)
    
    # Or with custom download path and retry
    #custom_path = "/path/to/your/downloads"
    #result = download_pdf_with_retry(url, custom_path)
    #print("Download result with retry:", result)