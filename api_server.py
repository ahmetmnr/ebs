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


def _extract_sector_experience(sektor_dagilimi: List[Dict[str, Any]]) -> Dict[str, float]:
    """Master JSON sektör dağılımından sektörel deneyim yılı çıkar."""
    sektor_tecrubeleri = {
        "enerji": 0.0,
        "metal": 0.0,
        "kimya": 0.0,
        "mineral": 0.0,
        "atik": 0.0,
        "diger": 0.0,
    }

    sektor_map = {
        'enerji': 'enerji',
        'elektrik': 'enerji',
        'metal': 'metal',
        'çelik': 'metal',
        'demir': 'metal',
        'kimya': 'kimya',
        'petrokimya': 'kimya',
        'mineral': 'mineral',
        'çimento': 'mineral',
        'seramik': 'mineral',
        'madencilik': 'mineral',
        'atik': 'atik',
        'geri dönüşüm': 'atik',
    }

    for sektor_item in sektor_dagilimi or []:
        if not isinstance(sektor_item, dict):
            continue
        sektor_adi = (sektor_item.get('sektor_adi') or '').lower()
        matched = None
        for keyword, key in sektor_map.items():
            if keyword in sektor_adi:
                matched = key
                break
        if not matched:
            matched = 'diger'
        sektor_tecrubeleri[matched] += sektor_item.get('sure_yil') or 0

    return sektor_tecrubeleri


def _normalize_adli_sicil(adli_sicil: Dict[str, Any]) -> bool:
    """Adli sicil bilgisinden kayıt var mı bilgisini üret."""
    if not isinstance(adli_sicil, dict):
        return False

    sabika = adli_sicil.get('sabika_kaydi')
    yuz_kizartici = adli_sicil.get('yuz_kizartici_suc')

    if isinstance(yuz_kizartici, bool) and yuz_kizartici:
        return True

    if isinstance(sabika, bool):
        return sabika

    if isinstance(sabika, str):
        return sabika.strip().lower() not in {"", "yok", "temiz", "hayır", "hayir", "none"}

    return False


def master_json_to_legacy(master_json: Dict[str, Any], basvuru: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Master JSON'u eski analiz_sonuclari formatına dönüştür."""
    if not isinstance(master_json, dict):
        return None

    basvuran = master_json.get('basvuran') or {}
    basvuru_info = master_json.get('basvuru_bilgileri') or {}
    egitim = master_json.get('egitim_durumu') or {}
    is_deneyimi = master_json.get('is_deneyimi') or {}
    sektor_dagilimi = master_json.get('sektor_dagilimi') or []
    projeler_master = master_json.get('projeler_ve_yayinlar') or {}
    adli_sicil = master_json.get('adli_sicil') or {}

    ad = basvuran.get('ad')
    soyad = basvuran.get('soyad')
    isim = " ".join(part for part in [ad, soyad] if part)
    if not isim and basvuru:
        isim = f"{basvuru.get('basvuruYapanAd', '')} {basvuru.get('basvuruYapanSoyad', '')}".strip()
    isim = isim.strip() if isinstance(isim, str) else None

    tc = basvuran.get('tc_kimlik_no') or (basvuru.get('basvuruYapanVatandasTC') if basvuru else None)

    toplam_gun = is_deneyimi.get('toplam_sure_gun') or 0
    toplam_yil = is_deneyimi.get('toplam_sure_yil')
    if toplam_yil is None and toplam_gun:
        toplam_yil = round(toplam_gun / 365, 2)
    toplam_yil = toplam_yil or 0
    toplam_ay = 0
    if toplam_gun:
        toplam_ay = int(round((toplam_gun % 365) / 30))

    sektor_tecrubeleri = _extract_sector_experience(sektor_dagilimi)

    projeler_list = projeler_master.get('liste', []) if isinstance(projeler_master, dict) else []
    proje_sayisi = projeler_master.get('toplam_sayi') if isinstance(projeler_master, dict) else None
    if proje_sayisi is None:
        proje_sayisi = len(projeler_list)

    basvurulan_sektor_listesi = basvuru_info.get('basvurulan_sektor_listesi')
    if basvurulan_sektor_listesi is None:
        sektor_flags = master_json.get('basvurulan_sektorler', {})
        if isinstance(sektor_flags, dict):
            basvurulan_sektor_listesi = [
                sektor.capitalize()
                for sektor, value in sektor_flags.items()
                if value
            ]
        else:
            basvurulan_sektor_listesi = []

    return {
        'ad_soyad': isim or None,
        'tc_kimlik_no': tc,
        'dogum_tarihi': basvuran.get('dogum_tarihi'),
        'dogum_yeri': basvuran.get('dogum_yeri'),
        'mezun_universite': egitim.get('universite'),
        'mezun_bolum': egitim.get('bolum'),
        'mezuniyet_yili': egitim.get('mezuniyet_yili'),
        'egitim_seviyesi': egitim.get('en_yuksek_egitim'),
        'toplam_is_deneyimi_yil': toplam_yil,
        'toplam_is_deneyimi_ay': toplam_ay,
        'tecrube_enerji': sektor_tecrubeleri['enerji'],
        'tecrube_metal': sektor_tecrubeleri['metal'],
        'tecrube_kimya': sektor_tecrubeleri['kimya'],
        'tecrube_mineral': sektor_tecrubeleri['mineral'],
        'tecrube_atik': sektor_tecrubeleri['atik'],
        'tecrube_diger': sektor_tecrubeleri['diger'],
        'adli_sicil_varmi': _normalize_adli_sicil(adli_sicil),
        'yeşil_donusum_tecrubesi': None,
        'cevre_mevzuati_bilgisi': None,
        'enerji_verimliligi_tecrubesi': None,
        'proje_yayin_sayisi': proje_sayisi,
        'diplomalar': [],
        'basvurulan_sektorler': basvurulan_sektor_listesi or [],
        '_sektor_tecrubeleri': sektor_tecrubeleri,
        '_adli_sicil_raw': adli_sicil,
        '_projeler_listesi': projeler_list,
    }


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
    query = "SELECT * FROM analiz_sonuclari WHERE takip_no = ?"
    analiz_row = db.fetchone(query, (takip_no,))

    analiz_master = None
    if analiz_row and analiz_row.get('master_json'):
        try:
            master_json = json.loads(analiz_row['master_json'])
        except (json.JSONDecodeError, TypeError):
            master_json = None

        legacy = master_json_to_legacy(master_json, basvuru) if master_json else None

        analiz_master = {
            'takip_no': analiz_row.get('takip_no'),
            'durum': analiz_row.get('durum'),
            'analiz_tarihi': analiz_row.get('analiz_tarihi'),
            'tablolar': master_json.get('tablolar', {}) if isinstance(master_json, dict) else {},
            'sonuc': legacy,
            'master_json': master_json,
        }

    return {
        'takip_no': takip_no,
        'basvuru': dict(basvuru),
        'belgeler': belgeler,
        'analiz': analiz_master
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
    query = "SELECT * FROM analiz_sonuclari WHERE takip_no = ?"
    analiz = db.fetchone(query, (takip_no,))

    if not analiz or not analiz.get('master_json'):
        raise HTTPException(status_code=404, detail="Analiz sonucu bulunamadı")

    try:
        master_json = json.loads(analiz['master_json'])
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Analiz sonucu okunamadı")

    legacy = master_json_to_legacy(master_json, basvuru)

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

    # Başvurulan sektörler (Master JSON'dan)
    basvurulan_sektorler = legacy.get('basvurulan_sektorler', []) if legacy else []

    # Projeler (Master JSON'dan)
    projeler_list = legacy.get('_projeler_listesi', []) if legacy else []
    projeler = []
    for proje in projeler_list:
        if not isinstance(proje, dict):
            continue
        yil = None
        tarih = proje.get('tarih')
        if isinstance(tarih, str) and len(tarih) >= 4:
            yil = tarih[:4]
        projeler.append({
            "tur": proje.get('tip'),
            "baslik": proje.get('baslik'),
            "yil": yil
        })

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
    sektor_tecrubeleri = {
        "enerji": legacy.get('tecrube_enerji', 0) if legacy else 0,
        "metal": legacy.get('tecrube_metal', 0) if legacy else 0,
        "kimya": legacy.get('tecrube_kimya', 0) if legacy else 0,
        "mineral": legacy.get('tecrube_mineral', 0) if legacy else 0,
        "atik": legacy.get('tecrube_atik', 0) if legacy else 0,
        "diger": legacy.get('tecrube_diger', 0) if legacy else 0,
    }

    adli_sicil_raw = legacy.get('_adli_sicil_raw', {}) if legacy else {}
    egitim = master_json.get('egitim_durumu', {}) if isinstance(master_json, dict) else {}

    return {
        "basvuruId": basvuru_id,
        "basvuru_bilgileri": {
            "ad_soyad": legacy.get('ad_soyad') if legacy else f"{basvuru.get('basvuruYapanAd', '')} {basvuru.get('basvuruYapanSoyad', '')}".strip(),
            "tc": legacy.get('tc_kimlik_no') if legacy else basvuru.get('basvuruYapanVatandasTC'),
            "basvuru_turu": basvuru_turu
        },
        "sektor_bilgileri": {
            "basvurulan_sektorler": basvurulan_sektorler,
            "tecrubeler": sektor_tecrubeleri
        },
        "dokuman_durumu": {**dokuman_durumu, **(master_json.get('sektor_belge_durumu', {}) or {})},
        "adli_sicil": {
            "var_mi": legacy.get('adli_sicil_varmi') if legacy else False,
            "kod": adli_sicil_raw.get('belge_no') if isinstance(adli_sicil_raw, dict) else None
        },
        "mezuniyet": {
            "universite": egitim.get('universite'),
            "bolum": egitim.get('bolum'),
            "yil": egitim.get('mezuniyet_yili')
        },
        "diplomalar": legacy.get('diplomalar', []) if legacy else [],
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
