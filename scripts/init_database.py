"""
Yeni veritabanını başlat (schema'yı uygula).

KULLANIM:
    python scripts/init_database.py
    python scripts/init_database.py --force  # Mevcut DB'yi sil ve yeniden oluştur
"""

import sys
import argparse
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.database import db
from config.settings import DATABASE_PATH, BASE_DIR

def init_database(force: bool = False):
    """
    Veritabanını başlat.

    Args:
        force: True ise mevcut DB'yi sil ve yeniden oluştur
    """
    print("=" * 80)
    print("VERİTABANI BAŞLATMA")
    print("=" * 80)

    schema_path = BASE_DIR / "database" / "schema.sql"

    print(f"\nVeritabanı: {DATABASE_PATH}")
    print(f"Schema: {schema_path}")

    # Mevcut DB kontrolü
    if DATABASE_PATH.exists():
        if force:
            print(f"\n[UYARI] Mevcut veritabanı siliniyor: {DATABASE_PATH}")
            DATABASE_PATH.unlink()
        else:
            print(f"\n[UYARI] Veritabanı zaten mevcut: {DATABASE_PATH}")
            response = input("Devam edilsin mi? Mevcut şema üzerine yazılacak! (evet/hayir): ").strip().lower()
            if response not in ['evet', 'e', 'yes', 'y']:
                print("[İPTAL] İşlem iptal edildi")
                return

    # Schema'yı uygula
    try:
        print("\n[İşlem] Schema uygulanıyor...")
        db.init_database(schema_path)
        print("[BAŞARILI] Veritabanı başarıyla oluşturuldu!")

        # Tablo listesi
        print("\n" + "=" * 80)
        print("OLUŞTURULAN TABLOLAR:")
        print("=" * 80)

        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        tables = db.fetchall(query)

        for i, table in enumerate(tables, 1):
            table_name = table['name']
            count = db.get_row_count(table_name)
            print(f"{i}. {table_name} ({count} kayıt)")

        # View listesi
        print("\n" + "=" * 80)
        print("OLUŞTURULAN VIEW'LAR:")
        print("=" * 80)

        query = "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        views = db.fetchall(query)

        for i, view in enumerate(views, 1):
            print(f"{i}. {view['name']}")

        print("\n" + "=" * 80)
        print("[BAŞARILI] Veritabanı hazır!")
        print("=" * 80)

        print(f"\nSONRAKİ ADIMLAR:")
        print(f"1. Eski veritabanını migrate et:")
        print(f"   python scripts/migrate_database.py")
        print(f"2. Başvuruları işle:")
        print(f"   python scripts/analyze_from_db.py --limit 10")

    except Exception as e:
        print(f"\n[HATA] Veritabanı oluşturma hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description="Veritabanını başlat")
    parser.add_argument('--force', action='store_true',
                       help='Mevcut DB\'yi sil ve yeniden oluştur')

    args = parser.parse_args()

    init_database(force=args.force)


if __name__ == "__main__":
    main()
