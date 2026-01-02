from transformers import AutoProcessor, AutoModelForZeroShotImageClassification
from PIL import Image
import torch
import requests
from io import BytesIO
import os

class VisionEngine:
    def __init__(self, model_id="google/siglip-base-patch16-224"):
        print(f"🧠 [VisionEngine] Loading SigLIP model: {model_id}...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if torch.backends.mps.is_available():
            self.device = "mps"
        
        print(f"   ⚙️ Device: {self.device}")

        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForZeroShotImageClassification.from_pretrained(model_id).to(self.device)
        print("   ✅ Model loaded.")

    def _load_image(self, image_path: str) -> Image.Image:
        """Loads an image from a local path or URL."""
        if image_path.startswith("http"):
            # Set User-Agent to avoid 403 blocks from some CDNs
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(image_path, headers=headers)
            return Image.open(BytesIO(response.content)).convert("RGB")
        elif image_path.startswith("file://"):
            return Image.open(image_path.replace("file://", "")).convert("RGB")
        else:
            return Image.open(image_path).convert("RGB")

    def analyze(self, image_path: str, candidate_data: dict) -> dict:
        """
        Performs Multi-Attribute Zero-Shot Classification.
        
        Args:
            image_path: Path/URL to image.
            candidate_data: Dictionary of categories and labels.
                            Example:
                            {
                                "fabric": ["Sherpa", "Velvet", "Lino"],
                                "texture": ["Smooth", "Rough", "Fluffy"],
                                "finish": ["Matte", "Shiny"]
                            }
        
        Returns:
            dict: Structured results with top match and confidence for each category.
                  Example:
                  {
                      "fabric": {"label": "Sherpa", "score": 0.95, "all_scores": {...}},
                      "texture": {"label": "Fluffy", "score": 0.88, ...},
                      ...
                  }
        """
        try:
            image = self._load_image(image_path)
            results = {}

            # Process each category independently using the same model
            for category, labels in candidate_data.items():
                if not labels: continue
                
                inputs = self.processor(images=image, text=labels, return_tensors="pt", padding=True).to(self.device)
                
                with torch.no_grad():
                    outputs = self.model(**inputs)
                
                logits = outputs.logits_per_image[0]
                probs = logits.softmax(dim=-1).cpu().numpy()
                
                # Zip scores
                scores = {label: float(probs[i]) for i, label in enumerate(labels)}
                sorted_scores = dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))
                
                # Get best
                best_label = list(sorted_scores.keys())[0]
                best_score = list(sorted_scores.values())[0]
                
                results[category] = {
                    "label": best_label,
                    "score": best_score,
                    "all_scores": sorted_scores
                }

            return results

        except Exception as e:
            # print(f"   ❌ [VisionEngine] Error processing {image_path}: {e}")
            # Keeping logs quiet for minor image errors to avoid clutter
            return {}

if __name__ == "__main__":
    vision = VisionEngine()
    test_image = "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg"
    
    # New Multi-Attribute Input
    candidates = {
        "fabric": ["denim", "silk", "leather", "cotton"],
        "texture": ["smooth", "rough", "quilted", "wrinkled"],
        "finish": ["matte", "shiny", "distressed"],
        "color_category": ["dark", "light", "pastel", "neon"]
    }
    
    print(f"Testing on: {test_image}")
    result = vision.analyze(test_image, candidates)
    import json
    print(json.dumps(result, indent=2))
