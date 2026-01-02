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
        driver = webdriver.Chrome(options=self.options)
        
        results = []
        unique_urls = set()

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
                        
                    src = img.get_attribute("src")
                    if not src or src in unique_urls:
                        continue

                    # Filter: High resolution only (originals or 564x, exclude 236x thumbnails)
                    if "/236x/" in src or "/75x75/" in src:
                        continue
                    
                    # Try to upgrade resolution if possible
                    # Pinterest often has /236x/ which can be replaced by /564x/ or /originals/
                    # For now just accepting 564x+ or originals
                    if "/564x/" not in src and "/originals/" not in src:
                        continue

                    unique_urls.add(src)
                    
                    # 4. Persistence
                    try:
                        print(f"📥 [PinterestHunter] Downloading: {src}")
                        image_data = self._download_image(src)
                        
                        file_name = f"pinterest_{uuid.uuid4().hex[:8]}.jpg"
                        stored_url = self.storage.upload_file(image_data, file_name)
                        
                        result = {
                            "s3_url": stored_url,
                            "source_url": src, # Ideally we get the Pin URL, but image src is ok for now
                            "query": query,
                            "timestamp": datetime.now().isoformat()
                        }
                        results.append(result)
                        print(f"✅ [PinterestHunter] Saved: {stored_url}")
                        
                    except Exception as e:
                        print(f"⚠️ [PinterestHunter] Failed to download {src}: {e}")
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
