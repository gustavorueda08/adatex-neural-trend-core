import os
from google import genai
from google.genai import types
from PIL import Image
import io

class ImageEngine:
    def __init__(self):
        print("🎨 [ImageEngine] Initializing Gemini Nano Banana (gemini-2.5-flash-image)...")
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            print("   ⚠️ GOOGLE_API_KEY not found. ImageEngine will fail if called.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def generate_image(self, prompt: str, output_path: str = "generated_concept.png"):
        """
        Generates an image using Google 'Nano Banana' model via the unified generate_content method.
        """
        if not self.client:
             print("   ⚠️ ImageEngine not initialized (No API Key). Skipping generation.")
             return None

        print(f"   🖌️ Generating concept for: '{prompt}'...")
        try:
            # Correct method from user docs: client.models.generate_content
            # The model 'gemini-2.5-flash-image' returns image parts.
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-image',
                contents=[prompt]
            )
            
            # Check parts for image
            if response.parts:
                for part in response.parts:
                    # The SDK documentation says check part.inline_data or if it has an as_image() method
                    # User docs:
                    # elif part.inline_data is not None:
                    #     image = part.as_image()
                    
                    # We will try the recommended way
                    try:
                        # Depending on SDK version, part might have .as_image() directly
                        image = part.as_image()
                        
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        image.save(output_path)
                        print(f"   💾 Saved concept art to: {output_path}")
                        return output_path
                    except AttributeError:
                        # Fallback if as_image is not directly available or handled differently
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # Decode manually if needed, but as_image is likely there on 1.56.0
                             pass 
                        continue
            
            print("   ❌ [ImageEngine] No images returned in response parts.")
            return None

        except Exception as e:
            print(f"   ❌ [ImageEngine] Error generating image: {e}")
            return None

if __name__ == "__main__":
    engine = ImageEngine()
    engine.generate_image("Futuristic fashion model wearing liquid silver fabric, cyberpunk city background, 8k resolution, cinematic lighting", "resources/test_concept.png")
