"""
JSON parse servisi.
API'den gelen JSON'ları parse eder ve veritabanına kaydeder.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from models import Basvuru, Belge
from config.settings import HIZMET_IDS

logger = logging.getLogger(__name__)


class JSONParser:
    """JSON parse ve veritabanı kayıt servisi"""

    @staticmethod
    def parse_basvuru_json(json_data: str, hizmet_id: str) -> Optional[int]:
        """
        Başvuru JSON'unu parse et ve veritabanına kaydet.

        Args:
            json_data: Ham JSON string
            hizmet_id: Hizmet ID

        Returns:
            int: Başvuru ID, başarısızsa None
        """
        try:
            data = json.loads(json_data)

            # Hizmet ID kontrolü
            if hizmet_id not in HIZMET_IDS:
                logger.warning(f"Geçersiz hizmet ID: {hizmet_id}")
                return None

            # Başvuru kaydı oluştur
            basvuru_id = Basvuru.create_from_json(json_data, hizmet_id)
            if not basvuru_id:
                logger.error("Başvuru kaydı oluşturulamadı")
                return None

            logger.info(f"Başvuru kaydedildi: {data.get('takipNo')} (ID: {basvuru_id})")

            # Belgeleri kaydet
            belge_listesi = data.get('basvuruBelgeListesi', [])
            belge_sayisi = JSONParser._parse_belgeler(basvuru_id, belge_listesi)

            logger.info(f"Başvuru {basvuru_id} için {belge_sayisi} belge kaydedildi")

            return basvuru_id

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}")
            return None
        except Exception as e:
            logger.error(f"Başvuru kaydetme hatası: {e}")
            return None

    @staticmethod
    def _parse_belgeler(basvuru_id: int, belge_listesi: List[Dict]) -> int:
        """
        Belgeleri parse et ve kaydet.

        Args:
            basvuru_id: Başvuru ID
            belge_listesi: Belge dictionary listesi

        Returns:
            int: Kaydedilen belge sayısı
        """
        kayit_sayisi = 0

        for belge_data in belge_listesi:
            try:
                belge_id = Belge.create_from_dict(basvuru_id, belge_data)
                if belge_id:
                    kayit_sayisi += 1

                    # Belge tipi tahmini yap
                    from services.belge_tipi_predictor import BelgeTipiPredictor
                    BelgeTipiPredictor.predict_and_update(belge_id)

            except Exception as e:
                logger.error(f"Belge kaydetme hatası: {e}")
                continue

        return kayit_sayisi

    @staticmethod
    def parse_batch(json_list: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Toplu JSON parse işlemi.

        Args:
            json_list: [{"json_data": "...", "hizmet_id": "..."}] formatında liste

        Returns:
            Dict: İstatistikler
        """
        stats = {
            'toplam': len(json_list),
            'basarili': 0,
            'basarisiz': 0,
            'basvuru_ids': [],
        }

        for item in json_list:
            json_data = item.get('json_data')
            hizmet_id = item.get('hizmet_id')

            if not json_data or not hizmet_id:
                stats['basarisiz'] += 1
                continue

            basvuru_id = JSONParser.parse_basvuru_json(json_data, hizmet_id)

            if basvuru_id:
                stats['basarili'] += 1
                stats['basvuru_ids'].append(basvuru_id)
            else:
                stats['basarisiz'] += 1

        return stats

    @staticmethod
    def validate_json_structure(json_data: str) -> tuple[bool, Optional[str]]:
        """
        JSON yapısını doğrula.

        Args:
            json_data: JSON string

        Returns:
            tuple: (geçerli mi?, hata mesajı)
        """
        try:
            data = json.loads(json_data)

            # Zorunlu alanlar
            required_fields = [
                'basvuruId', 'takipNo', 'basvuruTarihi',
                'hizmetAdi', 'basvuruYapanVatandasTC',
                'basvuruYapanAd', 'basvuruYapanSoyad',
                'basvuruDurum'
            ]

            for field in required_fields:
                if field not in data:
                    return False, f"Eksik alan: {field}"

            # TC kimlik kontrolü
            tc = data.get('basvuruYapanVatandasTC', '')
            if not tc or len(tc) != 11:
                return False, f"Geçersiz TC kimlik: {tc}"

            return True, None

        except json.JSONDecodeError as e:
            return False, f"JSON parse hatası: {e}"
        except Exception as e:
            return False, f"Bilinmeyen hata: {e}"
