from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import requests
from io import BytesIO
import matplotlib.colors as mcolors
import math

class ColorEngine:
    def __init__(self, n_colors=5):
        self.n_colors = n_colors
        # Pantone TCX Subset (Fashion Home + Interiors)
        # Mapping simple names/codes to RGB ref values
        self.pantone_db = {
            "11-0601 TCX": {"name": "Bright White", "rgb": (244, 249, 255)},
            "19-4007 TCX": {"name": "Anthracite", "rgb": (40, 40, 40)},
            "11-4001 TCX": {"name": "Brilliant White", "rgb": (240, 240, 250)},
            "13-1006 TCX": {"name": "Creme Brulee", "rgb": (219, 204, 181)},
            "16-1546 TCX": {"name": "Living Coral", "rgb": (255, 111, 97)},
            "18-3838 TCX": {"name": "Ultra Violet", "rgb": (95, 75, 139)},
            "19-4052 TCX": {"name": "Classic Blue", "rgb": (15, 76, 129)},
            "17-5104 TCX": {"name": "Ultimate Gray", "rgb": (147, 149, 151)},
            "13-0647 TCX": {"name": "Illuminating", "rgb": (245, 223, 77)},
            "15-0343 TCX": {"name": "Greenery", "rgb": (136, 176, 75)},
            "18-1438 TCX": {"name": "Marsala", "rgb": (150, 79, 76)},
            "18-3224 TCX": {"name": "Radiant Orchid", "rgb": (173, 94, 153)},
            "17-5641 TCX": {"name": "Emerald", "rgb": (0, 148, 115)},
            "17-1463 TCX": {"name": "Tangerine Tango", "rgb": (221, 65, 36)},
            "18-2120 TCX": {"name": "Honeysuckle", "rgb": (214, 80, 118)},
            "15-5519 TCX": {"name": "Turquoise", "rgb": (69, 181, 170)},
            "14-0848 TCX": {"name": "Mimosa", "rgb": (240, 192, 90)},
            "18-3943 TCX": {"name": "Blue Iris", "rgb": (90, 91, 159)},
            "19-1557 TCX": {"name": "Chili Pepper", "rgb": (155, 27, 48)},
            "13-1106 TCX": {"name": "Sand Dollar", "rgb": (222, 205, 190)},
            "19-0303 TCX": {"name": "Jet Black", "rgb": (45, 44, 47)},
            "19-4005 TCX": {"name": "Stretch Limo", "rgb": (43, 46, 52)},
            "11-0103 TCX": {"name": "Egret", "rgb": (243, 236, 224)},
            "14-1118 TCX": {"name": "Beige", "rgb": (212, 184, 149)},
            "16-1325 TCX": {"name": "Copper", "rgb": (184, 115, 51)},
            "17-2031 TCX": {"name": "Fuchsia", "rgb": (193, 84, 193)},
            "19-1664 TCX": {"name": "True Red", "rgb": (191, 25, 50)},
        }

    def _load_image(self, image_path: str) -> Image.Image:
        """Loads an image from a local path or URL."""
        if image_path.startswith("http"):
            response = requests.get(image_path)
            img = Image.open(BytesIO(response.content)).convert("RGB")
        elif image_path.startswith("file://"):
            img = Image.open(image_path.replace("file://", "")).convert("RGB")
        else:
            img = Image.open(image_path).convert("RGB")
        
        # Resize for faster processing
        img.thumbnail((200, 200)) 
        return img

    def _match_pantone(self, rgb_tuple):
        """Finds closest Pantone TCX from local DB using Euclidean distance."""
        min_dist = float('inf')
        closest_code = None
        closest_name = None
        
        r1, g1, b1 = rgb_tuple
        
        for code, data in self.pantone_db.items():
            r2, g2, b2 = data['rgb']
            # Simple Euclidean distance in RGB space
            # (Delta E Lab is better but requires conversion libs which might fail as per log)
            dist = math.sqrt((r2 - r1)**2 + (g2 - g1)**2 + (b2 - b1)**2)
            if dist < min_dist:
                min_dist = dist
                closest_code = code
                closest_name = data['name']
                
        return closest_code, closest_name

    def extract_palette(self, image_path: str) -> list[dict]:
        """
        Extracts dominant colors and matches them to Pantone.
        """
        try:
            image = self._load_image(image_path)
            image_np = np.array(image)
            
            pixels = image_np.reshape(-1, 3)
            
            kmeans = KMeans(n_clusters=self.n_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = kmeans.cluster_centers_
            labels = kmeans.labels_
            
            counts = np.bincount(labels)
            total = len(labels)
            
            palette = []
            for i in range(self.n_colors):
                rgb = colors[i].astype(int)
                hex_color = mcolors.to_hex(rgb / 255.0)
                percentage = counts[i] / total
                
                # Pantone Match
                p_code, p_name = self._match_pantone(rgb)

                palette.append({
                    "hex": hex_color,
                    "rgb": rgb.tolist(),
                    "percentage": round(percentage, 4),
                    "pantone_code": p_code,
                    "pantone_name": p_name
                })
            
            palette.sort(key=lambda x: x['percentage'], reverse=True)
            return palette

        except Exception as e:
            print(f"   ❌ [ColorEngine] Error processing {image_path}: {e}")
            return []

if __name__ == "__main__":
    color_engine = ColorEngine()
    test_image = "https://images.pexels.com/photos/1036623/pexels-photo-1036623.jpeg"
    print(f"Extracting palette from: {test_image}")
    palette = color_engine.extract_palette(test_image)
    for p in palette:
        print(f"   🎨 {p['hex']} ({p['percentage']*100:.1f}%) -> {p['pantone_name']} ({p['pantone_code']})")
