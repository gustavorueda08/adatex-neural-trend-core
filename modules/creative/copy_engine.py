import os
import json
import re
from google import genai
from google.genai import types

class CopyEngine:
    def __init__(self):
        print("✍️ [CopyEngine] Initializing Gemini 2.5 Flash...")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("   ⚠️ GOOGLE_API_KEY not found. CopyEngine will run in MOCK mode.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def generate_report(self, fabric_name: str, trend_status: str, source_summary: str, rich_context: dict = None) -> dict:
        """
        Generates a structured JSON report for a specific fabric/trend.
        Args:
            fabric_name: Name of the fabric
            trend_status: Rising/Stable/Declining
            source_summary: Basic counts
            rich_context: Dictionary containing 'textures', 'finishes', 'pantone_colors'
        """
        print(f"   📝 Generating Structured Report for '{fabric_name}'...")
        
        # Build Context String
        context_details = ""
        if rich_context:
            textures = ", ".join([f"{k} ({v})" for k, v in rich_context.get('textures', {}).items()])
            finishes = ", ".join([f"{k} ({v})" for k, v in rich_context.get('finishes', {}).items()])
            colors = ", ".join([f"{c['pantone_name']} ({c['hex']})" for c in rich_context.get('pantone_colors', [])[:3]])
            context_details = f"""
            DETALLES VISUALES DETECTADOS:
            - Texturas predominantes: {textures}
            - Acabados: {finishes}
            - Paleta Pantone Sugerida: {colors}
            """

        system_prompt = "Eres un Director Creativo de Moda experto en el mercado colombiano."
        
        user_prompt = f"""
        TEMA: {fabric_name}
        ESTADO DE MERCADO: {trend_status}
        CONTEXTO: {source_summary}
        {context_details}

        TAREA: Generar un objeto JSON válido con la siguiente estructura exacta:
        {{
            "pitch": "Argumento de venta emocional y sofisticado para el consumidor colombiano, mencionando especificamente las texturas y colores detectados.",
            "technical_summary": "Resumen para ingenieros textiles. Incluir composición probable, GSM sugerido y mencionar explícitamente los acabados y códigos Pantone sugeridos.",
            "usage": ["Prenda sugerida 1", "Prenda sugerida 2", "Prenda sugerida 3"],
            "sd_prompt": "An english prompt optimized for Stable Diffusion XL to generate a high-fashion photoshoot of a model wearing {fabric_name}. Include the specific textures ({textures if rich_context else ''}), finishes, and colors detected. Cinematic lighting, 8k resolution, photorealistic."
        }}
        
        Responder SOLO con el JSON.
        """

        if not self.client:
             return {
                "pitch": f"Mock pitch for {fabric_name}.",
                "technical_summary": "Mock tech specs.",
                "usage": ["Mock Item 1", "Mock Item 2"],
                "sd_prompt": f"Mock prompt for {fabric_name}"
            }

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json" 
                )
            )
            
            text_response = response.text
            text_response = text_response.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(text_response)
            return data

        except Exception as e:
            print(f"   ❌ [CopyEngine] Error generating report: {e}")
            return {
                "pitch": "Error generating pitch.",
                "technical_summary": "Error generating specs.",
                "usage": [],
                "sd_prompt": f"Fashion photography of {fabric_name}, cinematic lighting, 8k"
            }
