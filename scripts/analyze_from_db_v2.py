"""
Veritabanındaki başvuruları DOĞRU şekilde analiz et:
1. Her başvuruyu al
2. Belgeleri base64'ten çıkar
3. Her belge için OCR yap
4. Uygun prompt ile analiz et
5. Sonuçları kaydet
"""
import sys
import os
from pathlib import Path
import json
import sqlite3
import base64
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.document_processor import DocumentProcessor
from app.prompts.prompt_factory import PromptFactory
from app.config import settings

DB_PATH = Path("data/basvurular.db")
TEMP_DIR = Path("temp/analiz")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def init_analiz_table():
    """Analiz sonuçları tablosu oluştur"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analiz_sonuclari (
            takip_no TEXT PRIMARY KEY,
            cv_analiz TEXT,
            sgk_analiz TEXT,
            diploma_analiz TEXT,
            sicil_analiz TEXT,
            diger_belgeler TEXT,
            analiz_tarihi TEXT NOT NULL,
            durum TEXT NOT NULL,
            FOREIGN KEY (takip_no) REFERENCES basvurular(takip_no)
        )
    """)

    conn.commit()
    conn.close()
    print("Analiz tablosu hazir")


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

    return [
        {
            "takip_no": row[0],
            "hizmet_id": row[1],
            "data": json.loads(row[2])
        }
        for row in results
    ]


# BU FONKSİYON ARTIK KULLANILMIYOR - API'den gelen belgeTipi kullanılıyor
# def belge_tipi_belirle(belge_adi: str) -> Optional[str]:
#     """Belge adından tipini belirle"""
#     belge_adi_lower = belge_adi.lower()
#
#     if "cv" in belge_adi_lower or "özgeçmiş" in belge_adi_lower or "ozgecmis" in belge_adi_lower:
#         return "cv"
#     elif "sgk" in belge_adi_lower or "hizmet" in belge_adi_lower or "sigorta" in belge_adi_lower:
#         return "sgk"
#     elif "diploma" in belge_adi_lower or "mezuniyet" in belge_adi_lower:
#         return "diploma"
#     elif "sicil" in belge_adi_lower or "sabıka" in belge_adi_lower or "sabika" in belge_adi_lower:
#         return "sicil"
#     else:
#         return "diger"


def belge_kaydet(takip_no: str, belge_adi: str, base64_data: str) -> Optional[Path]:
    """Belgeyi base64'ten dosyaya kaydet"""
    try:
        # Base64 decode
        belge_bytes = base64.b64decode(base64_data)

        # Dosya uzantısını belirle
        ext = Path(belge_adi).suffix.lower()
        if not ext:
            ext = ".pdf"  # Default PDF

        # Temp dosya oluştur
        belge_dir = TEMP_DIR / takip_no
        belge_dir.mkdir(parents=True, exist_ok=True)

        belge_path = belge_dir / f"{Path(belge_adi).stem}{ext}"

        with open(belge_path, 'wb') as f:
            f.write(belge_bytes)

        return belge_path

    except Exception as e:
        print(f"  HATA: Belge kaydedilemedi - {str(e)[:50]}")
        return None


def belge_analiz_et(
    processor: DocumentProcessor,
    belge_path: Path,
    belge_tipi: str,
    basvuru_turu: Optional[str] = None
) -> Optional[Dict]:
    """Belgeyi OCR + Prompt ile analiz et"""
    try:
        # OCR yap (NOT: OCR service async değil, Path object bekliyor)
        print(f"    OCR yapiliyor...", end=" ", flush=True)
        text = processor.ocr_service.extract_text(belge_path)  # Path object gönder, await yok
        print(f"OK ({len(text)} karakter)")

        # Boş veya çok kısa metinler için LLM'e gönderme
        if not text or len(text.strip()) < 10:
            # Sessizce atla, LLM'e gereksiz istek gönderme
            return {"error": "Metin boş veya çok kısa", "icerik_yok": True}

        # Prompt seç
        prompt_template = PromptFactory.create_prompt(belge_tipi, basvuru_turu)

        if not prompt_template:
            print(f"    UYARI: Prompt bulunamadi - {belge_tipi}")
            return {"error": f"Prompt bulunamadı: {belge_tipi}"}

        # Basit bir şema (gerçekte daha detaylı olmalı)
        schema = {"type": "object", "properties": {}}

        # Prompt hazırla
        system_prompt = prompt_template.get_system_prompt()
        user_prompt = prompt_template.get_user_prompt(text, schema)

        # Ollama'ya gönder
        print(f"    Ollama'ya gonderiliyor...", end=" ", flush=True)
        response = processor.ollama_service.generate(
            prompt=f"{system_prompt}\n\n{user_prompt}",
            temperature=0.0,
            format="json"
        )
        print("OK")

        return json.loads(response["response"])

    except Exception as e:
        print(f"    HATA: {str(e)[:80]}")
        return {"error": str(e)}


def basvuru_analiz_et(processor: DocumentProcessor, basvuru: Dict) -> Dict:
    """Başvurunun TÜM belgelerini analiz et"""
    takip_no = basvuru["takip_no"]
    data = basvuru["data"]

    print(f"\n{takip_no} analiz ediliyor...")
    print(f"  Hizmet: {data.get('hizmetAdi', 'Bilinmiyor')}")

    # Belgeleri al
    belgeler = data.get("basvuruBelgeListesi", [])
    print(f"  Belge sayisi: {len(belgeler)}")

    sonuclar = {
        "cv_analiz": None,
        "sgk_analiz": None,
        "diploma_analiz": None,
        "sicil_analiz": None,
        "diger_belgeler": []
    }

    # Her belgeyi işle
    for idx, belge in enumerate(belgeler, 1):
        belge_adi = belge.get("belgeAdi", f"belge_{idx}")
        base64_data = belge.get("dosyaByte")  # API'deki alan adı
        api_belge_tipi = belge.get("belgeTipi")  # API'den gelen belge tipi

        if not base64_data:
            print(f"  [{idx}/{len(belgeler)}] {belge_adi} - ATLA (base64 yok)")
            continue

        print(f"  [{idx}/{len(belgeler)}] {belge_adi}")

        # API'den gelen belgeTipi'ni kullan (DocumentClassifier ile normalize et)
        from app.core.document_classifier import DocumentClassifier
        classifier = DocumentClassifier()
        belge_tipi = classifier.classify(
            filename=belge_adi,
            text=None,
            belge_tipi=api_belge_tipi
        )
        print(f"    API belgeTipi: '{api_belge_tipi}' → '{belge_tipi}'")

        # Belgeyi kaydet
        belge_path = belge_kaydet(takip_no, belge_adi, base64_data)
        if not belge_path:
            continue

        # Analiz et
        basvuru_turu = None  # TODO: API'den basvuru türünü al
        analiz = belge_analiz_et(processor, belge_path, belge_tipi, basvuru_turu)

        # Sonuca ekle
        if belge_tipi == "cv":
            sonuclar["cv_analiz"] = analiz
        elif belge_tipi == "sgk":
            sonuclar["sgk_analiz"] = analiz
        elif belge_tipi == "diploma":
            sonuclar["diploma_analiz"] = analiz
        elif belge_tipi == "sicil":
            sonuclar["sicil_analiz"] = analiz
        else:
            sonuclar["diger_belgeler"].append({
                "belge_adi": belge_adi,
                "analiz": analiz
            })

        # Temp dosyayı sil
        try:
            belge_path.unlink()
        except:
            pass

    return sonuclar


def analiz_kaydet(takip_no: str, sonuclar: Dict, durum: str):
    """Analiz sonuçlarını kaydet"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO analiz_sonuclari (
            takip_no, cv_analiz, sgk_analiz, diploma_analiz, sicil_analiz,
            diger_belgeler, analiz_tarihi, durum
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        takip_no,
        json.dumps(sonuclar.get("cv_analiz"), ensure_ascii=False) if sonuclar.get("cv_analiz") else None,
        json.dumps(sonuclar.get("sgk_analiz"), ensure_ascii=False) if sonuclar.get("sgk_analiz") else None,
        json.dumps(sonuclar.get("diploma_analiz"), ensure_ascii=False) if sonuclar.get("diploma_analiz") else None,
        json.dumps(sonuclar.get("sicil_analiz"), ensure_ascii=False) if sonuclar.get("sicil_analiz") else None,
        json.dumps(sonuclar.get("diger_belgeler", []), ensure_ascii=False),
        datetime.now().isoformat(),
        durum
    ))

    conn.commit()
    conn.close()


def main():
    print("=" * 80)
    print("DOGRU ANALIZ - Belge bazli")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Tablo oluştur
    init_analiz_table()

    # Processor başlat
    print(f"\nOllama: {settings.OLLAMA_BASE_URL}")
    print(f"Model: {settings.OLLAMA_MODEL}")
    processor = DocumentProcessor()

    # Analiz edilmemiş başvuruları al (ilk 1 tane test için)
    print("\nAnaliz edilmemis basvurular aliniyor...")
    basvurular = get_analiz_edilmemis(limit=1)
    print(f"BULUNDU: {len(basvurular)} basvuru\n")

    if not basvurular:
        print("Analiz edilecek basvuru yok!")
        return

    # Her başvuruyu analiz et
    for idx, basvuru in enumerate(basvurular, 1):
        print(f"\n{'='*80}")
        print(f"BASVURU {idx}/{len(basvurular)}")
        print(f"{'='*80}")

        try:
            sonuclar = basvuru_analiz_et(processor, basvuru)
            analiz_kaydet(basvuru["takip_no"], sonuclar, "basarili")
            print(f"\n  BASARILI: {basvuru['takip_no']}")

        except Exception as e:
            print(f"\n  HATA: {str(e)}")
            analiz_kaydet(basvuru["takip_no"], {"error": str(e)}, "hata")

    print("\n" + "=" * 80)
    print("ANALIZ TAMAMLANDI")
    print("=" * 80)


if __name__ == "__main__":
    main()
