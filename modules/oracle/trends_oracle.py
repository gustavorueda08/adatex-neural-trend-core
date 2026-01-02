from pytrends.request import TrendReq
import pandas as pd
import numpy as np
import time

class TrendsOracle:
    def __init__(self, hl='es-CO', tz=300): # Colombia timezone offset roughly, language Spanish-Colombia
        print("🔮 [TrendsOracle] Initializing Google Trends API (Colombia Region)...")
        # Retry/timeout config can be added here if needed
        self.pytrends = TrendReq(hl=hl, tz=tz, timeout=(10,25))

    def analyze_trend(self, keyword: str) -> dict:
        """
        Analyzes the trend for a keyword in Colombia over the last 12 months.
        Returns trend direction (Rising/Stable/Declining) and slope.
        """
        try:
            print(f"   📊 Querying trends (CO) for: '{keyword}'...")
            
            # Build payload (last 12 months, Geo=Colombia)
            self.pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='CO', gprop='')
            
            # Get Interest Over Time
            data = self.pytrends.interest_over_time()
            
            if data.empty:
                return {"keyword": keyword, "status": "No Data", "slope": 0, "mean_interest": 0}
            
            # Process Data
            interest_values = data[keyword].values
            
            # Simple Linear Regression to find Slope
            x = np.arange(len(interest_values))
            y = interest_values
            
            if len(x) > 1:
                slope, _ = np.polyfit(x, y, 1)
            else:
                slope = 0
            
            mean_interest = np.mean(interest_values)
            
            # Logic:
            # m > 0.5: RISING
            # -0.2 < m < 0.2: STABLE
            # m < -0.5: DECLINING
            # Gaps (0.2 to 0.5, -0.5 to -0.2): We need to classify them. 
            # I will assign "GROWING" for 0.2-0.5 and "WEAK" for negative gap, 
            # but user spec was strict. I'll default to the closest bucket or 'UNCERTAIN'.
            # Let's map strict user spec and fallback to 'STABLE' for the gaps to avoid dropping data?
            # Or maybe 'RISING' starts at 0.5? 
            # Let's stick to the prompt's implied buckets:
            
            status = "STABLE" # Default
            
            if slope > 0.5:
                status = "RISING"
            elif slope < -0.5:
                status = "DECLINING"
            elif -0.2 < slope < 0.2:
                status = "STABLE"
            else:
                # Handling the implementation gaps
                if slope >= 0.2:
                    status = "RISING (Weak)" # Or just Stable? Let's call it Stable-Positive
                elif slope <= -0.2:
                    status = "DECLINING (Weak)"
            
            # Basic sleep to avoid rate limits
            time.sleep(1)

            return {
                "keyword": keyword,
                "status": status,
                "slope": round(slope, 3),
                "mean_interest": round(mean_interest, 1),
                "top_region": "Colombia" # Pytrends can get region data, but for now we assume CO context
            }

        except Exception as e:
            print(f"   ❌ [TrendsOracle] Error processing '{keyword}': {e}")
            if "429" in str(e):
                print("      ⚠️ Google Trends Rate Limit hit.")
            return {"keyword": keyword, "status": "Error", "error": str(e), "slope": 0}

if __name__ == "__main__":
    oracle = TrendsOracle()
    keywords = ["Tela Sherpa", "Velvet", "Lino"]
    for kw in keywords:
        res = oracle.analyze_trend(kw)
        print(f"   Term: {res['keyword']}")
        print(f"   Status: {res.get('status')} (Slope: {res.get('slope')})")
        print("   ---")
