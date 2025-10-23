"""
Mevcut veritabanı şemasını kontrol et.
"""
import sqlite3
import json
import sys
from pathlib import Path

# UTF-8 encoding için
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = Path("data/basvurular.db")

def check_schema():
    """Mevcut şemayı kontrol et ve göster"""
    if not DB_PATH.exists():
        print(f"[HATA] Veritabani bulunamadi: {DB_PATH}")
        return

    print(f"[OK] Veritabani bulundu: {DB_PATH}")
    print(f"[INFO] Boyut: {DB_PATH.stat().st_size / (1024**3):.2f} GB\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabloları listele
    print("=" * 80)
    print("TABLOLAR:")
    print("=" * 80)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        # Satır sayısı
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        print(f"\n[TABLO] {table} ({count:,} satir)")

        # Şema
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        print("   Kolonlar:")
        for col in columns:
            col_id, name, dtype, notnull, default, pk = col
            constraints = []
            if pk:
                constraints.append("PRIMARY KEY")
            if notnull:
                constraints.append("NOT NULL")
            if default:
                constraints.append(f"DEFAULT {default}")

            constraint_str = f" ({', '.join(constraints)})" if constraints else ""
            print(f"   - {name}: {dtype}{constraint_str}")

    # Örnek veri göster
    print("\n" + "=" * 80)
    print("ÖRNEK VERİ - basvurular tablosu (ilk kayıt):")
    print("=" * 80)

    cursor.execute("SELECT * FROM basvurular LIMIT 1")
    row = cursor.fetchone()
    if row:
        cursor.execute("PRAGMA table_info(basvurular)")
        columns = [col[1] for col in cursor.fetchall()]

        for col, val in zip(columns, row):
            if col == 'json_data' and val:
                # JSON'u parse et
                try:
                    json_obj = json.loads(val)
                    print(f"\n{col}:")
                    print(json.dumps(json_obj, indent=2, ensure_ascii=False)[:500] + "...")
                except:
                    print(f"{col}: [JSON parse hatası]")
            else:
                val_str = str(val)[:100]
                print(f"{col}: {val_str}")

    # analiz_sonuclari varsa kontrol et
    if 'analiz_sonuclari' in tables:
        print("\n" + "=" * 80)
        print("ANALİZ SONUÇLARI - Örnek kayıt:")
        print("=" * 80)

        cursor.execute("SELECT * FROM analiz_sonuclari LIMIT 1")
        row = cursor.fetchone()
        if row:
            cursor.execute("PRAGMA table_info(analiz_sonuclari)")
            columns = [col[1] for col in cursor.fetchall()]

            for col, val in zip(columns, row):
                if 'json' in col.lower() and val:
                    try:
                        json_obj = json.loads(val)
                        print(f"\n{col}:")
                        print(json.dumps(json_obj, indent=2, ensure_ascii=False)[:300] + "...")
                    except:
                        print(f"{col}: [JSON parse hatası]")
                else:
                    val_str = str(val)[:100] if val else "NULL"
                    print(f"{col}: {val_str}")

    conn.close()

    print("\n" + "=" * 80)
    print("[OK] Sema kontrolu tamamlandi")
    print("=" * 80)

if __name__ == "__main__":
    check_schema()
