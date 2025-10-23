"""
Tüm başvuru verilerini API'den çekip SQLite veritabanına kaydeder
Tekrar çalıştırıldığında sadece yeni başvuruları çeker
"""
import sys
import os
from datetime import datetime
from pathlib import Path
import json
import sqlite3

# Proje root dizinini path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.external_api_client import ExternalAPIClient
from app.config import settings

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
            hizmet_id TEXT NOT NULL,
            basvuru_tarihi TEXT,
            durum TEXT,
            basvuru_listesi_json TEXT,
            basvuru_detay_json TEXT,
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
            dosya_adi TEXT,
            base64_data TEXT NOT NULL,
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
    print("✅ Veritabanı hazır")

def basvuru_var_mi(takip_no: str) -> bool:
    """Başvuru daha önce çekilmiş mi?"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM basvurular WHERE takip_no = ?", (takip_no,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def basvuru_kaydet(basvuru_data: dict, detay_data: dict, belgeler: list):
    """Başvuruyu ve belgelerini veritabanına kaydet"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    takip_no = basvuru_data.get("takipNo")
    hizmet_id = basvuru_data.get("hizmetId")
    basvuru_tarihi = basvuru_data.get("basvuruTarihi")
    durum = basvuru_data.get("durum")
    simdi = datetime.now().isoformat()

    # Başvuruyu kaydet
    cursor.execute("""
        INSERT OR REPLACE INTO basvurular
        (takip_no, hizmet_id, basvuru_tarihi, durum, basvuru_listesi_json,
         basvuru_detay_json, cekme_tarihi, son_guncelleme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        takip_no,
        hizmet_id,
        basvuru_tarihi,
        durum,
        json.dumps(basvuru_data, ensure_ascii=False),
        json.dumps(detay_data, ensure_ascii=False),
        simdi,
        simdi
    ))

    # Belgeleri kaydet
    for belge in belgeler:
        cursor.execute("""
            INSERT OR REPLACE INTO belgeler
            (takip_no, belge_id, belge_adi, belge_tipi, dosya_adi, base64_data, cekme_tarihi)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            takip_no,
            belge.get("belge_id"),
            belge.get("belge_adi"),
            belge.get("belge_tipi"),
            belge.get("dosya_adi"),
            belge.get("base64"),
            simdi
        ))

    conn.commit()
    conn.close()

def get_stats():
    """Veritabanı istatistiklerini getir"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM basvurular")
    toplam_basvuru = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM belgeler")
    toplam_belge = cursor.fetchone()[0]

    cursor.execute("SELECT hizmet_id, COUNT(*) FROM basvurular GROUP BY hizmet_id")
    hizmet_istatistikleri = cursor.fetchall()

    conn.close()

    return {
        "toplam_basvuru": toplam_basvuru,
        "toplam_belge": toplam_belge,
        "hizmet_istatistikleri": hizmet_istatistikleri
    }

def main():
    print("=" * 80)
    print("BAŞVURU VERİLERİNİ VERİTABANINA SENKRONIZE ET")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Veritabanını hazırla
    init_db()

    # Başlangıç istatistikleri
    onceki_stats = get_stats()
    print(f"📊 Mevcut durum:")
    print(f"   • Başvuru: {onceki_stats['toplam_basvuru']}")
    print(f"   • Belge: {onceki_stats['toplam_belge']}")
    print()

    # API client
    api_client = ExternalAPIClient(
        base_url=settings.EXTERNAL_API_URL,
        username=settings.EXTERNAL_API_USERNAME,
        password=settings.EXTERNAL_API_PASSWORD,
        timeout=settings.EXTERNAL_API_TIMEOUT
    )

    print(f"📡 API: {settings.EXTERNAL_API_URL}")
    print(f"🔧 Hizmetler: {', '.join(settings.HIZMET_IDS)}")
    print()

    yeni_basvuru_sayisi = 0
    atlanan_basvuru_sayisi = 0
    hata_sayisi = 0

    # Her hizmet için başvuruları çek
    for hizmet_idx, hizmet_id in enumerate(settings.HIZMET_IDS, 1):
        print(f"\n{'='*80}")
        print(f"🔍 HİZMET {hizmet_idx}/{len(settings.HIZMET_IDS)}: {hizmet_id}")
        print('='*80)

        try:
            # Başvuru listesini çek
            basvurular = api_client.get_basvuru_listesi(hizmet_id=hizmet_id)

            if not basvurular:
                print(f"   ⚠️  Başvuru bulunamadı")
                continue

            print(f"   ✅ {len(basvurular)} başvuru bulundu")

            # Her başvuru için
            for basvuru_idx, basvuru in enumerate(basvurular, 1):
                takip_no = basvuru.get("takipNo")

                if not takip_no:
                    print(f"   ⚠️  #{basvuru_idx}: Takip no yok")
                    continue

                # Daha önce çekilmiş mi kontrol et
                if basvuru_var_mi(takip_no):
                    print(f"   ⏭️  #{basvuru_idx}/{len(basvurular)}: {takip_no} (zaten mevcut)")
                    atlanan_basvuru_sayisi += 1
                    continue

                try:
                    print(f"   📥 #{basvuru_idx}/{len(basvurular)}: {takip_no}")

                    # Detayları çek
                    detay = api_client.get_basvuru_detay(takip_no)
                    belgeler_list = detay.get("belgeler", [])

                    # Belgeleri çek
                    belgeler_with_content = []
                    for belge in belgeler_list:
                        belge_id = belge.get("belge_id")
                        belge_adi = belge.get("belge_adi", "unknown")

                        if not belge_id:
                            continue

                        try:
                            belge_data = api_client.get_belge(takip_no, belge_id)
                            belgeler_with_content.append({
                                "belge_id": belge_id,
                                "belge_adi": belge_adi,
                                "belge_tipi": belge.get("belge_tipi"),
                                "base64": belge_data.get("base64"),
                                "dosya_adi": belge_data.get("dosyaAdi"),
                            })
                        except Exception as e:
                            print(f"      ⚠️  Belge hatası ({belge_adi}): {str(e)[:40]}")

                    # Veritabanına kaydet
                    basvuru_kaydet(basvuru, detay, belgeler_with_content)
                    yeni_basvuru_sayisi += 1
                    print(f"      ✅ Kaydedildi ({len(belgeler_with_content)} belge)")

                except Exception as e:
                    print(f"      ❌ Hata: {str(e)[:80]}")
                    hata_sayisi += 1
                    continue

        except Exception as e:
            print(f"   ❌ Hizmet hatası: {str(e)[:100]}")
            continue

    # Son istatistikler
    sonraki_stats = get_stats()

    print()
    print("=" * 80)
    print("ÖZET")
    print("=" * 80)
    print(f"✅ Yeni başvuru: {yeni_basvuru_sayisi}")
    print(f"⏭️  Atlanan başvuru: {atlanan_basvuru_sayisi}")
    print(f"❌ Hata: {hata_sayisi}")
    print()
    print(f"📊 Veritabanı:")
    print(f"   • Toplam başvuru: {onceki_stats['toplam_basvuru']} → {sonraki_stats['toplam_basvuru']}")
    print(f"   • Toplam belge: {onceki_stats['toplam_belge']} → {sonraki_stats['toplam_belge']}")
    print()
    print(f"   Hizmet bazında:")
    for hizmet_id, count in sonraki_stats['hizmet_istatistikleri']:
        print(f"   • {hizmet_id}: {count} başvuru")
    print()
    print(f"💾 Veritabanı: {DB_PATH.absolute()}")
    print()

if __name__ == "__main__":
    main()
