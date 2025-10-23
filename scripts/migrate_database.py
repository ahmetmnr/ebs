"""
Mevcut veritabanını yeni şemaya migrate et.

ESKİ ŞEMA (data/basvurular.db):
  - basvurular (takip_no, hizmet_id, json_data, cekme_tarihi)
  - analiz_sonuclari (eski format)

YENİ ŞEMA (database/schema.sql):
  - basvurular (normalize edilmiş)
  - belgeler (ayrı tablo)
  - analiz_sonuclari (yeni format)
  - + diğer tablolar

STRATEJI:
1. Yeni veritabanı oluştur (data/basvurular_v2.db)
2. Eski verileri yeni şemaya aktar
3. Başarılı olursa yedek al ve değiştir
"""

import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime
import sys
import io

# UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Paths
OLD_DB = Path("data/basvurular.db")
NEW_DB = Path("data/basvurular_v2.db")
BACKUP_DB = Path("data/basvurular_backup_{}.db".format(datetime.now().strftime("%Y%m%d_%H%M%S")))
SCHEMA_FILE = Path("database/schema.sql")


def create_new_database():
    """Yeni veritabanını schema'dan oluştur"""
    print("\n[1/5] Yeni veritabani olusturuluyor...")

    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema dosyasi bulunamadi: {SCHEMA_FILE}")

    # Eğer NEW_DB varsa sil
    if NEW_DB.exists():
        print(f"[UYARI] Mevcut {NEW_DB} siliniyor...")
        NEW_DB.unlink()

    # Schema'yı çalıştır
    conn = sqlite3.connect(NEW_DB)
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    print(f"[OK] Yeni veritabani olusturuldu: {NEW_DB}")


def migrate_basvurular():
    """basvurular tablosunu migrate et"""
    print("\n[2/5] 'basvurular' tablosu migrate ediliyor...")

    old_conn = sqlite3.connect(OLD_DB)
    new_conn = sqlite3.connect(NEW_DB)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Eski verileri oku
    old_cursor.execute("SELECT takip_no, hizmet_id, json_data, cekme_tarihi FROM basvurular")
    rows = old_cursor.fetchall()

    print(f"[INFO] {len(rows)} basvuru kaydi bulundu")

    migrated_count = 0
    error_count = 0

    for takip_no, hizmet_id, json_data, cekme_tarihi in rows:
        try:
            # JSON'u parse et
            data = json.loads(json_data)

            # Yeni şemaya göre insert
            new_cursor.execute("""
                INSERT INTO basvurular (
                    basvuruId, takipNo, basvuruTarihi, hizmetId, hizmetAdi,
                    basvuruYapanVatandasTC, basvuruYapanAd, basvuruYapanSoyad,
                    basvuruDurum, kararDurum, json_ham, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('basvuruId'),
                data.get('takipNo'),
                data.get('basvuruTarihi'),
                hizmet_id,
                data.get('hizmetAdi', ''),
                data.get('basvuruYapanVatandasTC', ''),
                data.get('basvuruYapanAd', ''),
                data.get('basvuruYapanSoyad', ''),
                data.get('basvuruDurum', ''),
                data.get('kararDurum'),
                json_data,  # Ham JSON'u sakla
                cekme_tarihi
            ))

            migrated_count += 1

            if migrated_count % 100 == 0:
                print(f"[INFO] {migrated_count}/{len(rows)} kayit islendi...")
                new_conn.commit()

        except Exception as e:
            error_count += 1
            print(f"[HATA] {takip_no} migrate edilemedi: {e}")
            continue

    new_conn.commit()
    old_conn.close()
    new_conn.close()

    print(f"[OK] {migrated_count} basvuru migrate edildi")
    print(f"[UYARI] {error_count} hata olustu")


def migrate_belgeler():
    """belgeler tablosunu migrate et (json_data içindeki basvuruBelgeListesi'nden)"""
    print("\n[3/5] 'belgeler' tablosu olusturuluyor...")

    old_conn = sqlite3.connect(OLD_DB)
    new_conn = sqlite3.connect(NEW_DB)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # JSON'ları oku
    old_cursor.execute("SELECT takip_no, json_data FROM basvurular")
    rows = old_cursor.fetchall()

    total_belgeler = 0
    error_count = 0

    for takip_no, json_data in rows:
        try:
            data = json.loads(json_data)

            # basvuruId bul
            basvuru_id = data.get('basvuruId')
            if not basvuru_id:
                continue

            # Belgeleri çıkar
            belgeler = data.get('basvuruBelgeListesi', [])

            for belge in belgeler:
                try:
                    # Dosya uzantısı
                    belge_adi = belge.get('belgeAdi', '')
                    uzanti = Path(belge_adi).suffix.lower() if belge_adi else None

                    # Belge boyutunu hesapla (base64'ten tahmin)
                    dosya_byte = belge.get('dosyaByte', '')
                    belge_boyutu = len(dosya_byte) * 3 // 4 if dosya_byte else 0  # Base64 -> bytes tahmini

                    new_cursor.execute("""
                        INSERT INTO belgeler (
                            basvuruId, belgeAdi, belgeTipi, belgeIcerik,
                            belge_boyutu_bytes, belge_uzantisi
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        basvuru_id,
                        belge_adi,
                        belge.get('belgeTipi'),  # null olabilir
                        dosya_byte,
                        belge_boyutu,
                        uzanti
                    ))

                    total_belgeler += 1

                except Exception as e:
                    error_count += 1
                    print(f"[HATA] Belge eklenemedi ({takip_no}): {e}")
                    continue

            if total_belgeler % 500 == 0:
                print(f"[INFO] {total_belgeler} belge islendi...")
                new_conn.commit()

        except Exception as e:
            error_count += 1
            print(f"[HATA] {takip_no} belgeleri islenmedi: {e}")
            continue

    new_conn.commit()
    old_conn.close()
    new_conn.close()

    print(f"[OK] {total_belgeler} belge migrate edildi")
    print(f"[UYARI] {error_count} hata olustu")


def update_belge_tipi_tahminleri():
    """Belge tipi NULL olanlar için tahmin yap"""
    print("\n[4/5] Belge tipleri tahmin ediliyor...")

    conn = sqlite3.connect(NEW_DB)
    cursor = conn.cursor()

    # NULL belgeTipi olan belgeleri bul
    cursor.execute("""
        SELECT b.belgeId, b.belgeAdi
        FROM belgeler b
        WHERE b.belgeTipi IS NULL
    """)

    belge_list = cursor.fetchall()
    print(f"[INFO] {len(belge_list)} belge icin tip tahmin edilecek")

    # Tahmin kurallarını al
    cursor.execute("""
        SELECT dosya_adi_pattern, tahmin_edilen_tip, oncelik
        FROM belge_tipi_kurallar
        WHERE aktif = 1
        ORDER BY oncelik DESC
    """)
    kurallar = cursor.fetchall()

    updated = 0
    for belge_id, belge_adi in belge_list:
        tahmin = None

        # Regex pattern matching
        import re
        for pattern, tip, _ in kurallar:
            if re.search(pattern, belge_adi, re.IGNORECASE):
                tahmin = tip
                break

        if tahmin:
            cursor.execute("""
                UPDATE belgeler
                SET belgeTipi_tahmini = ?
                WHERE belgeId = ?
            """, (tahmin, belge_id))
            updated += 1

    conn.commit()
    conn.close()

    print(f"[OK] {updated} belge tipi tahmin edildi")


def create_backup():
    """Eski veritabanını yedekle"""
    print("\n[5/5] Yedekleme yapiliyor...")

    if not OLD_DB.exists():
        print("[UYARI] Eski veritabani bulunamadi, yedekleme atlanıyor")
        return

    shutil.copy2(OLD_DB, BACKUP_DB)
    print(f"[OK] Yedek olusturuldu: {BACKUP_DB}")
    print(f"[INFO] Yedek boyutu: {BACKUP_DB.stat().st_size / (1024**3):.2f} GB")


def verify_migration():
    """Migration doğrulama"""
    print("\n" + "=" * 80)
    print("MIGRATION DOGRULAMA")
    print("=" * 80)

    old_conn = sqlite3.connect(OLD_DB)
    new_conn = sqlite3.connect(NEW_DB)

    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Başvuru sayısı kontrolü
    old_cursor.execute("SELECT COUNT(*) FROM basvurular")
    old_count = old_cursor.fetchone()[0]

    new_cursor.execute("SELECT COUNT(*) FROM basvurular")
    new_count = new_cursor.fetchone()[0]

    print(f"\nBasvuru sayisi:")
    print(f"  Eski DB: {old_count}")
    print(f"  Yeni DB: {new_count}")
    print(f"  Durum: {'[OK]' if old_count == new_count else '[HATA]'}")

    # Belge sayısı
    new_cursor.execute("SELECT COUNT(*) FROM belgeler")
    belge_count = new_cursor.fetchone()[0]
    print(f"\nBelgeler tablosu: {belge_count} kayit")

    # Örnek karşılaştırma
    print("\nOrnek kayit karsilastirmasi:")
    old_cursor.execute("SELECT takip_no, hizmet_id FROM basvurular LIMIT 1")
    old_sample = old_cursor.fetchone()

    new_cursor.execute("SELECT takipNo, hizmetId FROM basvurular LIMIT 1")
    new_sample = new_cursor.fetchone()

    print(f"  Eski: takip_no={old_sample[0]}, hizmet_id={old_sample[1]}")
    print(f"  Yeni: takipNo={new_sample[0]}, hizmetId={new_sample[1]}")

    old_conn.close()
    new_conn.close()

    print("\n" + "=" * 80)


def main():
    """Ana migration fonksiyonu"""
    print("=" * 80)
    print("VERITABANI MIGRATION - ESKİ SEMA -> YENİ SEMA")
    print("=" * 80)

    if not OLD_DB.exists():
        print(f"[HATA] Eski veritabani bulunamadi: {OLD_DB}")
        return

    print(f"\nEski DB: {OLD_DB} ({OLD_DB.stat().st_size / (1024**3):.2f} GB)")
    print(f"Yeni DB: {NEW_DB}")
    print(f"Yedek: {BACKUP_DB}")

    # Onay al
    response = input("\nMigration baslatilsin mi? (evet/hayir): ").strip().lower()
    if response not in ['evet', 'e', 'yes', 'y']:
        print("[IPTAL] Migration iptal edildi")
        return

    try:
        # Adımlar
        create_backup()
        create_new_database()
        migrate_basvurular()
        migrate_belgeler()
        update_belge_tipi_tahminleri()
        verify_migration()

        print("\n" + "=" * 80)
        print("[BASARILI] Migration tamamlandi!")
        print("=" * 80)
        print(f"\nSONRAKI ADIMLAR:")
        print(f"1. Yeni DB'yi kontrol et: {NEW_DB}")
        print(f"2. Eski DB yedeği: {BACKUP_DB}")
        print(f"3. Sorun yoksa eski DB'yi degistir:")
        print(f"   - Yedekle: mv {OLD_DB} {OLD_DB}.old")
        print(f"   - Degistir: mv {NEW_DB} {OLD_DB}")

    except Exception as e:
        print(f"\n[HATA] Migration basarisiz: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
