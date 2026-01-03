import sys
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def print_menu():
    print("\n🧪 [ANTC] Module Testing Tool")
    print("=============================")
    print("1. Test Pinterest Hunter (modules/hunters/pinterest_hunter.py)")
    print("2. Test TikTok Hunter (modules/hunters/tiktok_hunter.py)")
    print("3. Test YouTube Listener (modules/hunters/youtube_listener.py)")
    print("4. Test Web Reader (modules/hunters/web_reader.py)")
    print("5. Test Vision Engine (modules/brains/vision_engine.py)")
    print("6. Test Color Engine (modules/brains/color_engine.py)")
    print("7. Test NLP Engine (modules/brains/nlp_engine.py)")
    print("8. Test Trends Oracle (modules/oracle/trends_oracle.py)")
    print("9. Test Copy Engine (modules/creative/copy_engine.py)")
    print("10. Test Image Engine (modules/creative/image_engine.py)")
    print("0. Exit")
    print("=============================")

def run_test(module_name, query=None):
    print(f"\n🚀 Running test for: {module_name}")
    try:
        if module_name == "PinterestHunter":
            from modules.hunters.pinterest_hunter import PinterestHunter
            hunter = PinterestHunter()
            hunter.hunt(query or "Summer Fashion 2026", limit=10)

        elif module_name == "TikTokHunter":
            from modules.hunters.tiktok_hunter import TikTokHunter
            hunter = TikTokHunter()
            hunter.hunt(query or "Summer Fashion 2026", limit=1)

        elif module_name == "YouTubeListener":
            from modules.hunters.youtube_listener import YouTubeListener
            listener = YouTubeListener()
            listener.listen(query or "Fashion Trends 2026", limit=1)

        elif module_name == "WebReader":
            from modules.hunters.web_reader import WebReader
            reader = WebReader()
            # Test with a mock list or real url if provided
            reader.read("https://www.vogue.com/article/addressed-fashion-code-switching-at-home", limit=1)

        elif module_name == "VisionEngine":
            from modules.brains.vision_engine import VisionEngine
            vision = VisionEngine()
            test_img = "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg"
            candidates = {
                "fabric": ["denim", "silk", "leather", "cotton"],
                "texture": ["smooth", "rough"],
                "finish": ["matte", "shiny"]
            }
            print(f"Analyzing {test_img}...")
            res = vision.analyze(test_img, candidates)
            import json
            print(json.dumps(res, indent=2))

        elif module_name == "ColorEngine":
            from modules.brains.color_engine import ColorEngine
            engine = ColorEngine()
            test_img = "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg"
            pal = engine.extract_palette(test_img)
            for p in pal:
                 print(f"🎨 {p['hex']} -> {p['pantone_name']}")

        elif module_name == "NLPEngine":
            from modules.brains.nlp_engine import NLPEngine
            nlp = NLPEngine()
            text = "The new collection features lots of heavy wool and shearling fabrics."
            candidates = {"fabric": ["Wool", "Shearling", "Silk"]}
            print(f"Analyzing: '{text}'")
            print(nlp.analyze_text(text, candidates))

        elif module_name == "TrendsOracle":
            from modules.oracle.trends_oracle import TrendsOracle
            oracle = TrendsOracle()
            kw = query or "Moda 2026"
            print(oracle.analyze_trend(kw))

        elif module_name == "CopyEngine":
            from modules.creative.copy_engine import CopyEngine
            copy = CopyEngine()
            print(copy.generate_report("Silk", "RISING", "Visuals: 10"))

        elif module_name == "ImageEngine":
            from modules.creative.image_engine import ImageEngine
            gen = ImageEngine()
            gen.generate_image("Fashion sketch of a futuristic silk dress", "resources/test_gen.png")
            
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    while True:
        print_menu()
        choice = input("Select a module to test (0-10): ")
        
        if choice == "0":
            break
        elif choice == "1": run_test("PinterestHunter")
        elif choice == "2": run_test("TikTokHunter")
        elif choice == "3": run_test("YouTubeListener")
        elif choice == "4": run_test("WebReader")
        elif choice == "5": run_test("VisionEngine")
        elif choice == "6": run_test("ColorEngine")
        elif choice == "7": run_test("NLPEngine")
        elif choice == "8": run_test("TrendsOracle")
        elif choice == "9": run_test("CopyEngine")
        elif choice == "10": run_test("ImageEngine")
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
