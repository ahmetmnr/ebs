"""
FastAPI Server - Başvuru Analiz Sonuçları API
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path
import json

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

from models.database import db

app = FastAPI(
    title="Yeşil Dönüşüm Başvuru Analiz API",
    description="Sanayide Yeşil Dönüşüm başvuru analiz sonuçlarını görüntüleme API'si",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Pydantic models
class BasvuruSummary(BaseModel):
    basvuruId: int
    takipNo: str
    basvuruTarihi: str
    hizmetAdi: str
    basvuruYapanAd: str
    basvuruYapanSoyad: str
    basvuruDurum: str
    islendiMi: int


class BelgeInfo(BaseModel):
    belgeId: int
    belgeAdi: str
    belgeTipi: Optional[str]
    analiz_edildi: int
    analiz_suresi_sn: Optional[float]


class Stats(BaseModel):
    toplam_basvuru: int
    islenen_basvuru: int
    basarili_analiz: int
    toplam_chunk: int


@app.get("/")
async def root():
    """Ana sayfa - HTML arayüzü"""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return FileResponse("static/index.html", headers=headers)


@app.get("/api/stats")
async def get_stats():
    """Genel istatistikler - YENİ VERİTABANI YAPISI"""

    # Toplam başvuru
    query = "SELECT COUNT(*) as count FROM basvurular"
    toplam_basvuru = db.fetchone(query)['count']

    # İşlenen başvuru
    query = "SELECT COUNT(*) as count FROM basvurular WHERE islendiMi = 1"
    islenen_basvuru = db.fetchone(query)['count']

    # Başarılı analiz sayısı (başvuru bazında)
    query = """
        SELECT COUNT(DISTINCT b.basvuruId) as count
        FROM basvurular b
        INNER JOIN belgeler bel ON b.basvuruId = bel.basvuruId
        INNER JOIN belge_analiz_log l ON bel.belgeId = l.belgeId
        WHERE l.basarili = 1
    """
    basarili_basvuru = db.fetchone(query)['count']

    # Toplam analiz edilen belge
    query = "SELECT COUNT(*) as count FROM belge_analiz_log WHERE basarili = 1"
    basarili_belge = db.fetchone(query)['count']

    # Toplam chunk
    query = "SELECT COUNT(*) as count FROM chunk_sonuclari"
    toplam_chunk = db.fetchone(query)['count']

    return {
        "toplam_basvuru": toplam_basvuru,
        "islenen_basvuru": islenen_basvuru,
        "basarili_analiz": basarili_basvuru,
        "basarili_belge": basarili_belge,
        "toplam_chunk": toplam_chunk
    }


@app.get("/api/basvurular/latest")
async def get_latest_basvurular(limit: int = 20):
    """Son işlenen başvurular - YENİ VERİTABANI YAPISI"""

    # Analiz edilmiş başvuruları getir
    query = """
        SELECT DISTINCT b.basvuruId, b.takipNo, b.basvuruTarihi, b.hizmetAdi,
               b.basvuruYapanAd, b.basvuruYapanSoyad, b.basvuruDurum,
               COUNT(DISTINCT bel.belgeId) as toplam_belge,
               COUNT(DISTINCT l.id) as analiz_edilmis_belge,
               SUM(CASE WHEN l.basarili = 1 THEN 1 ELSE 0 END) as basarili_analiz
        FROM basvurular b
        INNER JOIN belgeler bel ON b.basvuruId = bel.basvuruId
        LEFT JOIN belge_analiz_log l ON bel.belgeId = l.belgeId
        WHERE b.islendiMi = 1
        GROUP BY b.basvuruId
        HAVING analiz_edilmis_belge > 0
        ORDER BY b.basvuruId DESC
        LIMIT ?
    """

    results = db.fetchall(query, (limit,))
    return results


@app.get("/api/basvuru/takip/{takip_no}")
async def get_basvuru_by_takip(takip_no: str):
    """Takip numarasına göre başvuru detayı"""

    # Başvuru bilgileri
    query = """
        SELECT * FROM basvurular
        WHERE takipNo = ?
    """
    basvuru = db.fetchone(query, (takip_no,))

    if not basvuru:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    # Belgeler
    query = """
        SELECT b.belgeId, b.belgeAdi, b.belgeTipi, b.analiz_edildi,
               b.analiz_suresi_sn, b.belge_boyutu_bytes,
               l.id as log_id, l.basarili, l.chunk_sayisi, l.islem_suresi_sn
        FROM belgeler b
        LEFT JOIN belge_analiz_log l ON b.belgeId = l.belgeId
        WHERE b.basvuruId = ?
        ORDER BY b.belgeId
    """
    belgeler = db.fetchall(query, (basvuru['basvuruId'],))

    # Her belge için chunk sonuçlarını getir
    for belge in belgeler:
        if belge['log_id']:
            query = """
                SELECT chunk_index, response_json, chunk_start, chunk_end
                FROM chunk_sonuclari
                WHERE log_id = ?
                ORDER BY chunk_index
            """
            chunks = db.fetchall(query, (belge['log_id'],))

            # JSON parse et
            parsed_chunks = []
            for chunk in chunks:
                parsed_chunks.append({
                    'chunk_index': chunk['chunk_index'],
                    'chunk_start': chunk['chunk_start'],
                    'chunk_end': chunk['chunk_end'],
                    'data': json.loads(chunk['response_json'])
                })

            belge['chunks'] = parsed_chunks
        else:
            belge['chunks'] = []

    # Analiz sonuçlarını ekle
    query = "SELECT * FROM analiz_sonuclari WHERE basvuruId = ?"
    analiz = db.fetchone(query, (basvuru['basvuruId'],))

    return {
        'takip_no': takip_no,
        'basvuru': dict(basvuru),
        'belgeler': belgeler,
        'analiz': {
            'belgeler': belgeler,
            'tablolar': {},  # Tablolar şimdilik boş (gerekirse ekleriz)
            'sonuc': dict(analiz) if analiz else None
        }
    }


@app.get("/api/document/{takip_no}/{belge_adi}")
async def get_document(takip_no: str, belge_adi: str):
    """Belge dosyasını döndür"""
    import base64
    from io import BytesIO

    # Başvuruyu bul
    query = "SELECT basvuruId FROM basvurular WHERE takipNo = ?"
    basvuru = db.fetchone(query, (takip_no,))

    if not basvuru:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    # Belgeyi bul
    query = """
        SELECT belgeIcerik, belge_uzantisi
        FROM belgeler
        WHERE basvuruId = ? AND belgeAdi = ?
    """
    belge = db.fetchone(query, (basvuru['basvuruId'], belge_adi))

    if not belge or not belge['belgeIcerik']:
        raise HTTPException(status_code=404, detail="Belge bulunamadı")

    # Base64 decode
    try:
        file_data = base64.b64decode(belge['belgeIcerik'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Belge decode hatası: {str(e)}")

    # MIME type belirle
    uzanti = belge['belge_uzantisi'] or Path(belge_adi).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.txt': 'text/plain',
    }
    media_type = mime_types.get(uzanti, 'application/octet-stream')

    return Response(content=file_data, media_type=media_type)


@app.get("/api/basvuru/id/{basvuru_id}")
async def get_basvuru_by_id(basvuru_id: int):
    """Başvuru ID'ye göre başvuru detayı"""

    # Takip no'yu bul
    query = "SELECT takipNo FROM basvurular WHERE basvuruId = ?"
    result = db.fetchone(query, (basvuru_id,))

    if not result:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    return await get_basvuru_by_takip(result['takipNo'])


@app.get("/api/basvuru/{takip_no}/ozet")
async def get_basvuru_ozet(takip_no: str):
    """
    UI için temiz özet formatı

    Returns:
        {
          "basvuruId": 961482,
          "basvuru_bilgileri": {...},
          "sektor_bilgileri": {...},
          "dokuman_durumu": {...},
          "adli_sicil": {...},
          "mezuniyet": {...},
          "projeler": [...]
        }
    """

    # Başvuru bilgileri
    query = "SELECT * FROM basvurular WHERE takipNo = ?"
    basvuru = db.fetchone(query, (takip_no,))

    if not basvuru:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    basvuru_id = basvuru['basvuruId']

    # Analiz sonuçları
    query = "SELECT * FROM analiz_sonuclari WHERE basvuruId = ?"
    analiz = db.fetchone(query, (basvuru_id,))

    if not analiz:
        raise HTTPException(status_code=404, detail="Analiz sonucu bulunamadı")

    # Belge durumu kontrolü (hangi sektör belgeleri var?)
    query = """
        SELECT belgeTipi, COUNT(*) as adet
        FROM belgeler
        WHERE basvuruId = ? AND belgeTipi IS NOT NULL
        GROUP BY belgeTipi
    """
    belgeler = db.fetchall(query, (basvuru_id,))

    # Sektör belge durumu map'i
    dokuman_durumu = {
        "enerji": False,
        "metal": False,
        "kimya": False,
        "mineral": False,
        "atik": False,
        "diger": False
    }

    for belge in belgeler:
        belge_tipi = belge['belgeTipi']
        if 'Enerji' in belge_tipi:
            dokuman_durumu['enerji'] = True
        elif 'Metal' in belge_tipi:
            dokuman_durumu['metal'] = True
        elif 'Kimya' in belge_tipi:
            dokuman_durumu['kimya'] = True
        elif 'Mineral' in belge_tipi:
            dokuman_durumu['mineral'] = True
        elif 'Atık' in belge_tipi:
            dokuman_durumu['atik'] = True
        elif 'Diğer' in belge_tipi:
            dokuman_durumu['diger'] = True

    # Başvurulan sektörler (tecrübesi olan sektörler)
    basvurulan_sektorler = []
    if analiz.get('tecrube_enerji') and analiz['tecrube_enerji'] > 0:
        basvurulan_sektorler.append("Enerji")
    if analiz.get('tecrube_metal') and analiz['tecrube_metal'] > 0:
        basvurulan_sektorler.append("Metal")
    if analiz.get('tecrube_kimya') and analiz['tecrube_kimya'] > 0:
        basvurulan_sektorler.append("Kimya")
    if analiz.get('tecrube_mineral') and analiz['tecrube_mineral'] > 0:
        basvurulan_sektorler.append("Mineral")
    if analiz.get('tecrube_atik') and analiz['tecrube_atik'] > 0:
        basvurulan_sektorler.append("Atık")
    if analiz.get('tecrube_diger') and analiz['tecrube_diger'] > 0:
        basvurulan_sektorler.append("Diğer")

    # Projeler
    query = "SELECT tur, baslik, yil FROM proje_yayinlar WHERE basvuruId = ? ORDER BY sira_no"
    projeler_db = db.fetchall(query, (basvuru_id,))

    projeler = [
        {
            "tur": p['tur'],
            "baslik": p['baslik'],
            "yil": p['yil']
        }
        for p in projeler_db
    ]

    # Hizmet tipini belirle (Akademisyen/Sektör/Bakanlık)
    hizmet_adi = basvuru.get('hizmetAdi', '')
    if 'Akademisyen' in hizmet_adi:
        basvuru_turu = 'Akademisyen'
    elif 'Bakanlık' in hizmet_adi or 'Kamu' in hizmet_adi:
        basvuru_turu = 'Eski Bakanlık Personeli'
    elif 'Sektör' in hizmet_adi:
        basvuru_turu = 'Sektör Çalışanı'
    else:
        basvuru_turu = 'Diğer'

    if 'Baş Sorumlu' in hizmet_adi or 'Başsorumlu' in hizmet_adi:
        basvuru_turu += ' - Baş Sorumlu'
    elif 'Sorumlu' in hizmet_adi:
        basvuru_turu += ' - Sorumlu'

    # FINAL FORMAT
    return {
        "basvuruId": basvuru_id,
        "basvuru_bilgileri": {
            "ad_soyad": analiz.get('ad_soyad') or f"{basvuru.get('basvuruYapanAd', '')} {basvuru.get('basvuruYapanSoyad', '')}".strip(),
            "tc": analiz.get('tc_kimlik_no') or basvuru.get('basvuruYapanVatandasTC'),
            "basvuru_turu": basvuru_turu
        },
        "sektor_bilgileri": {
            "basvurulan_sektorler": basvurulan_sektorler,
            "tecrubeler": {
                "enerji": analiz.get('tecrube_enerji') or 0,
                "metal": analiz.get('tecrube_metal') or 0,
                "kimya": analiz.get('tecrube_kimya') or 0,
                "mineral": analiz.get('tecrube_mineral') or 0,
                "atik": analiz.get('tecrube_atik') or 0,
                "diger": analiz.get('tecrube_diger') or 0
            }
        },
        "dokuman_durumu": dokuman_durumu,
        "adli_sicil": {
            "var_mi": bool(analiz.get('adli_sicil_varmi')),
            "kod": None  # Adli sicil kodu şu an kaydedilmiyor
        },
        "mezuniyet": {
            "universite": analiz.get('mezun_universite'),
            "bolum": analiz.get('mezun_bolum'),
            "yil": analiz.get('mezuniyet_yili')
        },
        "diplomalar": json.loads(analiz.get('diploma_bilgileri_json')) if analiz.get('diploma_bilgileri_json') else [],
        "projeler": projeler
    }


@app.get("/api/search")
async def search_basvuru(
    takip_no: Optional[str] = None,
    tc: Optional[str] = None,
    ad_soyad: Optional[str] = None
):
    """Başvuru arama"""

    if takip_no:
        query = "SELECT basvuruId, takipNo FROM basvurular WHERE takipNo = ?"
        result = db.fetchone(query, (takip_no,))
    elif tc:
        query = "SELECT basvuruId, takipNo FROM basvurular WHERE basvuruYapanVatandasTC = ?"
        result = db.fetchone(query, (tc,))
    elif ad_soyad:
        query = """
            SELECT basvuruId, takipNo FROM basvurular
            WHERE basvuruYapanAd || ' ' || basvuruYapanSoyad LIKE ?
        """
        result = db.fetchone(query, (f"%{ad_soyad}%",))
    else:
        raise HTTPException(status_code=400, detail="En az bir arama kriteri gerekli")

    if not result:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı")

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
