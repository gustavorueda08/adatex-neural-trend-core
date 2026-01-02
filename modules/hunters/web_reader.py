import newspaper
from datetime import datetime
from modules.integration.storage import get_storage_provider
import uuid

class WebReader:
    def __init__(self):
        self.storage = get_storage_provider()
        # Mock Feed List (In a real scenario, we would parse RSS feeds)
        # Using a reliable source for testing.
        self.sources = [
            "https://www.vogue.com/fashion",
            "https://www.businessoffashion.com/articles"
        ]

    def read(self, specific_url: str = None, limit: int = 3):
        print(f"📖 [WebReader] Starting read session...")
        results = []
        
        target_articles = []
        
        if specific_url:
             target_articles.append(specific_url)
        else:
            # RSS/Sitemap logic usually goes here.
            # For this POC, we will try to build a source or use a provided specific URL in the pipeline test
            # because crawling Vogue homepage usually gets complicated with JS rendering.
            # newspaper3k works best on direct article URLs or simple RSS.
            pass

        # If no specific URL provided, let's pretend we found some (mock logic or try to build)
        # Actually, let's just allow passing a list of URLs to process for now, 
        # or defaults to None and prints a warning if no specific URL.
        
        for url in target_articles:
            try:
                print(f"   🕸️ Processing: {url}")
                article = newspaper.Article(url)
                article.download()
                article.parse()
                
                # NLP processing (optional in this step, but good for summary)
                # article.nlp() 
                
                title = article.title
                text = article.text
                
                clean_text = f"TITLE: {title}\n\nBODY:\n{text}"
                
                # Persistence
                file_name = f"web_article_{uuid.uuid4().hex[:8]}.txt"
                stored_url = self.storage.upload_file(clean_text.encode('utf-8'), file_name)
                
                results.append({
                    "source_url": url,
                    "title": title,
                    "content_preview": text[:100],
                    "s3_url": stored_url,
                    "timestamp": datetime.now().isoformat()
                })
                print(f"   ✅ Article saved: {stored_url}")
                
            except Exception as e:
                print(f"   ❌ Error processing {url}: {e}")
                
        print(f"🏁 [WebReader] Finished. Processed {len(results)} articles.")
        return results

if __name__ == "__main__":
    reader = WebReader()
    # Test with a real article URL
    reader.read("https://www.vogue.com/article/spring-2025-fashion-trends") 
