from modules.brains.vision_engine import VisionEngine
import os

def analyze_failure():
    vision = VisionEngine()
    # Path to the image reported by the user
    image_path = "/Users/grmini/Develop - Local/adatex-neural-trend-core/resources/antc_data/pinterest_05072aea.jpg"
    
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    # Use the EXACT same candidates as pinterest_hunter.py to reproduce the decision
    candidates = {
        "content_type": [
            "editorial fashion photography",
            "promotional graphic with text",
            "digital collage with text"
        ]
    }

    print(f"🔍 Analyzing: {image_path}")
    result = vision.analyze(image_path, candidates)
    
    if result and "content_type" in result:
        print("\n--- Results ---")
        best = result["content_type"]
        print(f"Winner: {best['label']} (Score: {best['score']:.4f})")
        print("\nAll Scores:")
        for label, score in best['all_scores'].items():
            print(f"  - {label}: {score:.4f}")
    else:
        print("Analysis failed.")

if __name__ == "__main__":
    analyze_failure()
