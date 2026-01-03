import os
import sys
import json
from dotenv import load_dotenv
from collections import Counter

# Load env variables
load_dotenv()

# --- Modules ---
from modules.hunters.pinterest_hunter import PinterestHunter
from modules.hunters.tiktok_hunter import TikTokHunter
from modules.hunters.youtube_listener import YouTubeListener
from modules.hunters.web_reader import WebReader

from modules.brains.vision_engine import VisionEngine
from modules.brains.nlp_engine import NLPEngine
from modules.brains.color_engine import ColorEngine

from modules.oracle.trends_oracle import TrendsOracle
from modules.creative.copy_engine import CopyEngine
from modules.creative.image_engine import ImageEngine
from modules.integration.db import get_db_engine
from modules.integration.models import Base, TrendReport
from sqlalchemy.orm import sessionmaker

def main():
    print("🚀 [ANTC] Starting Pipeline (Omnichannel Top 5 Mode)...")
    load_dotenv()
    
    # Define Candidates
    candidate_fabrics = ["Sherpa", "Velvet", "Lino", "Denim", "Satin", "Metallic", "Leather", "Jersey", "Piel de Durazno", "Polilycra", "Piel de Conejo"]
    candidate_textures = ["Soft", "Rough", "Fluffy", "Smooth", "Quilted", "Wrinkled"]
    candidate_finishes = ["Matte", "Shiny", "Distressed", "Sublimated", "Metallic"]
    
    # Initialize Counters & Aggregators
    fabric_counts = Counter()
    fabric_scores = {f: [] for f in candidate_fabrics} 
    asset_map = {f: [] for f in candidate_fabrics} # Visual evidence
    text_evidence = {f: [] for f in candidate_fabrics} # Text evidence
    
    # Attribute Aggregators (per fabric)
    fabric_attributes = {
        f: {
            "textures": Counter(),
            "finishes": Counter(),
            "colors": [] # List of palettes
        } for f in candidate_fabrics
    }
    
    # --- 1. THE HUNTERS (Ingesta Omnicanal) ---
    print("\n🏹 [ANTC] Phase 1: Hunters (Omnichannel)")
    
    # 1.1 Pinterest (Visual - Static)
    pinterest = PinterestHunter()
    pin_assets = pinterest.hunt("Fashion Trends 2026", limit=5)
    
    # 1.2 TikTok (Visual - Dynamic)
    tiktok = TikTokHunter()
    tt_assets = tiktok.hunt("FashionTrends2026", limit=5) 
    
    visual_assets = pin_assets + tt_assets
    print(f"   📸 Total Visual Assets: {len(visual_assets)}")

    # 1.3 YouTube (Context - Audio/Text)
    youtube = YouTubeListener()
    yt_assets = youtube.listen("Tendencias de moda 2026", limit=5)
    
    # 1.4 Web (Context - text)
    web = WebReader()
    web_assets = web.read("https://www.vogue.co.uk/fashion/article/spring-summer-2025-fashion-trends", limit=5)
    
    text_assets = yt_assets + web_assets
    print(f"   📄 Total Text Assets: {len(text_assets)}")
    
    # Fallback
    if not visual_assets and not text_assets:
         print("   ⚠️ No assets collected. Injecting MOCK DATA...")
         visual_assets = [{'s3_url': f"file:///mock/img_{i}.jpg"} for i in range(5)]
         fabric_counts['Sherpa'] = 15 # Simple injection

    # --- 2. THE BRAINS (Procesamiento) ---
    print("\n🧠 [ANTC] Phase 2: The Brains (Vision, NLP, Color)")
    
    # 2.1 Vision Analysis (Multi-Attribute)
    vision = VisionEngine()
    color_engine = ColorEngine(n_colors=3)
    
    # Labels Dict for Vision
    vision_candidates = {
        "fabric": candidate_fabrics,
        "texture": candidate_textures,
        "finish": candidate_finishes
    }

    print("   --- Vision Processing ---")
    for asset in visual_assets:
        img_url = asset.get('s3_url')
        if not img_url or "mock" in img_url: continue 
        
        print(f"   👁️ Analyzing: {img_url.split('/')[-1]}")
        
        # 1. Vision Classify
        results = vision.analyze(img_url, vision_candidates)
        
        # 2. Color Extract
        palette = color_engine.extract_palette(img_url)
        
        if results.get('fabric'):
             fab_res = results['fabric']
             winner = fab_res['label']
             score = fab_res['score']
             
             if score >= 0.70:
                 print(f"      ✅ Match: {winner} ({score:.2f})")
                 fabric_counts[winner] += 1
                 fabric_scores[winner].append(score)
                 asset_map[winner].append(img_url)
                 
                 # Aggregate Attributes
                 if results.get('texture'):
                     fabric_attributes[winner]['textures'][results['texture']['label']] += 1
                 if results.get('finish'):
                     fabric_attributes[winner]['finishes'][results['finish']['label']] += 1
                 
                 # Aggregate Colors
                 if palette:
                     fabric_attributes[winner]['colors'].extend(palette)
             else:
                 print(f"      🗑️ Discarded ({score:.2f})")

    # 2.2 NLP Analysis (Multi-Attribute)
    nlp = NLPEngine()
    
    # Labels Dict for NLP
    nlp_candidates = {
        "fabric": candidate_fabrics,
        "texture": candidate_textures,
        "finish": candidate_finishes
    }
    
    print("   --- NLP Processing ---")
    for asset in text_assets:
        text_content = asset.get('full_text') or (asset.get('title', '') + " " + asset.get('content_preview', ''))
        if not text_content: continue
        
        print(f"   📜 Analyzing Text...")
        nlp_results = nlp.analyze_text(text_content, nlp_candidates)
        
        if 'attributes' in nlp_results and nlp_results['attributes'].get('fabric'):
            fab_data = nlp_results['attributes']['fabric']
            if fab_data:
                winner = fab_data['label']
                sentiment = nlp_results.get('sentiment', 'NEUTRAL')
                
                print(f"      🗣️ Mentioned: {winner} ({sentiment})")
                
                weight = 1
                if sentiment == "POSITIVE": weight = 2
                elif sentiment == "NEGATIVE": weight = 0
                
                if weight > 0:
                    fabric_counts[winner] += weight
                    text_evidence[winner].append(f"Text ({sentiment})")
                    
                    # Aggregate NLP Attributes
                    if nlp_results['attributes'].get('texture'):
                        t_data = nlp_results['attributes']['texture']
                        if t_data: fabric_attributes[winner]['textures'][t_data['label']] += 1
                    
                    if nlp_results['attributes'].get('finish'):
                        f_data = nlp_results['attributes']['finish']
                        if f_data: fabric_attributes[winner]['finishes'][f_data['label']] += 1

    # --- 3. RANKING (Top 5) ---
    print("\n🏆 [ANTC] Phase 3: Ranking Top 5")
    top_5 = fabric_counts.most_common(5)
    
    if not top_5:
        print("   ⚠️ No fabrics found. Exiting.")
        return

    rank_list = []
    for i, (fabric, count) in enumerate(top_5, 1):
        scores = fabric_scores[fabric]
        avg_score = sum(scores)/len(scores) if scores else 0.0
        
        # Get Top Attributes
        top_textures = dict(fabric_attributes[fabric]['textures'].most_common(3))
        top_finishes = dict(fabric_attributes[fabric]['finishes'].most_common(3))
        
        # Process Colors (Simple frequency of pantone codes not implemented, just taking unique top ones)
        # Actually better to just take the palette of the highest confidence image, 
        # or aggregate. For this POC, we take the colors from the first 5 palettes found
        # to pass to context.
        raw_colors = fabric_attributes[fabric]['colors']
        # Deduplicate by hex
        seen_hex = set()
        unique_colors = []
        for c in raw_colors:
            if c['hex'] not in seen_hex:
                unique_colors.append(c)
                seen_hex.add(c['hex'])
        top_colors = unique_colors[:5]

        print(f"   #{i}: {fabric} (Score: {count})")
        print(f"         Textures: {list(top_textures.keys())}")
        print(f"         Pantones: {[c['pantone_name'] for c in top_colors]}")

        rank_list.append({
            "rank": i,
            "fabric": fabric,
            "count": count,
            "probability": avg_score,
            "evidence_images": asset_map[fabric],
            "evidence_text": text_evidence[fabric],
            "rich_context": {
                "textures": top_textures,
                "finishes": top_finishes,
                "pantone_colors": top_colors
            }
        })

    # --- 4. THE ORACLE (Validación) ---
    print("\n🔮 [ANTC] Phase 4: The Oracle (Market Validation)")
    oracle = TrendsOracle()
    final_candidates = []
    for item in rank_list:
        fabric = item['fabric']
        trend_data = oracle.analyze_trend(f"Tela {fabric}")
        status = trend_data.get('status', 'Unknown')
        slope = trend_data.get('slope', 0)
        item['market_status'] = status
        print(f"   📊 {fabric}: {status} (Slope: {slope})")
        
        if status == "DECLINING": continue
        final_candidates.append(item)

    # --- 5. THE CREATIVE (Síntesis) ---
    print("\n🎨 [ANTC] Phase 5: The Creative (GenAI)")
    copy_bot = CopyEngine()
    image_bot = ImageEngine()
    
    for item in final_candidates:
        fabric = item['fabric']
        print(f"   ✨ Processing Rank #{item['rank']}: {fabric}")
        
        ctx_str = f"Visual Count: {item['count']}."
        
        # Pass RICH CONTEXT to CopyEngine
        report_json = copy_bot.generate_report(
            fabric_name=fabric,
            trend_status=item['market_status'],
            source_summary=ctx_str,
            rich_context=item['rich_context'] # NEW ARGUMENT
        )
        
        item['creative_content'] = report_json
        
        sd_prompt = report_json.get('sd_prompt') or f"Fashion {fabric}"
        img_path = image_bot.generate_image(sd_prompt, f"resources/generated_{fabric.lower()}.png")
        item['generated_image'] = img_path

    # --- 6. INTEGRATION (Database) ---
    print(f"\n💾 [ANTC] Phase 6: Sync to Database")
    engine = get_db_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        for item in final_candidates:
            report_data = item['creative_content']
            pitch = report_data.get('pitch', '')
            specs = {"technical_summary": report_data.get('technical_summary', ''), "usage": report_data.get('usage', [])}
            all_evidence = item['evidence_images'] + item['evidence_text']
            
            # Extract main color name from rich context if available
            main_color_name = "Unknown"
            if item['rich_context']['pantone_colors']:
                main_color_name = item['rich_context']['pantone_colors'][0]['pantone_name']

            new_report = TrendReport(
                rank=item['rank'],
                fabric_name=item['fabric'],
                main_color=main_color_name,  # REAL DATA NOW
                probability=item['probability'],
                market_status=item['market_status'],
                description=pitch,
                specs=specs,
                image_url=item.get('generated_image', ''),
                evidence=all_evidence
            )
            session.add(new_report)
        session.commit()
        print("   ✅ Saved reports to DB.")
    except Exception as e:
        print(f"   ❌ DB Error: {e}")
        session.rollback()
    finally:
        session.close()

    print("\n🏁 [ANTC] Pipeline Finished Successfully.")

if __name__ == "__main__":
    main()
