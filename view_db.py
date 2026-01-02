import sqlite3
import json

def inspect_db():
    conn = sqlite3.connect('antc_dev.db')
    cursor = conn.cursor()
    
    print("🔍 Inspecting 'antc_dev.db'...\n")
    
    try:
        cursor.execute("SELECT id, rank, fabric_name, market_status, description, image_url, created_at FROM trend_reports ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️ No reports found in database.")
            return

        print(f"✅ Found {len(rows)} recent reports:\n")
        print(f"{'RANK':<5} | {'FABRIC':<15} | {'STATUS':<15} | {'CREATED AT':<20}")
        print("-" * 60)
        
        for row in rows:
            report_id, rank, fabric, status, desc, img, created = row
            # Truncate desc for view
            short_desc = (desc[:50] + '...') if desc else "No Description"
            
            print(f"#{rank:<4} | {fabric:<15} | {status:<15} | {created}")
            print(f"      📝 Pitch: {short_desc}")
            print(f"      🖼️ Image: {img}\n")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_db()
