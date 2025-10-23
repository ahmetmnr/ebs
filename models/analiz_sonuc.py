"""
Analiz Sonucu model sınıfı.
"""

from typing import Dict, List, Optional, Any
import json
import logging

from .database import BaseModel, db

logger = logging.getLogger(__name__)


class AnalizSonuc(BaseModel):
    """Analiz Sonucu model sınıfı"""

    table_name = "analiz_sonuclari"

    @classmethod
    def create_or_update(cls, basvuru_id: int, analiz_data: Dict[str, Any]) -> bool:
        """
        Analiz sonucu oluştur veya güncelle.

        Args:
            basvuru_id: Başvuru ID
            analiz_data: Analiz sonucu dictionary

        Returns:
            bool: Başarılı ise True
        """
        try:
            # Mevcut kaydı kontrol et
            existing = cls.get_by_basvuru_id(basvuru_id)

            # Eksik belgeler JSON array'e çevir
            if 'eksik_belgeler' in analiz_data and isinstance(analiz_data['eksik_belgeler'], list):
                analiz_data['eksik_belgeler'] = json.dumps(analiz_data['eksik_belgeler'], ensure_ascii=False)

            if existing:
                # Güncelle
                return cls.update(existing['id'], analiz_data)
            else:
                # Yeni kayıt
                analiz_data['basvuruId'] = basvuru_id
                cls.insert(analiz_data)
                return True

        except Exception as e:
            logger.error(f"Analiz sonucu kaydetme hatası: {e}")
            return False

    @classmethod
    def get_by_basvuru_id(cls, basvuru_id: int) -> Optional[Dict]:
        """
        Başvuruya ait analiz sonucunu getir.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            Dict or None: Analiz sonucu
        """
        query = f"SELECT * FROM {cls.table_name} WHERE basvuruId = ?"
        result = db.fetchone(query, (basvuru_id,))

        # Eksik belgeler JSON'u parse et
        if result and result.get('eksik_belgeler'):
            try:
                result['eksik_belgeler'] = json.loads(result['eksik_belgeler'])
            except:
                result['eksik_belgeler'] = []

        return result

    @classmethod
    def update_from_cv(cls, basvuru_id: int, cv_data: Dict[str, Any]) -> bool:
        """
        CV analizinden gelen verileri güncelle.

        Args:
            basvuru_id: Başvuru ID
            cv_data: CV analiz sonucu

        Returns:
            bool: Başarılı ise True
        """
        # 🔍 LOG: CV DATA INPUT
        logger.info(f"{'='*80}")
        logger.info(f"💾 CV SAVE - Başvuru ID: {basvuru_id}")
        logger.info(f"Input keys: {list(cv_data.keys())}")
        logger.info(f"universite: {cv_data.get('universite')}")
        logger.info(f"bolum: {cv_data.get('bolum')}")
        logger.info(f"mezuniyet_yili: {cv_data.get('mezuniyet_yili')}")
        logger.info(f"{'='*80}")

        update_data = {
            'mezun_universite': cv_data.get('universite'),  # LLM 'universite' döndürür
            'mezun_bolum': cv_data.get('bolum'),  # LLM 'bolum' döndürür
            'mezuniyet_yili': cv_data.get('mezuniyet_yili'),
            'egitim_seviyesi': cv_data.get('egitim_seviyesi'),
            'tecrube_enerji': cv_data.get('tecrube_enerji'),
            'tecrube_metal': cv_data.get('tecrube_metal'),
            'tecrube_mineral': cv_data.get('tecrube_mineral'),
            'tecrube_kimya': cv_data.get('tecrube_kimya'),
            'tecrube_atik': cv_data.get('tecrube_atik'),
            'tecrube_diger': cv_data.get('tecrube_diger'),
            'kaynak_cv': 1,
        }

        return cls.create_or_update(basvuru_id, update_data)

    @classmethod
    def update_from_sgk(cls, basvuru_id: int, sgk_data: Dict[str, Any]) -> bool:
        """
        SGK analizinden gelen verileri güncelle.

        Args:
            basvuru_id: Başvuru ID
            sgk_data: SGK analiz sonucu

        Returns:
            bool: Başarılı ise True
        """
        update_data = {
            'toplam_is_deneyimi_yil': sgk_data.get('toplam_is_deneyimi_yil'),
            'toplam_is_deneyimi_ay': sgk_data.get('toplam_is_deneyimi_ay'),
            'kaynak_sgk': 1,
        }

        return cls.create_or_update(basvuru_id, update_data)

    @classmethod
    def update_from_diploma(cls, basvuru_id: int, diploma_data: Dict[str, Any]) -> bool:
        """
        Diploma analizinden gelen verileri güncelle.

        Args:
            basvuru_id: Başvuru ID
            diploma_data: Diploma analiz sonucu (yeni format: {"diplomalar": [...]})

        Returns:
            bool: Başarılı ise True
        """
        import json

        # 🔍 LOG: DIPLOMA DATA INPUT
        logger.info(f"{'='*80}")
        logger.info(f"💾 DIPLOMA SAVE - Başvuru ID: {basvuru_id}")
        logger.info(f"Input data keys: {list(diploma_data.keys())}")
        logger.info(f"Input data: {json.dumps(diploma_data, ensure_ascii=False, indent=2)[:500]}...")
        logger.info(f"{'='*80}")

        # Yeni format: {"diplomalar": [...]}
        diplomalar = diploma_data.get('diplomalar', [])

        # Backward compatibility: Eğer eski format gelirse
        if not diplomalar and diploma_data.get('universite'):
            diplomalar = [diploma_data]

        # En güncel/en yüksek diplomayı summary için bul (backward compatibility)
        summary_diploma = None
        if diplomalar:
            # En son mezuniyet tarihli diplomayı al
            sorted_diplomas = sorted(
                diplomalar,
                key=lambda d: d.get('mezuniyet_tarihi', ''),
                reverse=True
            )
            summary_diploma = sorted_diplomas[0]

        update_data = {
            'kaynak_diploma': 1,
            'diploma_bilgileri_json': json.dumps(diplomalar, ensure_ascii=False) if diplomalar else None,
        }

        # Summary alanları (en güncel diploma bilgisi - backward compatibility için)
        if summary_diploma:
            update_data['mezun_universite'] = summary_diploma.get('universite')
            update_data['mezun_bolum'] = summary_diploma.get('program_bolum') or summary_diploma.get('bolum')

            # Mezuniyet yılını çıkar (DD/MM/YYYY -> YYYY)
            mezuniyet_tarihi = summary_diploma.get('mezuniyet_tarihi', '')
            if mezuniyet_tarihi and '/' in mezuniyet_tarihi:
                # DD/MM/YYYY formatından yılı al
                update_data['mezuniyet_yili'] = int(mezuniyet_tarihi.split('/')[-1])
            elif summary_diploma.get('mezuniyet_yili'):
                # Eski format için
                update_data['mezuniyet_yili'] = summary_diploma.get('mezuniyet_yili')

            # Eğitim seviyesini program_bolum'dan çıkar
            program_bolum = summary_diploma.get('program_bolum', '')
            if '(YL)' in program_bolum or 'YÜKSEK LİSANS' in program_bolum.upper():
                update_data['egitim_seviyesi'] = 'Yüksek Lisans'
            elif '(DR)' in program_bolum or 'DOKTORA' in program_bolum.upper():
                update_data['egitim_seviyesi'] = 'Doktora'
            else:
                update_data['egitim_seviyesi'] = summary_diploma.get('egitim_seviyesi', 'Lisans')

        # 🔍 LOG: FINAL UPDATE DATA
        logger.info(f"{'='*80}")
        logger.info(f"💾 DIPLOMA FINAL UPDATE DATA - Başvuru ID: {basvuru_id}")
        logger.info(f"Diploma sayısı: {len(diplomalar)}")
        logger.info(f"mezun_universite: {update_data.get('mezun_universite')}")
        logger.info(f"mezun_bolum: {update_data.get('mezun_bolum')}")
        logger.info(f"mezuniyet_yili: {update_data.get('mezuniyet_yili')}")
        logger.info(f"egitim_seviyesi: {update_data.get('egitim_seviyesi')}")
        logger.info(f"diploma_bilgileri_json length: {len(update_data.get('diploma_bilgileri_json', '')) if update_data.get('diploma_bilgileri_json') else 0} chars")
        logger.info(f"{'='*80}")

        return cls.create_or_update(basvuru_id, update_data)

    @classmethod
    def update_from_adli_sicil(cls, basvuru_id: int, sicil_data: Dict[str, Any]) -> bool:
        """
        Adli sicil analizinden gelen verileri güncelle.

        Args:
            basvuru_id: Başvuru ID
            sicil_data: Adli sicil analiz sonucu

        Returns:
            bool: Başarılı ise True
        """
        update_data = {
            'adli_sicil_varmi': 1 if sicil_data.get('var_mi') else 0,  # LLM 'var_mi' döndürür
            'adli_sicil_kodu': sicil_data.get('kod'),  # LLM 'kod' döndürür
            'adli_sicil_aciklama': sicil_data.get('aciklama'),
            'kaynak_adli_sicil': 1,
        }

        return cls.create_or_update(basvuru_id, update_data)

    @classmethod
    def update_from_proje(cls, basvuru_id: int, proje_count: int) -> bool:
        """
        Proje/yayın sayısını güncelle.

        Args:
            basvuru_id: Başvuru ID
            proje_count: Proje/yayın sayısı

        Returns:
            bool: Başarılı ise True
        """
        update_data = {
            'proje_yayin_sayisi': proje_count,
            'kaynak_proje_dosyasi': 1,
        }

        return cls.create_or_update(basvuru_id, update_data)

    @classmethod
    def update_sektor_basvuru(cls, basvuru_id: int, sektor: str, value: bool = True) -> bool:
        """
        Sektör başvurusunu güncelle.

        Args:
            basvuru_id: Başvuru ID
            sektor: Sektör adı (enerji, metal, mineral, kimya, atik, diger)
            value: Değer (True/False)

        Returns:
            bool: Başarılı ise True
        """
        column_map = {
            'enerji': 'sektor_enerji',
            'metal': 'sektor_metal',
            'mineral': 'sektor_mineral',
            'kimya': 'sektor_kimya',
            'atik': 'sektor_atik',
            'diger': 'sektor_diger',
        }

        column = column_map.get(sektor.lower())
        if not column:
            logger.error(f"Geçersiz sektör: {sektor}")
            return False

        update_data = {column: 1 if value else 0}
        return cls.create_or_update(basvuru_id, update_data)

    @classmethod
    def check_zorunlu_belgeler(cls, basvuru_id: int, hizmet_id: str) -> Dict[str, Any]:
        """
        Zorunlu belgelerin kontrolü.

        Args:
            basvuru_id: Başvuru ID
            hizmet_id: Hizmet ID

        Returns:
            Dict: {'tam': bool, 'eksik': List[str]}
        """
        from .belge import Belge

        # Zorunlu belgeleri al
        query = """
            SELECT belgeTipi
            FROM zorunlu_belgeler
            WHERE hizmetId = ? AND zorunlu = 1
        """
        zorunlu_belgeler = db.fetchall(query, (hizmet_id,))
        zorunlu_tipler = set([b['belgeTipi'] for b in zorunlu_belgeler])

        # Mevcut belgeleri al
        belgeler = Belge.get_by_basvuru_id(basvuru_id)
        mevcut_tipler = set([
            b.get('belgeTipi') or b.get('belgeTipi_tahmini')
            for b in belgeler
            if b.get('belgeTipi') or b.get('belgeTipi_tahmini')
        ])

        # Eksik belgeleri bul
        eksik = list(zorunlu_tipler - mevcut_tipler)

        # Güncelle
        update_data = {
            'zorunlu_belgeler_tam': 1 if len(eksik) == 0 else 0,
            'eksik_belgeler': json.dumps(eksik, ensure_ascii=False),
        }
        cls.create_or_update(basvuru_id, update_data)

        return {
            'tam': len(eksik) == 0,
            'eksik': eksik
        }

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        Analiz sonuçları istatistikleri.

        Returns:
            Dict: İstatistikler
        """
        stats = {}

        # Toplam
        stats['toplam'] = cls.count()

        # Zorunlu belgeler tam olan sayısı
        query = f"SELECT COUNT(*) as count FROM {cls.table_name} WHERE zorunlu_belgeler_tam = 1"
        result = db.fetchone(query)
        stats['zorunlu_belgeler_tam'] = result['count'] if result else 0

        # Sektör dağılımı
        sektorler = ['enerji', 'metal', 'mineral', 'kimya', 'atik', 'diger']
        stats['sektor_dagilimi'] = {}
        for sektor in sektorler:
            query = f"SELECT COUNT(*) as count FROM {cls.table_name} WHERE sektor_{sektor} = 1"
            result = db.fetchone(query)
            stats['sektor_dagilimi'][sektor] = result['count'] if result else 0

        # Ortalama iş deneyimi
        query = f"SELECT AVG(toplam_is_deneyimi_yil) as avg_exp FROM {cls.table_name}"
        result = db.fetchone(query)
        stats['ortalama_is_deneyimi_yil'] = round(result['avg_exp'], 2) if result['avg_exp'] else 0

        return stats
