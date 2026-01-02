from transformers import pipeline
import torch

class NLPEngine:
    def __init__(self):
        print("🧠 [NLPEngine] Loading NLP Models...")
        self.device = 0 if torch.cuda.is_available() else -1
        
        device_str = "cpu"
        if torch.backends.mps.is_available():
            device_str = "mps" # Pipeline support varies, relying on cpu fallback if needed
        
        print(f"   ⚙️ Device Target: {device_str}")

        # Summarization (BART)
        print("   📚 Loading Summarizer (BART)...")
        self.summarizer = pipeline(
            "summarization", 
            model="facebook/bart-large-cnn", 
            device=self.device
        )

        # Sentiment (DistilBERT)
        print("   🙂 Loading Sentiment Analyzer (DistilBERT)...")
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=self.device
        )
        
        # Zero-Shot Classification (BART MNLI) - For Attribute Detection
        print("   🏷️ Loading Zero-Shot Classifier (BART-MNLI)...")
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=self.device
        )
        
        print("   ✅ Models loaded.")

    def analyze_text(self, text: str, candidate_data: dict = None) -> dict:
        """
        Summarizes, analyzes sentiment, AND classifies multiple attributes (Fabric, Texture, Finish).
        
        Args:
            text: Input text content.
            candidate_data: Dictionary of categories and labels.
                            Example:
                            {
                                "fabric": ["Sherpa", "Velvet"],
                                "texture": ["Soft", "Rough"],
                                "finish": ["Matte", "Shiny"]
                            }
        """
        if not text:
             return {}
             
        metrics = {}
        processed_text = text[:3000] # Truncate

        try:
            # 1. Summarize
            summary_output = self.summarizer(processed_text, max_length=130, min_length=30, do_sample=False)
            summary_text = summary_output[0]['summary_text']
            metrics['summary'] = summary_text

            # 2. Sentiment
            sentiment_output = self.sentiment_analyzer(summary_text)
            metrics['sentiment'] = sentiment_output[0]['label']
            metrics['sentiment_score'] = round(sentiment_output[0]['score'], 4)
            
            # 3. Multi-Attribute Classification (Zero-Shot)
            if candidate_data:
                metrics['attributes'] = {}
                
                for category, labels in candidate_data.items():
                    if not labels: continue
                    
                    classification = self.classifier(
                        processed_text, 
                        labels, 
                        multi_label=False
                    )
                    
                    top_label = classification['labels'][0]
                    top_score = classification['scores'][0]
                    
                    if top_score > 0.4: # Threshold
                        metrics['attributes'][category] = {
                            "label": top_label,
                            "score": round(top_score, 4)
                        }
                    else:
                        metrics['attributes'][category] = None
            
            return metrics

        except Exception as e:
            print(f"   ❌ [NLPEngine] Error processing text: {e}")
            return {}

if __name__ == "__main__":
    nlp = NLPEngine()
    text = "The winter collection features heavy use of faux sheepskin which feels incredibly soft and has a matte finish."
    
    candidates = {
        "fabric": ["Sherpa", "Velvet", "Lino"],
        "texture": ["Soft", "Rough", "Scratchy"],
        "finish": ["Matte", "Shiny", "Metallic"]
    }
    
    print(nlp.analyze_text(text, candidates))
