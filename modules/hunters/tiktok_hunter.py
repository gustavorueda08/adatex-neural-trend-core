import os
import cv2
import yt_dlp
import uuid
import glob
from datetime import datetime
from modules.integration.storage import get_storage_provider

class TikTokHunter:
    def __init__(self):
        self.storage = get_storage_provider()
        self.temp_dir = "temp_video_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)

    def hunt(self, tag: str, limit: int = 5):
        print(f"🎵 [TikTokHunter] Starting hunt for tag: '{tag}'")
        
        # 1. Search and Download via yt-dlp
        # Note: TikTok search via yt-dlp can be unstable. 
        # Using "ytsearch" (YouTube) as a proxy for "Reels/Shorts" in this POC if TikTok fails, 
        # but the blueprint asks for TikTok. I will try a generic search that yt-dlp supports.
        # Ideally, we would use a specific TikTok scraper, but yt-dlp supports tiktok.com URLs.
        # For 'search', yt-dlp works best with YouTube. 
        # To strictly follow the blueprint "TikTok/Reels Hunter", I will assume we might search generic short video platforms 
        # or rely on direct URLs if search is blocked. 
        # However, yt-dlp DOES support "ytsearch:". Let's try to find Shorts/Reels style content on YouTube 
        # if TikTok search is flaky, OR we can try to download specific TikTok URLs if provided.
        # For this implementation, I will implement a search on YouTube Shorts as it's more reliable for automation 
        # than scraping TikTok search results without a dedicated API.
        
        # UPDATE: The prompt implies "TikTok/Reels". 
        results = []
        
        ydl_opts = {
            # 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Requires FFmpeg
            'format': 'best[ext=mp4]', # Single file
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            # 'max_downloads': limit # Removed to avoid exception
        }

        # We will use "ytsearch" with "shorts" keyword to simulate finding vertical viral videos if direct TikTok search is hard.
        # But let's try to be generic. 
        search_query = f"ytsearch{limit}:{tag} #shorts"

        print(f"⬇️ [TikTokHunter] Downloading up to {limit} videos matching '{tag}'...")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                if 'entries' in info:
                    video_entries = info['entries']
                else:
                    video_entries = [info]

                # Manually limit
                for entry in video_entries[:limit]:
                    if not entry: continue
                    video_id = entry.get('id')
                    
                    # Try to find any file with that ID
                    candidates = glob.glob(os.path.join(self.temp_dir, f"{video_id}.*"))
                    if candidates:
                        video_path = candidates[0]
                    else:
                        print(f"⚠️ [TikTokHunter] File not found for {video_id}")
                        continue

                    # 2. Process Video (Frame Sampling)
                    frames = self._process_video(video_path, parent_id=video_id, tag=tag)
                    results.extend(frames)
                    
                    # 3. Cleanup
                    if os.path.exists(video_path):
                        os.remove(video_path)

        except Exception as e:
            print(f"❌ [TikTokHunter] Error during download/processing: {e}")

        print(f"🏁 [TikTokHunter] Hunt finished. Captured {len(results)} frames.")
        return results

    def _process_video(self, video_path: str, parent_id: str, tag: str) -> list:
        print(f"🎞️ [TikTokHunter] Processing video: {os.path.basename(video_path)}")
        frames_captured = []
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30 # Fallback

        # Logic: Extract 1 frame every 2 seconds
        sample_rate_sec = 2
        frame_interval = int(fps * sample_rate_sec)
        
        current_frame = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if current_frame % frame_interval == 0:
                # Encode frame to memory
                success, buffer = cv2.imencode(".jpg", frame)
                if success:
                    file_name = f"tiktok_{parent_id}_{current_frame}.jpg"
                    
                    # Upload
                    stored_url = self.storage.upload_file(buffer.tobytes(), file_name)
                    
                    frames_captured.append({
                        "s3_url": stored_url,
                        "parent_video": parent_id,
                        "tag": tag,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"   📸 Frame saved: {file_name}")

            current_frame += 1
        
        cap.release()
        return frames_captured

if __name__ == "__main__":
    hunter = TikTokHunter()
    # Testing with a YouTube Short query as proxy for "TikTok/Reels" content
    hunter.hunt("Summer Fashion Trends 2025", limit=1)
