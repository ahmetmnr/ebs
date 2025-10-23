"""
Belge tipi tahmin servisi.
Dosya adından belge tipini tahmin eder.
"""

import re
import logging
from typing import Optional

from models.database import db

logger = logging.getLogger(__name__)


class BelgeTipiPredictor:
    """Belge tipi tahmin servisi"""

    @staticmethod
    def predict(belge_adi: str) -> Optional[str]:
        """
        Belge adından tipi tahmin et.

        Args:
            belge_adi: Belge dosya adı

        Returns:
            str: Tahmin edilen belge tipi, bulunamazsa None
        """
        if not belge_adi:
            return None

        # Kuralları al (öncelik sırasına göre)
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

            try:
                if re.search(pattern, belge_adi, re.IGNORECASE):
                    logger.debug(f"Belge tipi tahmin edildi: {belge_adi} -> {tip}")
                    return tip
            except re.error as e:
                logger.error(f"Regex hatası ({pattern}): {e}")
                continue

        logger.debug(f"Belge tipi tahmin edilemedi: {belge_adi}")
        return None

    @staticmethod
    def predict_and_update(belge_id: int) -> bool:
        """
        Belge tipini tahmin et ve güncelle.

        Args:
            belge_id: Belge ID

        Returns:
            bool: Başarılı ise True
        """
        from models import Belge

        # Belge bilgisini al
        belge = Belge.get_by_id(belge_id, 'belgeId')
        if not belge:
            return False

        # Zaten tipi varsa atla
        if belge.get('belgeTipi'):
            return True

        # Tahmin et
        belge_adi = belge.get('belgeAdi', '')
        tahmin = BelgeTipiPredictor.predict(belge_adi)

        if tahmin:
            # Güncelle
            Belge.update(belge_id, {'belgeTipi_tahmini': tahmin}, 'belgeId')
            logger.info(f"Belge {belge_id} tipi güncellendi: {tahmin}")
            return True

        return False

    @staticmethod
    def add_rule(
        pattern: str,
        belge_tipi: str,
        oncelik: int = 5,
        aktif: bool = True
    ) -> bool:
        """
        Yeni tahmin kuralı ekle.

        Args:
            pattern: Regex pattern
            belge_tipi: Tahmin edilecek belge tipi
            oncelik: Öncelik (yüksek = önce kontrol)
            aktif: Aktif mi?

        Returns:
            bool: Başarılı ise True
        """
        try:
            # Pattern'i test et
            re.compile(pattern)

            query = """
                INSERT OR REPLACE INTO belge_tipi_kurallar
                (dosya_adi_pattern, tahmin_edilen_tip, oncelik, aktif)
                VALUES (?, ?, ?, ?)
            """

            with db.get_cursor() as cursor:
                cursor.execute(query, (pattern, belge_tipi, oncelik, 1 if aktif else 0))

            logger.info(f"Belge tipi kuralı eklendi: {pattern} -> {belge_tipi}")
            return True

        except re.error as e:
            logger.error(f"Geçersiz regex pattern: {pattern} ({e})")
            return False
        except Exception as e:
            logger.error(f"Kural ekleme hatası: {e}")
            return False

    @staticmethod
    def get_all_rules() -> list:
        """
        Tüm kuralları getir.

        Returns:
            list: Kural listesi
        """
        query = """
            SELECT *
            FROM belge_tipi_kurallar
            ORDER BY oncelik DESC, tahmin_edilen_tip
        """
        return db.fetchall(query)
