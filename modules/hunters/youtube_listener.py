import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from datetime import datetime
import os
import json
import time
from modules.integration.storage import get_storage_provider
from transformers import pipeline
import torch

class YouTubeListener:
    def __init__(self):
        self.storage = get_storage_provider()
        # Initialize ASR pipeline lazily or here? 
        # Doing it lazily to save resources if not needed
        self.asr_pipeline = None

    def _get_asr_pipeline(self):
        if not self.asr_pipeline:
            print("      🤖 Loading content for local transcription (Whisper-Tiny)...")
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self.asr_pipeline = pipeline(
                "automatic-speech-recognition", 
                model="openai/whisper-tiny",
                device=device
            )
        return self.asr_pipeline

    def listen(self, query: str, limit: int = 3):
        print(f"👂 [YouTubeListener] listening for: '{query}'")
        
        # 1. Search for Video IDs using yt-dlp
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'max_downloads': limit
        }
        
        search_query = f"ytsearch{limit}:{query}"
        video_ids = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            video_ids.append(entry.get('id'))
        except Exception as e:
            print(f"❌ [YouTubeListener] Search error: {e}")
            return []

        results = []

        # 2. Extract Transcripts
        for vid in video_ids:
            clean_text = ""
            print(f"   📄 Fetching transcript for {vid}...")
            
            # --- STRATEGY A: Official Transcript API (Instance Mode) ---
            try:
                # 1. Instantiate (Required for this version 1.2.3)
                api = YouTubeTranscriptApi()
                
                # 2. List Transcripts
                if hasattr(api, 'list_transcripts'):
                     # Modern/Standard way if available
                     t_list = api.list_transcripts(vid)
                elif hasattr(api, 'list'):
                     # The method found in debug
                     t_list = api.list(vid)
                else:
                     raise Exception("No list method found on API instance")

                # 3. Find Best Transcript (Manual or Generated)
                transcript = None
                try:
                    # Try manual
                    transcript = t_list.find_manually_created_transcript(['es', 'en', 'en-US'])
                except:
                    try:
                        # Try generated
                        transcript = t_list.find_generated_transcript(['es', 'en', 'en-US'])
                    except:
                        # Try any
                        try:
                            transcript = t_list.find_transcript(['es', 'en', 'en-US'])
                        except:
                             # Last resort: iterate and pick first
                             for t in t_list:
                                 transcript = t
                                 break
                
                if transcript:
                    full_text_list = transcript.fetch()
                    # Check first item type to be safe (dict vs object)
                    if full_text_list:
                        first = full_text_list[0]
                        if hasattr(first, 'text'):
                             clean_text = " ".join([t.text for t in full_text_list])
                        elif isinstance(first, dict):
                             clean_text = " ".join([t['text'] for t in full_text_list])
                        else:
                             clean_text = str(full_text_list)
                    else:
                        clean_text = ""
                    
                    print(f"      ✅ Transcript found via API ({len(clean_text)} chars).")
                else:
                    print(f"      ⚠️ No suitable transcript found in list.")

            except Exception as e:
                print(f"      ⚠️ API Error ({vid}): {e}")

            # --- STRATEGY B: Local Whisper Fallback (Disabled due to missing ffmpeg) ---
            # if not clean_text:
            #      print(f"      🤖 Attempting Local Whisper Transcription for {vid}...")
            #      clean_text = self._transcribe_with_whisper(vid)

            # 3. Process & Save
            if clean_text:
                clean_text = clean_text.replace('\n', ' ').replace('  ', ' ')
                
                # Check for storage
                try:
                    file_name = f"youtube_{vid}_transcript.txt"
                    # Encode to bytes
                    stored_url = self.storage.upload_file(clean_text.encode('utf-8'), file_name)
                    print(f"      💾 Saved transcript to: {stored_url}")
                except Exception as e:
                     print(f"      ⚠️ Storage Error: {e}")
                     stored_url = None

                results.append({
                    "video_id": vid,
                    "full_text": clean_text,
                    "s3_url": stored_url,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                 print(f"      ❌ Failed to get text for {vid}")

        print(f"🏁 [YouTubeListener] Finished. Retrieved {len(results)} transcripts.")
        return results

    def _transcribe_with_whisper(self, video_id: str) -> str:
        """
        [DISABLED] Requires ffmpeg.
        Downloads audio (m4a) -> Local Whisper -> Text
        """
        return ""

if __name__ == "__main__":
    listener = YouTubeListener()
    listener.listen("Fashion Forecast 2026")
