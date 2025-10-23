"""
Veritabanındaki başvuruları analiz et ve Master JSON oluştur

AKIŞ:
1. Veritabanından başvuru çek
2. Belgeleri base64'ten decode et
3. OCR + LLM ile belgeleri analiz et
4. Master JSON oluştur
5. Sonuçları veritabanına kaydet
6. LLM loglarını takip_no klasörüne kaydet
"""
import sys
import os
from pathlib import Path
import json
import sqlite3
import base64
import argparse
from datetime import datetime
from typing import Dict, List, Optional
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.document_processor import DocumentProcessor
from app.config import settings

DB_PATH = Path("data/basvurular.db")
TEMP_DIR = Path("temp/analiz")
LLM_LOGS_DIR = Path("llm_logs")

TEMP_DIR.mkdir(parents=True, exist_ok=True)
LLM_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def init_analiz_table():
    """Analiz sonuçları tablosu oluştur"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analiz_sonuclari (
            takip_no TEXT PRIMARY KEY,
            master_json TEXT NOT NULL,
            analiz_tarihi TEXT NOT NULL,
            durum TEXT NOT NULL,
            FOREIGN KEY (takip_no) REFERENCES basvurular(takip_no)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Analiz tablosu hazir")


def get_analiz_edilmemis(limit: int = 10) -> List[Dict]:
    """Analiz edilmemiş başvuruları getir"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT b.takip_no, b.hizmet_id, b.json_data
        FROM basvurular b
        LEFT JOIN analiz_sonuclari a ON b.takip_no = a.takip_no
        WHERE a.takip_no IS NULL
        LIMIT {limit}
    """)

    results = cursor.fetchall()
    conn.close()

    basvurular = []
    for row in results:
        takip_no = row[0]
        hizmet_id = row[1]
        data = json.loads(row[2])

        # Belgeleri hazırla
        belgeler = []
        for belge in data.get("basvuruBelgeListesi", []):
            belgeler.append({
                "belge_adi": belge.get("belgeAdi"),
                "belge_tipi": belge.get("belgeTipi"),
                "base64_data": belge.get("dosyaByte")
            })

        basvurular.append({
            "takip_no": takip_no,
            "hizmet_id": hizmet_id,
            "hizmet_adi": data.get("hizmetAdi", ""),
            "basvuru_tarihi": data.get("basvuruTarihi", ""),
            "belgeler": belgeler
        })

    return basvurular


def belge_kaydet(takip_no: str, belge_adi: str, base64_data: str) -> Optional[Path]:
    """Belgeyi base64'ten dosyaya kaydet"""
    try:
        # Base64 decode
        belge_bytes = base64.b64decode(base64_data)

        # Dosya uzantısını belirle
        ext = Path(belge_adi).suffix.lower()
        if not ext:
            ext = ".pdf"

        # Temp dosya oluştur
        belge_dir = TEMP_DIR / takip_no
        belge_dir.mkdir(parents=True, exist_ok=True)

        belge_path = belge_dir / f"{Path(belge_adi).stem}{ext}"

        with open(belge_path, 'wb') as f:
            f.write(belge_bytes)

        return belge_path

    except Exception as e:
        print(f"    ❌ HATA: Belge kaydedilemedi - {str(e)[:50]}")
        return None


def save_llm_log(takip_no: str, belge_adi: str, request: str, response: str):
    """LLM isteği ve yanıtını takip numarasına göre kaydet"""
    try:
        log_dir = LLM_LOGS_DIR / takip_no
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{timestamp}_{Path(belge_adi).stem}.json"

        log_data = {
            "takip_no": takip_no,
            "belge_adi": belge_adi,
            "timestamp": datetime.now().isoformat(),
            "request": request,
            "response": response
        }

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"    ⚠️  LLM log kaydedilemedi: {str(e)[:50]}")


async def basvuru_analiz_et(processor: DocumentProcessor, basvuru: Dict) -> Dict:
    """
    Başvuruyu analiz et ve Master JSON oluştur

    DocumentProcessor.process_application() kullanılır:
    - Tüm belgeleri OCR + LLM ile analiz eder
    - Validasyon ve requirements kontrolü yapar
    - Master JSON oluşturur
    - Tabloları oluşturur
    """
    takip_no = basvuru["takip_no"]

    print(f"\n{'='*80}")
    print(f"📄 {takip_no}")
    print(f"{'='*80}")
    print(f"  Hizmet: {basvuru['hizmet_adi']}")
    print(f"  Belge sayisi: {len(basvuru['belgeler'])}")

    # Belgeleri base64'ten dosyalara kaydet
    belgeler_with_paths = []
    for idx, belge in enumerate(basvuru["belgeler"], 1):
        belge_adi = belge["belge_adi"]
        base64_data = belge["base64_data"]
        belge_tipi = belge["belge_tipi"]

        if not base64_data:
            print(f"  [{idx}/{len(basvuru['belgeler'])}] {belge_adi} - ATLA (base64 yok)")
            continue

        print(f"  [{idx}/{len(basvuru['belgeler'])}] {belge_adi}")
        print(f"    belgeTipi: {belge_tipi}")

        belge_path = belge_kaydet(takip_no, belge_adi, base64_data)
        if belge_path:
            belgeler_with_paths.append({
                "belge_id": idx,  # Belge ID
                "belge_adi": belge_adi,
                "belge_path": belge_path,
                "belge_tipi": belge_tipi,
                "base64": base64_data  # Base64 data
            })

    # DocumentProcessor ile işle
    # process_application() ASYNC fonksiyon ve master JSON döndürür
    basvuru_data = {
        "basvuru_id": basvuru.get("takip_no"),  # Unique ID
        "takip_no": takip_no,
        "basvuru_tarihi": basvuru["basvuru_tarihi"],
        "hizmet_adi": basvuru["hizmet_adi"],
        "belgeler": belgeler_with_paths
    }

    print(f"\n  🔄 DocumentProcessor ile analiz ediliyor...")
    master_json = await processor.process_application(basvuru_data)

    # Temp dosyaları temizle
    try:
        for belge in belgeler_with_paths:
            belge["belge_path"].unlink()
        (TEMP_DIR / takip_no).rmdir()
    except:
        pass

    return master_json


def analiz_kaydet(takip_no: str, master_json: Dict, durum: str):
    """Analiz sonuçlarını veritabanına kaydet"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO analiz_sonuclari (
            takip_no, master_json, analiz_tarihi, durum
        )
        VALUES (?, ?, ?, ?)
    """, (
        takip_no,
        json.dumps(master_json, ensure_ascii=False),
        datetime.now().isoformat(),
        durum
    ))

    conn.commit()
    conn.close()
    print(f"  💾 Veritabanına kaydedildi")


async def main():
    parser = argparse.ArgumentParser(description='Veritabanındaki başvuruları analiz et')
    parser.add_argument('--limit', type=int, default=10, help='Kaç başvuru analiz edilecek (default: 10)')
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 BAŞVURU ANALİZİ")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Tablo oluştur
    init_analiz_table()

    # Processor başlat
    print(f"\n🔗 Ollama: {settings.OLLAMA_BASE_URL}")
    print(f"🤖 Model: {settings.OLLAMA_MODEL}")
    processor = DocumentProcessor()

    # Analiz edilmemiş başvuruları al
    print(f"\n📥 Analiz edilmemiş başvurular alınıyor (limit: {args.limit})...")
    basvurular = get_analiz_edilmemis(limit=args.limit)
    print(f"✅ BULUNDU: {len(basvurular)} başvuru")

    if not basvurular:
        print("\n⚠️  Analiz edilecek başvuru yok!")
        return

    # Her başvuruyu analiz et
    basarili = 0
    hatali = 0

    for idx, basvuru in enumerate(basvurular, 1):
        try:
            master_json = await basvuru_analiz_et(processor, basvuru)
            analiz_kaydet(basvuru["takip_no"], master_json, "basarili")
            print(f"  ✅ BAŞARILI\n")
            basarili += 1

        except Exception as e:
            print(f"  ❌ HATA: {str(e)}\n")
            error_json = {"error": str(e), "timestamp": datetime.now().isoformat()}
            analiz_kaydet(basvuru["takip_no"], error_json, "hata")
            hatali += 1

    print("\n" + "=" * 80)
    print(f"✅ ANALİZ TAMAMLANDI")
    print(f"   Başarılı: {basarili}")
    print(f"   Hatalı: {hatali}")
    print(f"   Toplam: {basarili + hatali}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
