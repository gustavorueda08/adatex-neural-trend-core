import sqlite3

def inspect_pantone():
    conn = sqlite3.connect('antc_dev.db')
    cursor = conn.cursor()
    print("🔍 Inspecting Pantone in 'antc_dev.db'...\n")
    try:
        cursor.execute("SELECT id, fabric_name, main_color, created_at FROM trend_reports ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        print(f"{'FABRIC':<15} | {'MAIN COLOR (Pantone)':<25} | {'CREATED AT'}")
        print("-" * 65)
        for row in rows:
            print(f"{row[1]:<15} | {row[2]:<25} | {row[3]}")
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_pantone()
