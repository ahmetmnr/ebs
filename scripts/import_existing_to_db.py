"""
Mevcut output/ klasöründeki JSON dosyalarını veritabanına aktar
"""
import sys
import os
from datetime import datetime
from pathlib import Path
import json
import sqlite3

# Veritabanı yolu
DB_PATH = Path("data/basvurular.db")
DB_PATH.parent.mkdir(exist_ok=True)

def init_db():
    """Veritabanı tablolarını oluştur"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Başvurular tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS basvurular (
            takip_no TEXT PRIMARY KEY,
            hizmet_id TEXT,
            basvuru_tarihi TEXT,
            ad_soyad TEXT,
            tc_no TEXT,
            durum TEXT,
            json_data TEXT NOT NULL,
            cekme_tarihi TEXT NOT NULL,
            son_guncelleme TEXT NOT NULL
        )
    """)

    # Belgeler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS belgeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            takip_no TEXT NOT NULL,
            belge_id TEXT NOT NULL,
            belge_adi TEXT NOT NULL,
            belge_tipi TEXT,
            base64_data TEXT NOT NULL,
            durum TEXT,
            cekme_tarihi TEXT NOT NULL,
            FOREIGN KEY (takip_no) REFERENCES basvurular(takip_no),
            UNIQUE(takip_no, belge_id)
        )
    """)

    # İndeksler
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_basvuru_hizmet ON basvurular(hizmet_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_belge_takip ON belgeler(takip_no)")

    conn.commit()
    conn.close()

def import_json_to_db(json_file: Path):
    """Tek bir JSON dosyasını veritabanına aktar"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    takip_no = data.get("basvuru_bilgileri", {}).get("takip_no")
    if not takip_no:
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Başvuru bilgileri
    basvuru_bilgileri = data.get("basvuru_bilgileri", {})
    simdi = datetime.now().isoformat()

    try:
        # Başvuruyu kaydet
        cursor.execute("""
            INSERT OR REPLACE INTO basvurular
            (takip_no, hizmet_id, basvuru_tarihi, ad_soyad, tc_no, durum, json_data, cekme_tarihi, son_guncelleme)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            takip_no,
            basvuru_bilgileri.get("hizmet_id"),
            basvuru_bilgileri.get("basvuru_tarihi"),
            basvuru_bilgileri.get("ad_soyad"),
            basvuru_bilgileri.get("tc_no"),
            basvuru_bilgileri.get("durum"),
            json.dumps(data, ensure_ascii=False),
            simdi,
            simdi
        ))

        # Belgeleri kaydet
        belgeler = data.get("belgeler", [])
        for belge in belgeler:
            belge_id = belge.get("belge_id")
            if not belge_id:
                continue

            cursor.execute("""
                INSERT OR REPLACE INTO belgeler
                (takip_no, belge_id, belge_adi, belge_tipi, base64_data, durum, cekme_tarihi)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                takip_no,
                belge_id,
                belge.get("belge_adi"),
                belge.get("belge_tipi"),
                belge.get("base64", ""),
                belge.get("durum"),
                simdi
            ))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        conn.close()
        print(f"      ❌ Hata: {str(e)}")
        return False

def main():
    print("=" * 80)
    print("MEVCUT JSON DOSYALARINI VERİTABANINA AKTAR")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Veritabanını hazırla
    print("📦 Veritabanı hazırlanıyor...")
    init_db()

    # JSON dosyalarını bul
    output_dir = Path("output")
    json_files = list(output_dir.glob("basvuru_*.json"))

    print(f"📁 {len(json_files)} JSON dosyası bulundu")
    print()

    basarili = 0
    basarisiz = 0

    for idx, json_file in enumerate(json_files, 1):
        takip_no = json_file.stem.replace("basvuru_", "")
        print(f"   [{idx}/{len(json_files)}] {takip_no}...", end=" ")

        if import_json_to_db(json_file):
            print("✅")
            basarili += 1
        else:
            print("❌")
            basarisiz += 1

    # İstatistikler
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM basvurular")
    toplam_basvuru = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM belgeler")
    toplam_belge = cursor.fetchone()[0]

    cursor.execute("SELECT hizmet_id, COUNT(*) FROM basvurular WHERE hizmet_id IS NOT NULL GROUP BY hizmet_id")
    hizmet_istatistikleri = cursor.fetchall()

    conn.close()

    print()
    print("=" * 80)
    print("ÖZET")
    print("=" * 80)
    print(f"✅ Başarılı: {basarili}")
    print(f"❌ Başarısız: {basarisiz}")
    print()
    print(f"📊 Veritabanı:")
    print(f"   • Toplam başvuru: {toplam_basvuru}")
    print(f"   • Toplam belge: {toplam_belge}")
    print()
    if hizmet_istatistikleri:
        print(f"   Hizmet bazında:")
        for hizmet_id, count in hizmet_istatistikleri:
            print(f"   • {hizmet_id or 'Bilinmeyen'}: {count} başvuru")
    print()
    print(f"💾 Veritabanı: {DB_PATH.absolute()}")
    print()

if __name__ == "__main__":
    main()
