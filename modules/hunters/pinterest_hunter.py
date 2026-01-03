import time
import uuid
import requests
import io
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from modules.integration.storage import get_storage_provider

class PinterestHunter:
    def __init__(self):
        self.storage = get_storage_provider()
        self.options = Options()
        # self.options.add_argument("--headless=new") # Commented out for visual debugging if needed, usually passed via env
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
    def hunt(self, query: str, limit: int = 10):
        print(f"🕵️‍♀️ [PinterestHunter] Starting hunt for: '{query}'")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)
        except Exception as e:
            print(f"⚠️ [PinterestHunter] Failed to init driver with manager, trying default: {e}")
            driver = webdriver.Chrome(options=self.options)
        
        results = []
        unique_urls = set()
        visited_raw_urls = set()

        try:
            # 1. Navigation
            search_url = f"https://www.pinterest.com/search/pins/?q={query}"
            driver.get(search_url)
            time.sleep(5) # Initial load wait

            # 2. Infinite Scroll
            scrolls = 0
            while len(results) < limit and scrolls < 10:
                print(f"📜 [PinterestHunter] Scrolling... ({scrolls+1})")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 4))
                
                # 3. Extraction
                images = driver.find_elements(By.TAG_NAME, "img")
                
                for img in images:
                    if len(results) >= limit:
                        break
                        
                    raw_src = img.get_attribute("src")
                    if not raw_src or raw_src in visited_raw_urls:
                        continue
                    visited_raw_urls.add(raw_src)

                    if "/75x75/" in raw_src or "/60x60/" in raw_src: # Skip tiny avatars
                        continue

                    # Generate candidates for best resolution
                    candidates = []
                    if "/236x/" in raw_src:
                        # Priority: Originals -> 564x -> 236x (fallback)
                        candidates.append(raw_src.replace("/236x/", "/originals/"))
                        candidates.append(raw_src.replace("/236x/", "/564x/"))
                        candidates.append(raw_src) 
                    else:
                        candidates.append(raw_src)

                    # Try downloading candidates
                    image_data = None
                    successful_url = None

                    for url in candidates:
                        if url in unique_urls: 
                            continue # Already captured this exact URL
                        
                        try:
                            # print(f"🔍 [PinterestHunter] Trying: {url}") # Verbose debugging
                            image_data = self._download_image(url)
                            successful_url = url
                            break # Success!
                        except Exception:
                            # print(f"⚠️ [PinterestHunter] Failed: {url}")
                            continue
                    
                    if not image_data or not successful_url:
                        continue

                    unique_urls.add(successful_url)
                    
                    # 4. Persistence
                    try:
                        print(f"📥 [PinterestHunter] Downloading: {successful_url}")
                        
                        file_name = f"pinterest_{uuid.uuid4().hex[:8]}.jpg"
                        stored_url = self.storage.upload_file(image_data, file_name)
                        
                        result = {
                            "s3_url": stored_url,
                            "source_url": successful_url,
                            "query": query,
                            "timestamp": datetime.now().isoformat()
                        }
                        results.append(result)
                        print(f"✅ [PinterestHunter] Saved: {stored_url}")
                        
                    except Exception as e:
                        print(f"⚠️ [PinterestHunter] Failed to save {successful_url}: {e}")
                        continue
                
                scrolls += 1
                
        except Exception as e:
            print(f"❌ [PinterestHunter] Critical error: {e}")
        finally:
            driver.quit()
        
        print(f"🏁 [PinterestHunter] Hunt finished. Captured {len(results)} assets.")
        return results

    def _download_image(self, url: str) -> io.BytesIO:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        return io.BytesIO(response.content)

if __name__ == "__main__":
    # Test execution
    hunter = PinterestHunter()
    hunter.hunt("Summer 2025 Fashion Trends", limit=3)
