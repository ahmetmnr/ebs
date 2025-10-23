"""
Belge ve başvuru validasyon servisi.
Zorunlu belge kontrolü ve validasyon yapar.
"""

import logging
from typing import Dict, List, Optional, Any

from models import Basvuru, Belge, AnalizSonuc
from models.database import db

logger = logging.getLogger(__name__)


class ValidationService:
    """Validasyon servisi"""

    @staticmethod
    def check_required_documents(basvuru_id: int, hizmet_id: str) -> Dict[str, Any]:
        """
        Zorunlu belgeleri kontrol et.

        Args:
            basvuru_id: Başvuru ID
            hizmet_id: Hizmet ID

        Returns:
            Dict: {
                'complete': bool,
                'missing': List[str],
                'optional_present': List[str],
                'stats': Dict
            }
        """
        # Zorunlu belgeleri al
        query = """
            SELECT belgeTipi, zorunlu, aciklama
            FROM zorunlu_belgeler
            WHERE hizmetId = ?
            ORDER BY zorunlu DESC, belgeTipi
        """
        zorunlu_belgeler = db.fetchall(query, (hizmet_id,))

        # Mevcut belgeleri al
        belgeler = Belge.get_by_basvuru_id(basvuru_id)
        mevcut_tipler = set()

        for belge in belgeler:
            tip = belge.get('belgeTipi') or belge.get('belgeTipi_tahmini')
            if tip:
                mevcut_tipler.add(tip)

        # Zorunlu ve opsiyonel ayır
        zorunlu_tipler = set()
        opsiyonel_tipler = set()

        for belge_req in zorunlu_belgeler:
            tip = belge_req['belgeTipi']
            if belge_req['zorunlu'] == 1:
                zorunlu_tipler.add(tip)
            else:
                opsiyonel_tipler.add(tip)

        # Eksik belgeleri bul
        eksik = list(zorunlu_tipler - mevcut_tipler)

        # Mevcut opsiyonel belgeler
        opsiyonel_mevcut = list(opsiyonel_tipler & mevcut_tipler)

        # Tam mı?
        complete = len(eksik) == 0

        result = {
            'complete': complete,
            'missing': eksik,
            'optional_present': opsiyonel_mevcut,
            'stats': {
                'total_required': len(zorunlu_tipler),
                'total_present': len(mevcut_tipler),
                'missing_count': len(eksik),
                'optional_count': len(opsiyonel_mevcut),
            }
        }

        logger.info(
            f"Başvuru {basvuru_id}: "
            f"{len(mevcut_tipler)}/{len(zorunlu_tipler)} zorunlu belge mevcut"
        )

        return result

    @staticmethod
    def validate_basvuru_data(basvuru: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Başvuru verisini doğrula.

        Args:
            basvuru: Başvuru dictionary

        Returns:
            tuple: (geçerli mi?, hata listesi)
        """
        errors = []

        # TC kimlik kontrolü
        tc = basvuru.get('basvuruYapanVatandasTC', '')
        if not tc or len(tc) != 11:
            errors.append(f"Geçersiz TC kimlik: {tc}")

        # Tarih kontrolü
        tarih = basvuru.get('basvuruTarihi')
        if not tarih:
            errors.append("Başvuru tarihi eksik")

        # Hizmet ID kontrolü
        hizmet_id = basvuru.get('hizmetId', '')
        valid_ids = ['10307', '10308', '10309', '10310', '10311', '10312']
        if hizmet_id not in valid_ids:
            errors.append(f"Geçersiz hizmet ID: {hizmet_id}")

        # Ad soyad kontrolü
        ad = basvuru.get('basvuruYapanAd', '').strip()
        soyad = basvuru.get('basvuruYapanSoyad', '').strip()
        if not ad or not soyad:
            errors.append("Ad veya soyad eksik")

        return len(errors) == 0, errors

    @staticmethod
    def validate_analiz_sonuc(sonuc: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Analiz sonucunu doğrula.

        Args:
            sonuc: Analiz sonucu dictionary

        Returns:
            tuple: (geçerli mi?, hata listesi)
        """
        errors = []

        # Mezuniyet yılı kontrolü
        mezuniyet = sonuc.get('mezuniyet_yili')
        if mezuniyet and (mezuniyet < 1950 or mezuniyet > 2030):
            errors.append(f"Geçersiz mezuniyet yılı: {mezuniyet}")

        # İş deneyimi kontrolü
        is_deneyimi_yil = sonuc.get('toplam_is_deneyimi_yil')
        if is_deneyimi_yil and (is_deneyimi_yil < 0 or is_deneyimi_yil > 50):
            errors.append(f"Geçersiz iş deneyimi: {is_deneyimi_yil} yıl")

        # Sektör tecrübeleri kontrolü
        for sektor in ['enerji', 'metal', 'mineral', 'kimya', 'atik', 'diger']:
            tecrube = sonuc.get(f'tecrube_{sektor}')
            if tecrube and (tecrube < 0 or tecrube > 50):
                errors.append(f"Geçersiz {sektor} tecrübesi: {tecrube} yıl")

        return len(errors) == 0, errors

    @staticmethod
    def get_validation_report(basvuru_id: int) -> Dict[str, Any]:
        """
        Başvuru için tam validasyon raporu.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            Dict: Validasyon raporu
        """
        # Başvuru bilgisi
        basvuru = Basvuru.get_by_id(basvuru_id, 'basvuruId')
        if not basvuru:
            return {'error': 'Başvuru bulunamadı'}

        # Başvuru validasyonu
        basvuru_valid, basvuru_errors = ValidationService.validate_basvuru_data(basvuru)

        # Belge kontrolü
        doc_check = ValidationService.check_required_documents(
            basvuru_id,
            basvuru['hizmetId']
        )

        # Analiz sonucu varsa kontrol et
        analiz = AnalizSonuc.get_by_basvuru_id(basvuru_id)
        analiz_valid = True
        analiz_errors = []

        if analiz:
            analiz_valid, analiz_errors = ValidationService.validate_analiz_sonuc(analiz)

        # Genel durum
        overall_valid = (
            basvuru_valid and
            doc_check['complete'] and
            analiz_valid
        )

        return {
            'basvuru_id': basvuru_id,
            'takip_no': basvuru.get('takipNo'),
            'overall_valid': overall_valid,
            'basvuru': {
                'valid': basvuru_valid,
                'errors': basvuru_errors,
            },
            'documents': {
                'complete': doc_check['complete'],
                'missing': doc_check['missing'],
                'stats': doc_check['stats'],
            },
            'analiz': {
                'valid': analiz_valid,
                'errors': analiz_errors,
                'exists': analiz is not None,
            }
        }
