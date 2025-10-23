"""
FastAPI web server - Belge görüntüleyici
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

app = FastAPI(title="CSB eBasvuru Viewer", version="1.0.0")

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
    return {"message": "CSB eBasvuru Viewer API"}

@app.get("/degerlendirme.html")
async def degerlendirme():
    """Değerlendirme sayfası"""
    degerlendirme_file = Path(__file__).parent / "degerlendirme.html"
    if degerlendirme_file.exists():
        return FileResponse(
            degerlendirme_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="Sayfa bulunamadı")

@app.get("/basvuru_json.html")
async def basvuru_json_page():
    """Başvuru JSON görüntüleyici sayfası"""
    json_file = Path(__file__).parent / "basvuru_json.html"
    if json_file.exists():
        return FileResponse(
            json_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="Sayfa bulunamadı")


@app.get("/api/basvuru_json/{takip_no}")
async def get_basvuru_json(takip_no: str) -> Dict:
    """SADECE başvuru JSON'ını getir (analiz YOK)"""
    try:
        if not DB_PATH.exists():
            raise HTTPException(status_code=404, detail='Veritabanı bulunamadı')

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Sadece başvuru JSON'ını getir
        cursor.execute("SELECT json_data FROM basvurular WHERE takip_no = ?", (takip_no,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail='Başvuru bulunamadı')

        json_data = row[0]
        data = json.loads(json_data)

        conn.close()
        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/applications")
async def get_applications() -> List[Dict]:
    """YENİ VERİTABANI: Analiz edilmiş başvuruları listele"""
    try:
        if not DB_PATH.exists():
            return []

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Yeni veritabanından chunk bazlı analiz sonuçlarını getir
        cursor.execute("""
            SELECT DISTINCT
                b.takipNo,
                MAX(l.islem_bitis) as analiz_tarihi,
                CASE WHEN SUM(l.basarili) > 0 THEN 'basarili' ELSE 'hata' END as analiz_durumu
            FROM basvurular b
            INNER JOIN belgeler bel ON b.basvuruId = bel.basvuruId
            INNER JOIN belge_analiz_log l ON bel.belgeId = l.belgeId
            WHERE l.basarili = 1
            GROUP BY b.takipNo
            ORDER BY analiz_tarihi DESC
            LIMIT 100
        """)

        applications = []
        for row in cursor.fetchall():
            applications.append({
                'takip_no': row['takipNo'],
                'analiz_tarihi': row['analiz_tarihi'],
                'analiz_durumu': row['analiz_durumu']
            })

        conn.close()
        return applications

    except Exception as e:
        print(f"ERROR in get_applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/application/{takip_no}")
async def get_application(takip_no: str) -> Dict:
    """Belirli bir başvurunun detaylarını getir (veritabanından)"""
    try:
        if not DB_PATH.exists():
            raise HTTPException(status_code=404, detail='Veritabanı bulunamadı')

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # analiz_sonuclari tablosu var mı kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analiz_sonuclari'")
        has_analiz_table = cursor.fetchone() is not None

        if has_analiz_table:
            # Başvuru ve analiz sonuçlarını getir
            cursor.execute("""
                SELECT b.takip_no, b.hizmet_id, b.json_data,
                       a.analiz_json, a.durum as analiz_durumu, a.analiz_tarihi
                FROM basvurular b
                LEFT JOIN analiz_sonuclari a ON b.takip_no = a.takip_no
                WHERE b.takip_no = ?
            """, (takip_no,))

            row = cursor.fetchone()
            if not row:
                conn.close()
                raise HTTPException(status_code=404, detail='Başvuru bulunamadı')

            takip_no, hizmet_id, json_data, analiz_json, analiz_durumu, analiz_tarihi = row
            data = json.loads(json_data)

            result = {
                'takip_no': takip_no,
                'hizmet_id': hizmet_id,
                'basvuru_data': data,
                'analiz_durumu': analiz_durumu,
                'analiz_tarihi': analiz_tarihi
            }

            if analiz_json:
                result['analiz'] = json.loads(analiz_json)
        else:
            # Sadece başvuruyu getir - ham JSON'u dön (henüz analiz yapılmamış)
            cursor.execute("SELECT takip_no, hizmet_id, json_data FROM basvurular WHERE takip_no = ?", (takip_no,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                raise HTTPException(status_code=404, detail='Başvuru bulunamadı')

            takip_no, hizmet_id, json_data = row
            raw_data = json.loads(json_data)

            # Ham API verisini dönüyoruz - frontend bu formatı bekliyor
            result = {
                'raw_api_data': raw_data,
                'takip_no': takip_no,
                'hizmet_id': hizmet_id,
                'message': 'Bu başvuru henüz analiz edilmemiş. Ham API verisi döndürülüyor.'
            }

        conn.close()
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/document/{takip_no}/{belge_adi:path}")
async def get_document(takip_no: str, belge_adi: str):
    """Belge dosyasını getir (veritabanından base64'ten)"""
    try:
        # Önce fiziksel dosyayı dene
        docs_dir = STATIC_DIR / "documents" / takip_no
        file_path = docs_dir / belge_adi

        if file_path.exists():
            return FileResponse(file_path)

        # Dosya yoksa veritabanından base64 data'yı kullan
        if not DB_PATH.exists():
            raise HTTPException(status_code=404, detail='Veritabanı bulunamadı')

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT json_data FROM basvurular WHERE takip_no = ?", (takip_no,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail='Başvuru bulunamadı')

        data = json.loads(row[0])

        # Belgeler listesinde ara (API format: basvuruBelgeListesi)
        belgeler = data.get('basvuruBelgeListesi', [])
        for belge in belgeler:
            if belge.get('belgeAdi') == belge_adi:
                base64_data = belge.get('dosyaByte')
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
    """YENİ VERİTABANI: İstatistikleri getir"""
    try:
        stats = {
            'toplam_basvuru': 0,
            'analiz_edilmis': 0,
            'analiz_bekleyen': 0,
            'analiz_basarili': 0,
            'analiz_hatali': 0
        }

        if not DB_PATH.exists():
            return stats

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Toplam başvuru sayısı
        cursor.execute("SELECT COUNT(*) FROM basvurular")
        stats['toplam_basvuru'] = cursor.fetchone()[0]

        # Analiz edilmiş başvuru sayısı (chunk_sonuclari'ndan)
        cursor.execute("""
            SELECT COUNT(DISTINCT b.basvuruId)
            FROM basvurular b
            INNER JOIN belgeler bel ON b.basvuruId = bel.basvuruId
            INNER JOIN belge_analiz_log l ON bel.belgeId = l.belgeId
            WHERE l.basarili = 1
        """)
        stats['analiz_edilmis'] = cursor.fetchone()[0]
        stats['analiz_basarili'] = stats['analiz_edilmis']  # Şu anlık hepsi başarılı kabul

        stats['analiz_bekleyen'] = stats['toplam_basvuru'] - stats['analiz_edilmis']
        stats['analiz_hatali'] = 0  # Şu anlık yok

        conn.close()
        return stats

    except Exception as e:
        print(f"ERROR in get_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import sys
    import io

    # Windows encoding fix
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("CSB eBasvuru Belge Goruntuleyici")
    print("=" * 60)
    print(f"Veritabani: {DB_PATH}")
    print(f"Tarayicinizda acin: http://localhost:8000")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
