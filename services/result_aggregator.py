"""
Sonuç birleştirme servisi.
Chunk sonuçlarını ve farklı belge analizlerini birleştirir.
"""

import logging
from typing import Dict, List, Any, Optional

from models import AnalizSonuc

logger = logging.getLogger(__name__)


class ResultAggregator:
    """Sonuç birleştirme servisi"""

    @staticmethod
    def aggregate_document_results(
        basvuru_id: int,
        document_results: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Farklı belge analizlerini birleştir ve kaydet.

        Args:
            basvuru_id: Başvuru ID
            document_results: {
                'cv': {...},
                'sgk': {...},
                'diploma': {...},
                'adli_sicil': {...},
                'proje': {...}
            }

        Returns:
            bool: Başarılı ise True
        """
        try:
            # CV sonuçları
            if 'cv' in document_results:
                cv_data = document_results['cv']
                AnalizSonuc.update_from_cv(basvuru_id, cv_data)

            # SGK sonuçları
            if 'sgk' in document_results:
                sgk_data = document_results['sgk']
                AnalizSonuc.update_from_sgk(basvuru_id, sgk_data)

            # Diploma sonuçları
            if 'diploma' in document_results:
                diploma_data = document_results['diploma']
                AnalizSonuc.update_from_diploma(basvuru_id, diploma_data)

            # Adli sicil sonuçları
            if 'adli_sicil' in document_results:
                sicil_data = document_results['adli_sicil']
                AnalizSonuc.update_from_adli_sicil(basvuru_id, sicil_data)

            # Proje sonuçları
            if 'proje' in document_results:
                proje_data = document_results['proje']
                proje_sayisi = len(proje_data.get('projeler', []))
                AnalizSonuc.update_from_proje(basvuru_id, proje_sayisi)

            logger.info(f"Başvuru {basvuru_id} analiz sonuçları birleştirildi")
            return True

        except Exception as e:
            logger.error(f"Sonuç birleştirme hatası: {e}")
            return False

    @staticmethod
    def merge_chunk_results(chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Chunk sonuçlarını birleştir.

        Args:
            chunk_results: Chunk analiz sonuçları listesi

        Returns:
            Dict: Birleştirilmiş sonuç
        """
        if not chunk_results:
            return {}

        # İlk chunk'ı base al
        merged = chunk_results[0].copy()

        # Diğer chunk'ları merge et
        for result in chunk_results[1:]:
            merged = ResultAggregator._deep_merge(merged, result)

        return merged

    @staticmethod
    def _deep_merge(dict1: Dict, dict2: Dict) -> Dict:
        """
        İki dictionary'yi deep merge et.

        Args:
            dict1: İlk dictionary
            dict2: İkinci dictionary

        Returns:
            Dict: Merge edilmiş dictionary
        """
        merged = dict1.copy()

        for key, value in dict2.items():
            if key not in merged:
                merged[key] = value
                continue

            val1 = merged[key]
            val2 = value

            # Sayısal değerler - maksimum al (chunk'larda aynı bilgi tekrar edebilir)
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                merged[key] = max(val1, val2)

            # String değerler - daha uzun olanı al
            elif isinstance(val1, str) and isinstance(val2, str):
                merged[key] = val1 if len(val1) >= len(val2) else val2

            # Boolean değerler - OR
            elif isinstance(val1, bool) and isinstance(val2, bool):
                merged[key] = val1 or val2

            # List değerler - birleştir ve unique yap
            elif isinstance(val1, list) and isinstance(val2, list):
                merged[key] = list(set(val1 + val2))

            # Dict değerler - recursive merge
            elif isinstance(val1, dict) and isinstance(val2, dict):
                merged[key] = ResultAggregator._deep_merge(val1, val2)

        return merged

    @staticmethod
    def calculate_completion_score(basvuru_id: int) -> float:
        """
        Başvuru tamamlanma skorunu hesapla.

        Args:
            basvuru_id: Başvuru ID

        Returns:
            float: Tamamlanma skoru (0.0 - 1.0)
        """
        from models import Basvuru
        from services.validation_service import ValidationService

        basvuru = Basvuru.get_by_id(basvuru_id, 'basvuruId')
        if not basvuru:
            return 0.0

        score = 0.0
        max_score = 0.0

        # Belge kontrolü (50 puan)
        max_score += 50
        doc_check = ValidationService.check_required_documents(
            basvuru_id,
            basvuru['hizmetId']
        )
        if doc_check['complete']:
            score += 50
        else:
            # Kısmi puan
            stats = doc_check['stats']
            if stats['total_required'] > 0:
                score += 50 * (
                    (stats['total_required'] - stats['missing_count']) /
                    stats['total_required']
                )

        # Analiz sonucu kontrolü (30 puan)
        max_score += 30
        analiz = AnalizSonuc.get_by_basvuru_id(basvuru_id)
        if analiz:
            score += 30

            # Ek puan: veri kaynakları
            kaynak_fields = [
                'kaynak_cv', 'kaynak_sgk', 'kaynak_diploma',
                'kaynak_adli_sicil', 'kaynak_proje_dosyasi'
            ]
            kaynak_count = sum(1 for f in kaynak_fields if analiz.get(f, 0) == 1)
            max_score += 20
            score += 20 * (kaynak_count / len(kaynak_fields))

        # Normalize (0.0 - 1.0)
        return score / max_score if max_score > 0 else 0.0
