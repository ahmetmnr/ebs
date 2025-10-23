"""
Database Migration Runner
Bekleyen migration'ları çalıştırır.
"""

import sqlite3
from pathlib import Path
import sys

def run_migrations(db_path: Path):
    """
    Bekleyen migration'ları çalıştır.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Migration tablosu oluştur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Uygulanan migration'ları al
        cursor.execute("SELECT version FROM schema_migrations")
        applied = set(row[0] for row in cursor.fetchall())

        # Migration dosyalarını bul
        project_root = Path(__file__).parent.parent
        migrations_dir = project_root / "database" / "migrations"

        if not migrations_dir.exists():
            print(f"Migration klasörü bulunamadı: {migrations_dir}")
            return

        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            print("Migration dosyası bulunamadı")
            return

        print(f"Migration klasörü: {migrations_dir}")
        print(f"Bulunan migration sayısı: {len(migration_files)}")
        print()

        applied_count = 0

        for file in migration_files:
            # Versiyon numarasını çıkar (001_xxx.sql → 1)
            version_str = file.stem.split('_')[0]
            try:
                version = int(version_str)
            except ValueError:
                print(f"[SKIP] Gecersiz migration dosya adi: {file.name}")
                continue

            if version in applied:
                print(f"[SKIP] Migration {version} zaten uygulanmis: {file.name}")
                continue

            print(f"[RUN] Migration {version} uygulan iyor: {file.name}")

            # SQL'i çalıştır
            with open(file, 'r', encoding='utf-8') as f:
                sql = f.read()

            try:
                # Her satırı ayrı ayrı çalıştır (SQLite executescript sorunlarından kaçınmak için)
                statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

                for statement in statements:
                    if statement:
                        try:
                            cursor.execute(statement)
                        except sqlite3.OperationalError as e:
                            # "duplicate column" hatası kabul edilebilir
                            if 'duplicate column name' in str(e).lower():
                                print(f"   [SKIP] Kolon zaten mevcut")
                            else:
                                raise

                # Kaydet
                cursor.execute(
                    "INSERT INTO schema_migrations (version, filename) VALUES (?, ?)",
                    (version, file.name)
                )
                conn.commit()

                print(f"[OK] Migration {version} basarili")
                applied_count += 1

            except Exception as e:
                print(f"[ERROR] Migration {version} basarisiz: {e}")
                conn.rollback()
                raise

        print()
        if applied_count > 0:
            print(f"[OK] {applied_count} migration basariyla uygulandi")
        else:
            print("[OK] Tum migration'lar zaten uygulanmis")

    except Exception as e:
        print(f"\n[ERROR] Migration hatasi: {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "basvurular.db"

    if not db_path.exists():
        print(f"[ERROR] Veritabani bulunamadi: {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("DATABASE MIGRATION RUNNER")
    print("=" * 60)
    print(f"Veritabanı: {db_path}")
    print()

    run_migrations(db_path)

    print()
    print("=" * 60)
