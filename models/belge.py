"""
Belge model sınıfı.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import base64
import logging

from .database import BaseModel, db

logger = logging.getLogger(__name__)


class Belge(BaseModel):
    """Belge model sınıfı"""

    table_name = "belgeler"

    @classmethod
    def get_by_id(cls, record_id: int) -> Optional[Dict]:
        """
        Belge ID'ye göre kayıt getir.
        Override: belgeler tablosunda primary key 'belgeId'
        """
        return super().get_by_id(record_id, id_column='belgeId')

    @classmethod
    def create_from_dict(cls, basvuru_id: int, belge_data: Dict[str, Any]) -> Optional[int]:
        """
        Dictionary'den belge oluştur.

        Args:
            basvuru_id: Başvuru ID
            belge_data: Belge dictionary (API'den gelen format)

        Returns:
            int: Belge ID, hata durumunda None
        """
        try:
            belge_adi = belge_data.get('belgeAdi', '')
            dosya_byte = belge_data.get('dosyaByte', '')

            # Uzantı
            uzanti = Path(belge_adi).suffix.lower() if belge_adi else None

            # Boyut tahmini (base64 -> bytes)
            belge_boyutu = len(dosya_byte) * 3 // 4 if dosya_byte else 0

            data = {
                'basvuruId': basvuru_id,
                'belgeAdi': belge_adi,
                'belgeTipi': belge_data.get('belgeTipi'),  # null olabilir
                'belgeIcerik': dosya_byte,
                'belge_boyutu_bytes': belge_boyutu,
                'belge_uzantisi': uzanti,
            }

            return cls.insert(data)

        except Exception as e:
            logger.error(f"Belge oluşturma hatası: {e}")
            return None

    @classmethod
    def get_by_basvuru_id(cls, basvuru_id: int) -> List[Dict]:
        """
        Başvuruya ait belgeleri getir.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            List[Dict]: Belge listesi
        """
        query = f"SELECT * FROM {cls.table_name} WHERE basvuruId = ?"
        return db.fetchall(query, (basvuru_id,))

    @classmethod
    def get_unanalyzed(cls, limit: Optional[int] = None) -> List[Dict]:
        """
        Analiz edilmemiş belgeleri getir.

        Args:
            limit: Maksimum kayıt sayısı

        Returns:
            List[Dict]: Belge listesi
        """
        query = f"""
            SELECT * FROM {cls.table_name}
            WHERE analiz_edildi = 0
            ORDER BY created_at
        """

        if limit:
            query += f" LIMIT {limit}"

        return db.fetchall(query)

    @classmethod
    def mark_as_analyzing(cls, belge_id: int) -> bool:
        """
        Belgeyi analiz ediliyor olarak işaretle.

        Args:
            belge_id: Belge ID

        Returns:
            bool: Başarılı ise True
        """
        data = {
            'analiz_baslangic': datetime.now().isoformat()
        }
        return cls.update(belge_id, data, 'belgeId')

    @classmethod
    def mark_as_analyzed(cls, belge_id: int, success: bool = True, error_msg: Optional[str] = None) -> bool:
        """
        Belgeyi analiz edildi olarak işaretle.

        Args:
            belge_id: Belge ID
            success: Başarılı mı?
            error_msg: Hata mesajı (varsa)

        Returns:
            bool: Başarılı ise True
        """
        # Önce başlangıç zamanını al
        belge = cls.get_by_id(belge_id)
        if not belge:
            return False

        now = datetime.now().isoformat()
        data = {
            'analiz_edildi': 1 if success else 0,
            'analiz_bitis': now,
        }

        # Süre hesapla
        if belge.get('analiz_baslangic'):
            try:
                start = datetime.fromisoformat(belge['analiz_baslangic'])
                end = datetime.fromisoformat(now)
                duration = (end - start).total_seconds()
                data['analiz_suresi_sn'] = duration
            except:
                pass

        if error_msg:
            data['analiz_hata'] = error_msg

        return cls.update(belge_id, data, 'belgeId')

    @classmethod
    def decode_icerik(cls, belge: Dict) -> Optional[bytes]:
        """
        Base64 içeriği decode et.

        Args:
            belge: Belge dictionary

        Returns:
            bytes or None: Decode edilmiş içerik
        """
        try:
            icerik = belge.get('belgeIcerik', '')
            if not icerik:
                return None

            return base64.b64decode(icerik)

        except Exception as e:
            logger.error(f"Base64 decode hatası: {e}")
            return None

    @classmethod
    def predict_belge_tipi(cls, belge_id: int) -> Optional[str]:
        """
        Belge adından belge tipini tahmin et.

        Args:
            belge_id: Belge ID

        Returns:
            str or None: Tahmin edilen belge tipi
        """
        belge = cls.get_by_id(belge_id)
        if not belge:
            return None

        belge_adi = belge.get('belgeAdi', '')
        if not belge_adi:
            return None

        # Kuralları al
        import re
        query = """
            SELECT dosya_adi_pattern, tahmin_edilen_tip
            FROM belge_tipi_kurallar
            WHERE aktif = 1
            ORDER BY oncelik DESC
        """
        kurallar = db.fetchall(query)

        for kural in kurallar:
            pattern = kural['dosya_adi_pattern']
            tip = kural['tahmin_edilen_tip']

            if re.search(pattern, belge_adi, re.IGNORECASE):
                # Tahmin güncelle
                cls.update(belge_id, {'belgeTipi_tahmini': tip}, 'belgeId')
                return tip

        return None

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        Belge istatistikleri.

        Returns:
            Dict: İstatistikler
        """
        stats = {}

        # Toplam
        stats['toplam'] = cls.count()

        # Analiz edilmiş/edilmemiş
        query = f"SELECT analiz_edildi, COUNT(*) as count FROM {cls.table_name} GROUP BY analiz_edildi"
        results = db.fetchall(query)
        stats['analiz_edilmis'] = next((r['count'] for r in results if r['analiz_edildi'] == 1), 0)
        stats['analiz_edilmemis'] = next((r['count'] for r in results if r['analiz_edildi'] == 0), 0)

        # Belge tiplerine göre
        query = f"""
            SELECT
                COALESCE(belgeTipi, belgeTipi_tahmini, 'Bilinmeyen') as tip,
                COUNT(*) as count
            FROM {cls.table_name}
            GROUP BY tip
        """
        results = db.fetchall(query)
        stats['tipler'] = {r['tip']: r['count'] for r in results}

        # Ortalama boyut
        query = f"SELECT AVG(belge_boyutu_bytes) as avg_size FROM {cls.table_name}"
        result = db.fetchone(query)
        stats['ortalama_boyut_mb'] = (result['avg_size'] / (1024 * 1024)) if result['avg_size'] else 0

        return stats
