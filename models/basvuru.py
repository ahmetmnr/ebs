"""
Başvuru model sınıfı.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from .database import BaseModel, db

logger = logging.getLogger(__name__)


class Basvuru(BaseModel):
    """Başvuru model sınıfı"""

    table_name = "basvurular"

    @classmethod
    def create_from_json(cls, json_data: str, hizmet_id: str) -> Optional[int]:
        """
        JSON'dan başvuru oluştur.

        Args:
            json_data: Ham JSON string
            hizmet_id: Hizmet ID

        Returns:
            int: Başvuru ID, hata durumunda None
        """
        try:
            data = json.loads(json_data)

            basvuru_data = {
                'basvuruId': data.get('basvuruId'),
                'takipNo': data.get('takipNo'),
                'basvuruTarihi': data.get('basvuruTarihi'),
                'hizmetId': hizmet_id,
                'hizmetAdi': data.get('hizmetAdi', ''),
                'basvuruYapanVatandasTC': data.get('basvuruYapanVatandasTC', ''),
                'basvuruYapanAd': data.get('basvuruYapanAd', ''),
                'basvuruYapanSoyad': data.get('basvuruYapanSoyad', ''),
                'basvuruDurum': data.get('basvuruDurum', ''),
                'kararDurum': data.get('kararDurum'),
                'json_ham': json_data,
            }

            return cls.insert(basvuru_data)

        except Exception as e:
            logger.error(f"Başvuru oluşturma hatası: {e}")
            return None

    @classmethod
    def get_by_takip_no(cls, takip_no: str) -> Optional[Dict]:
        """
        Takip numarasına göre başvuru getir.

        Args:
            takip_no: Takip numarası

        Returns:
            Dict or None: Başvuru dictionary
        """
        query = f"SELECT * FROM {cls.table_name} WHERE takipNo = ?"
        return db.fetchone(query, (takip_no,))

    @classmethod
    def get_unprocessed(cls, limit: Optional[int] = None) -> List[Dict]:
        """
        İşlenmemiş başvuruları getir.

        Args:
            limit: Maksimum kayıt sayısı

        Returns:
            List[Dict]: Başvuru listesi
        """
        query = f"""
            SELECT * FROM {cls.table_name}
            WHERE islendiMi = 0
            ORDER BY basvuruTarihi DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        return db.fetchall(query)

    @classmethod
    def mark_as_processing(cls, basvuru_id: int) -> bool:
        """
        Başvuruyu işleniyor olarak işaretle.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            bool: Başarılı ise True
        """
        data = {
            'islenme_baslangic': datetime.now().isoformat()
        }
        return cls.update(basvuru_id, data, 'basvuruId')

    @classmethod
    def mark_as_processed(cls, basvuru_id: int, success: bool = True, error_msg: Optional[str] = None) -> bool:
        """
        Başvuruyu işlendi olarak işaretle.

        Args:
            basvuru_id: Başvuru ID
            success: Başarılı mı?
            error_msg: Hata mesajı (varsa)

        Returns:
            bool: Başarılı ise True
        """
        # Önce başlangıç zamanını al
        basvuru = cls.get_by_id(basvuru_id, 'basvuruId')
        if not basvuru:
            return False

        now = datetime.now().isoformat()
        data = {
            'islendiMi': 1 if success else 0,
            'islenme_bitis': now,
        }

        # Süre hesapla
        if basvuru.get('islenme_baslangic'):
            try:
                start = datetime.fromisoformat(basvuru['islenme_baslangic'])
                end = datetime.fromisoformat(now)
                duration = (end - start).total_seconds()
                data['islenme_suresi_sn'] = duration
            except:
                pass

        if error_msg:
            data['hata_mesaji'] = error_msg

        return cls.update(basvuru_id, data, 'basvuruId')

    @classmethod
    def get_belgeler(cls, basvuru_id: int) -> List[Dict]:
        """
        Başvuruya ait belgeleri getir.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            List[Dict]: Belge listesi
        """
        from .belge import Belge
        return Belge.get_by_basvuru_id(basvuru_id)

    @classmethod
    def get_analiz_sonucu(cls, basvuru_id: int) -> Optional[Dict]:
        """
        Başvuruya ait analiz sonucunu getir.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            Dict or None: Analiz sonucu
        """
        from .analiz_sonuc import AnalizSonuc
        return AnalizSonuc.get_by_basvuru_id(basvuru_id)

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        Başvuru istatistikleri.

        Returns:
            Dict: İstatistikler
        """
        stats = {}

        # Toplam sayılar
        stats['toplam'] = cls.count()

        # İşlenmiş/işlenmemiş
        query = f"SELECT islendiMi, COUNT(*) as count FROM {cls.table_name} GROUP BY islendiMi"
        results = db.fetchall(query)
        stats['islenmis'] = next((r['count'] for r in results if r['islendiMi'] == 1), 0)
        stats['islenmemis'] = next((r['count'] for r in results if r['islendiMi'] == 0), 0)

        # Hizmet türüne göre
        query = f"SELECT hizmetId, COUNT(*) as count FROM {cls.table_name} GROUP BY hizmetId"
        results = db.fetchall(query)
        stats['hizmet_turleri'] = {r['hizmetId']: r['count'] for r in results}

        return stats
