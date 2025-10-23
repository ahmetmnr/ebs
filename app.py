"""
Yeşil Dönüşüm Başvuru Analiz Görüntüleme Sistemi
YENİ VERİTABANI YAPISI (chunk_sonuclari + belge_analiz_log)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import base64

from models.database import db

app = FastAPI(title="Yeşil Dönüşüm Analiz Viewer", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
TEMPLATE_DIR = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory="templates"), name="static")


@app.get("/")
async def root():
    """Ana sayfa"""
    return FileResponse(TEMPLATE_DIR / "index.html")


@app.get("/api/stats")
async def get_stats():
    """İstatistikler - YENİ VERİTABANI"""

    # Toplam başvuru
    q = "SELECT COUNT(*) as c FROM basvurular"
    toplam = db.fetchone(q)['c']

    # Analiz edilmiş (en az 1 belge analiz edilmiş)
    q = """
        SELECT COUNT(DISTINCT b.basvuruId) as c
        FROM basvurular b
        JOIN belgeler bel ON b.basvuruId = bel.basvuruId
        JOIN belge_analiz_log l ON bel.belgeId = l.belgeId
        WHERE l.basarili = 1
    """
    analiz_edilmis = db.fetchone(q)['c']

    # Toplam belge sayısı
    q = "SELECT COUNT(*) as c FROM belgeler"
    toplam_belge = db.fetchone(q)['c']

    # Başarılı belge sayısı
    q = "SELECT COUNT(*) as c FROM belge_analiz_log WHERE basarili = 1"
    basarili_belge = db.fetchone(q)['c']

    # Başarısız belge sayısı
    q = "SELECT COUNT(*) as c FROM belge_analiz_log WHERE basarili = 0"
    basarisiz_belge = db.fetchone(q)['c']

    # Analiz edilmemiş belge sayısı
    q = """
        SELECT COUNT(*) as c FROM belgeler bel
        WHERE NOT EXISTS (
            SELECT 1 FROM belge_analiz_log l WHERE l.belgeId = bel.belgeId
        )
    """
    analiz_edilmemis_belge = db.fetchone(q)['c']

    # Toplam chunk
    q = "SELECT COUNT(*) as c FROM chunk_sonuclari"
    chunk = db.fetchone(q)['c']

    return {
        'toplam_basvuru': toplam,
        'analiz_edilmis': analiz_edilmis,
        'analiz_basarili': analiz_edilmis,
        'bekleyen': toplam - analiz_edilmis,
        'toplam_belge': toplam_belge,
        'basarili_belge': basarili_belge,
        'basarisiz_belge': basarisiz_belge,
        'analiz_edilmemis_belge': analiz_edilmemis_belge,
        'toplam_chunk': chunk
    }


@app.get("/api/basvurular")
async def get_basvurular(limit: int = 50):
    """Başvuru listesi - YENİ VERİTABANI"""

    q = """
        SELECT
            b.basvuruId,
            b.takipNo,
            b.basvuruTarihi,
            b.hizmetAdi,
            b.basvuruYapanAd,
            b.basvuruYapanSoyad,
            b.basvuruDurum,
            COUNT(DISTINCT bel.belgeId) as toplam_belge,
            COUNT(DISTINCT l.id) as analiz_edilmis,
            MAX(l.islem_bitis) as son_analiz
        FROM basvurular b
        JOIN belgeler bel ON b.basvuruId = bel.basvuruId
        LEFT JOIN belge_analiz_log l ON bel.belgeId = l.belgeId AND l.basarili = 1
        GROUP BY b.basvuruId
        HAVING analiz_edilmis > 0
        ORDER BY son_analiz DESC
        LIMIT ?
    """

    return db.fetchall(q, (limit,))


@app.get("/api/basvuru/{takip_no}")
async def get_basvuru_detay(takip_no: str):
    """Başvuru detayı + TÜM BELGE ANALİZLERİ"""

    # Başvuru bilgileri
    q = "SELECT * FROM basvurular WHERE takipNo = ?"
    basvuru = db.fetchone(q, (takip_no,))

    if not basvuru:
        raise HTTPException(404, "Başvuru bulunamadı")

    # Belgeler + analizleri
    q = """
        SELECT
            bel.belgeId,
            bel.belgeAdi,
            bel.belgeTipi,
            bel.belge_boyutu_bytes,
            l.id as log_id,
            l.basarili,
            l.chunk_sayisi,
            l.islem_suresi_sn,
            l.islem_bitis
        FROM belgeler bel
        LEFT JOIN belge_analiz_log l ON bel.belgeId = l.belgeId
        WHERE bel.basvuruId = ?
        ORDER BY bel.belgeId
    """

    belgeler = db.fetchall(q, (basvuru['basvuruId'],))

    # Her belge için chunk sonuçlarını getir
    for belge in belgeler:
        if belge['log_id']:
            q = """
                SELECT chunk_index, chunk_start, chunk_end, response_json
                FROM chunk_sonuclari
                WHERE log_id = ?
                ORDER BY chunk_index
            """
            chunks = db.fetchall(q, (belge['log_id'],))

            # JSON parse et
            for chunk in chunks:
                chunk['data'] = json.loads(chunk['response_json'])
                del chunk['response_json']

            belge['chunks'] = chunks

            # İlk chunk'ın datasını da belge seviyesinde göster
            if chunks:
                belge['analiz_data'] = chunks[0]['data']
        else:
            belge['chunks'] = []
            belge['analiz_data'] = None

    return {
        'basvuru': dict(basvuru),
        'belgeler': belgeler
    }


@app.get("/api/belge/{belge_id}")
async def get_belge_download(belge_id: int):
    """Belge indirme - base64'ten"""

    q = """
        SELECT bel.belgeAdi, bel.belgeIcerik, b.takipNo
        FROM belgeler bel
        JOIN basvurular b ON bel.basvuruId = b.basvuruId
        WHERE bel.belgeId = ?
    """

    belge = db.fetchone(q, (belge_id,))

    if not belge or not belge['belgeIcerik']:
        raise HTTPException(404, "Belge bulunamadı")

    # Base64 decode
    content = base64.b64decode(belge['belgeIcerik'])

    # Content type
    filename = belge['belgeAdi']
    if filename.endswith('.pdf'):
        media_type = 'application/pdf'
    elif filename.endswith(('.jpg', '.jpeg')):
        media_type = 'image/jpeg'
    elif filename.endswith('.png'):
        media_type = 'image/png'
    else:
        media_type = 'application/octet-stream'

    return Response(
        content=content,
        media_type=media_type,
        headers={'Content-Disposition': f'inline; filename="{filename}"'}
    )


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Yeşil Dönüşüm Analiz Görüntüleyici")
    print("=" * 60)
    print("Tarayıcınızda açın: http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
