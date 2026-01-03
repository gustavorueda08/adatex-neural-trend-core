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
        
        results = []
        
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'concurrent_fragment_downloads': 1, # Prevent race conditions
        }

        # Use "ytsearch" with "shorts" keyword and fetch more results to filter
        search_query = f"ytsearch{limit*3}:{tag} #shorts" 

        print(f"⬇️ [TikTokHunter] Searching for up to {limit} short videos matching '{tag}'...")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. Extract Info WITHOUT Downloading first
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    all_entries = info['entries']
                else:
                    all_entries = [info]

                # 2. Filter by Duration (Simulate TikTok/Reels < 120s)
                filtered_entries = []
                for entry in all_entries:
                    if not entry: continue
                    duration = entry.get('duration', 0)
                    if 0 < duration < 120: # Less than 2 minutes
                        filtered_entries.append(entry)
                
                print(f"   ℹ️ Found {len(filtered_entries)} valid short videos (duration < 120s).")

                # 3. Download Filtered Entries
                for entry in filtered_entries[:limit]:
                    video_id = entry.get('id')
                    video_url = entry.get('webpage_url') or entry.get('url')
                    
                    print(f"   ⬇️ Downloading video {video_id} ({entry.get('duration')}s)...")
                    
                    try:
                        # Download specific video
                        ydl.download([video_url or video_id])
                        
                        # Find the file
                        candidates = glob.glob(os.path.join(self.temp_dir, f"{video_id}.*"))
                        if candidates:
                            video_path = candidates[0]
                            # 4. Process
                            frames = self._process_video(video_path, parent_id=video_id, tag=tag)
                            results.extend(frames)
                            
                            # Cleanup
                            if os.path.exists(video_path):
                                os.remove(video_path)
                        else:
                             print(f"   ⚠️ File not found for {video_id} after download.")

                    except Exception as e:
                        print(f"   ❌ Failed to download/process {video_id}: {e}")
                        continue
                    
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
