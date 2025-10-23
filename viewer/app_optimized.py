"""
FastAPI web server - Belge görüntüleyici (OPTİMİZE EDİLMİŞ)

İyileştirmeler:
1. Sadece işlenmiş başvuruları göster (HIZLI!)
2. Sol menüde hafif veri (isim, takip no, durum)
3. Detay tıklandığında tam veri çek
"""
import os
import json
import base64
import io
import sqlite3
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CSB eBasvuru Viewer", version="2.0.0")

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proje dizinleri
PROJECT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"
TEMP_DIR = PROJECT_DIR / "temp"
STATIC_DIR = Path(__file__).parent / "static"
DB_PATH = PROJECT_DIR / "data" / "basvurular.db"

# Static dosyalar
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Ana sayfa"""
    index_file = Path(__file__).parent / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "CSB eBasvuru Viewer API v2.0"}


@app.get("/api/applications")
async def get_applications() -> List[Dict]:
    """
    İşlenmiş başvuruları listele - SADECE ÖZET BİLGİ (HIZLI!)

    Returns:
        List of applications with summary info:
        - takip_no
        - basvuran (ad soyad)
        - durum (uygunluk)
        - analiz_tarihi
    """
    try:
        if not DB_PATH.exists():
            return []

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # analiz_sonuclari tablosu var mı kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analiz_sonuclari'")
        has_analiz_table = cursor.fetchone() is not None

        if not has_analiz_table:
            conn.close()
            return []

        # SADECE işlenmiş başvuruların ÖZET bilgilerini çek
        cursor.execute("""
            SELECT takip_no, analiz_json, analiz_tarihi
            FROM analiz_sonuclari
            WHERE durum = 'basarili'
            ORDER BY analiz_tarihi DESC
            LIMIT 200
        """)

        applications = []
        for row in cursor.fetchall():
            takip_no, analiz_json, analiz_tarihi = row

            try:
                # Sadece gerekli alanları parse et (tüm JSON'u değil!)
                analiz = json.loads(analiz_json)

                basvuran = analiz.get('basvuran', {})
                ad = basvuran.get('ad', '')
                soyad = basvuran.get('soyad', '')
                basvuran_ad = f"{ad} {soyad}".strip() or 'Bilinmiyor'

                uygunluk = analiz.get('uygunluk', {})
                genel_degerlendirme = uygunluk.get('genel_degerlendirme', 'Bilinmiyor')

                basvuru_bilgileri = analiz.get('basvuru_bilgileri', {})

                # SADECE ÖZET BİLGİ
                app_data = {
                    'takip_no': takip_no,
                    'basvuran': basvuran_ad,
                    'tc_no': basvuran.get('tc_kimlik_no', ''),
                    'durum': genel_degerlendirme,
                    'basvuru_turu': basvuru_bilgileri.get('basvuru_turu', ''),
                    'hizmet_adi': basvuru_bilgileri.get('hizmet_adi', ''),
                    'analiz_tarihi': analiz_tarihi
                }

                applications.append(app_data)

            except (json.JSONDecodeError, KeyError):
                continue

        conn.close()
        return applications

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/application/{takip_no}")
async def get_application(takip_no: str) -> Dict:
    """
    Belirli bir başvurunun TAM detaylarını getir

    Args:
        takip_no: Başvuru takip numarası

    Returns:
        Tam analiz JSON'u
    """
    try:
        if not DB_PATH.exists():
            raise HTTPException(status_code=404, detail='Veritabanı bulunamadı')

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # analiz_sonuclari tablosundan çek
        cursor.execute("""
            SELECT analiz_json, analiz_tarihi, durum
            FROM analiz_sonuclari
            WHERE takip_no = ?
        """, (takip_no,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail='Başvuru bulunamadı veya henüz işlenmemiş')

        analiz_json, analiz_tarihi, durum = row

        # Tam JSON'u döndür
        result = json.loads(analiz_json)
        result['_metadata'] = {
            'analiz_tarihi': analiz_tarihi,
            'durum': durum
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/document/{takip_no}/{belge_adi:path}")
async def get_document(takip_no: str, belge_adi: str):
    """Belge dosyasını getir (base64'ten)"""
    try:
        if not DB_PATH.exists():
            raise HTTPException(status_code=404, detail='Veritabanı bulunamadı')

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Analiz sonucundan belge listesini al
        cursor.execute("SELECT analiz_json FROM analiz_sonuclari WHERE takip_no = ?", (takip_no,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail='Başvuru bulunamadı')

        analiz = json.loads(row[0])
        belgeler = analiz.get('belgeler', [])

        # Belgeyi bul
        for belge in belgeler:
            if belge.get('belge_adi') == belge_adi:
                base64_data = belge.get('base64')
                if not base64_data:
                    raise HTTPException(status_code=404, detail='Belge base64 verisi bulunamadı')

                # Base64'ü decode et
                file_bytes = base64.b64decode(base64_data)

                # Content type'ı belirle
                content_type = 'application/octet-stream'
                if belge_adi.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif belge_adi.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif belge_adi.lower().endswith('.png'):
                    content_type = 'image/png'
                elif belge_adi.lower().endswith('.docx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

                return Response(content=file_bytes, media_type=content_type)

        raise HTTPException(status_code=404, detail='Belge bulunamadı')

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats() -> Dict:
    """İstatistikleri getir"""
    try:
        stats = {
            'toplam_basvuru': 0,
            'analiz_edilmis': 0,
            'uygun': 0,
            'uygun_degil': 0,
            'degerlendiriliyor': 0,
            'hizmet_bazinda': {}
        }

        if not DB_PATH.exists():
            return stats

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Toplam başvuru sayısı
        cursor.execute("SELECT COUNT(*) FROM basvurular")
        stats['toplam_basvuru'] = cursor.fetchone()[0]

        # Analiz edilmiş sayısı
        cursor.execute("SELECT COUNT(*) FROM analiz_sonuclari WHERE durum = 'basarili'")
        stats['analiz_edilmis'] = cursor.fetchone()[0]

        # Uygunluk bazında istatistikler
        cursor.execute("SELECT analiz_json FROM analiz_sonuclari WHERE durum = 'basarili'")
        for row in cursor.fetchall():
            try:
                analiz = json.loads(row[0])
                uygunluk = analiz.get('uygunluk', {})
                genel = uygunluk.get('genel_degerlendirme', '')

                if 'UYGUN DEĞİL' in genel:
                    stats['uygun_degil'] += 1
                elif 'UYGUN' in genel and 'DEĞİL' not in genel:
                    stats['uygun'] += 1
                else:
                    stats['degerlendiriliyor'] += 1

                # Hizmet bazında
                basvuru_bilgileri = analiz.get('basvuru_bilgileri', {})
                hizmet_adi = basvuru_bilgileri.get('hizmet_adi', 'Bilinmiyor')
                if hizmet_adi not in stats['hizmet_bazinda']:
                    stats['hizmet_bazinda'][hizmet_adi] = 0
                stats['hizmet_bazinda'][hizmet_adi] += 1

            except:
                continue

        conn.close()
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import sys
    import io

    # Windows encoding fix
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("CSB eBasvuru Belge Görüntüleyici v2.0 (OPTİMİZE)")
    print("=" * 60)
    print(f"Veritabanı: {DB_PATH}")
    print(f"Tarayıcınızda açın: http://localhost:8000")
    print("=" * 60)
    print()
    print("İyileştirmeler:")
    print("  ✓ Sadece işlenmiş başvurular gösteriliyor")
    print("  ✓ Sol menü hafif veri kullanıyor (hızlı!)")
    print("  ✓ Detay tıklandığında tam veri çekiliyor")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
