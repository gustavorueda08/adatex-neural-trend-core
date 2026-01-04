import sys
import os

# Ensure modules can be imported
sys.path.append(os.getcwd())

from modules.hunters.short_video_hunter import ShortVideoHunter

def main():
    print("Testing ShortVideoHunter...")
    hunter = ShortVideoHunter()
    # Use a very specific/safe tag
    results = hunter.hunt("cats", limit=1)
    print(f"Results found: {len(results)}")

if __name__ == "__main__":
    main()
