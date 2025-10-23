"""
Cross-Validation Service
Farklı belgelerden gelen bilgileri karşılaştırır ve doğrular.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CrossValidator:
    """
    Farklı belgelerden gelen bilgileri ground truth ile karşılaştırır.
    """

    def __init__(self, ground_truth: Dict):
        """
        Args:
            ground_truth: Üst yazıdan gelen bilgiler (referans)
        """
        self.ground_truth = ground_truth
        self.validation_errors = []
        self.validation_warnings = []
        self.field_checks = []

    def validate_field(self,
                      field_name: str,
                      value: Any,
                      source: str,
                      severity: str = 'WARNING',
                      ground_truth_key: Optional[str] = None) -> bool:
        """
        Tek bir field'i ground truth ile karşılaştır.

        Args:
            field_name: Field adı (örn: 'tc_kimlik_no')
            value: Kontrol edilecek değer
            source: Değerin geldiği kaynak (örn: 'Diploma')
            severity: 'CRITICAL' veya 'WARNING'
            ground_truth_key: Ground truth'taki key (varsayılan: field_name)

        Returns:
            bool: Validation başarılı mı?
        """
        if ground_truth_key is None:
            ground_truth_key = field_name

        ground_truth_value = self.ground_truth.get(ground_truth_key)

        # Ground truth'ta yok, validation yapamıyoruz
        if ground_truth_value is None:
            logger.debug(f"Ground truth'ta '{ground_truth_key}' yok, validation atlanıyor")
            return True

        # Değer boş/None
        if value is None or value == "":
            logger.debug(f"{source} belgesi '{field_name}' değeri boş")
            return True

        # Değerleri normalize et
        if isinstance(value, str) and isinstance(ground_truth_value, str):
            value_normalized = self._normalize_string(value)
            gt_normalized = self._normalize_string(ground_truth_value)
        else:
            value_normalized = value
            gt_normalized = ground_truth_value

        # Karşılaştır
        if value_normalized != gt_normalized:
            error = {
                'field': field_name,
                'source': source,
                'value': value,
                'expected': ground_truth_value,
                'severity': severity
            }

            if severity == 'CRITICAL':
                self.validation_errors.append(error)
                logger.error(
                    f"🔴 DOĞRULAMA HATASI: {field_name} - "
                    f"{source}: '{value}' ≠ Üst Yazı: '{ground_truth_value}'"
                )
            else:
                self.validation_warnings.append(error)
                logger.warning(
                    f"🟡 Doğrulama uyarısı: {field_name} - "
                    f"{source}: '{value}' ≠ Üst Yazı: '{ground_truth_value}'"
                )

            self.field_checks.append({
                'field': field_name,
                'source': source,
                'match': False,
                'severity': severity
            })

            return False

        # Başarılı
        logger.debug(f"✓ {field_name} doğrulandı: {source} = Üst Yazı")
        self.field_checks.append({
            'field': field_name,
            'source': source,
            'match': True,
            'severity': severity
        })

        return True

    def validate_document_list(self, actual_documents: List[str]) -> Dict:
        """
        Belge listesini kontrol et.

        Args:
            actual_documents: Sistemde yüklü belge dosya adları

        Returns:
            Dict: Kontrol sonucu
        """
        expected_files = set(self.ground_truth.get('belge_listesi', []))
        actual_files = set(actual_documents)

        # Normalize et (küçük harf, boşlukları temizle)
        expected_normalized = {self._normalize_filename(f) for f in expected_files}
        actual_normalized = {self._normalize_filename(f) for f in actual_files}

        # Eksik ve fazla belgeler
        eksik_normalized = expected_normalized - actual_normalized
        fazla_normalized = actual_normalized - expected_normalized

        # Orijinal isimlere geri dön (raporlama için)
        name_map_expected = {self._normalize_filename(f): f for f in expected_files}
        name_map_actual = {self._normalize_filename(f): f for f in actual_files}

        eksik = [name_map_expected[f] for f in eksik_normalized]
        fazla = [name_map_actual[f] for f in fazla_normalized]

        if eksik:
            logger.error(f"🔴 EKSİK BELGELER ({len(eksik)}): {eksik}")
            self.validation_errors.append({
                'type': 'missing_documents',
                'missing': eksik,
                'severity': 'CRITICAL'
            })

        if fazla:
            logger.warning(f"🟡 Fazla belgeler (üst yazıda belirtilmemiş) ({len(fazla)}): {fazla}")
            self.validation_warnings.append({
                'type': 'extra_documents',
                'extra': fazla,
                'severity': 'WARNING'
            })

        match = len(eksik) == 0 and len(fazla) == 0

        if match:
            logger.info(f"✓ Belge listesi tam: {len(actual_files)} belge")

        return {
            'expected_count': len(expected_files),
            'actual_count': len(actual_files),
            'missing': eksik,
            'extra': fazla,
            'match': match
        }

    def get_validation_report(self) -> Dict:
        """
        Validation raporunu döndür.

        Returns:
            Dict: Validation özeti
        """
        status = 'PASS' if len(self.validation_errors) == 0 else 'FAIL'

        return {
            'status': status,
            'total_errors': len(self.validation_errors),
            'total_warnings': len(self.validation_warnings),
            'errors': self.validation_errors,
            'warnings': self.validation_warnings,
            'field_checks': self.field_checks,
            'summary': self._get_summary()
        }

    def _get_summary(self) -> str:
        """
        İnsan okunabilir özet.
        """
        total_checks = len(self.field_checks)
        passed = sum(1 for c in self.field_checks if c['match'])
        failed = total_checks - passed

        if len(self.validation_errors) == 0:
            return f"✓ Doğrulama başarılı! {passed}/{total_checks} kontrol geçti ({len(self.validation_warnings)} uyarı)"
        else:
            return f"✗ Doğrulama başarısız! {len(self.validation_errors)} kritik hata, {len(self.validation_warnings)} uyarı"

    def _normalize_string(self, s: str) -> str:
        """
        String'i normalize et (karşılaştırma için).
        - Büyük harfe çevir
        - Gereksiz boşlukları temizle
        - Türkçe karakterleri koru
        """
        return ' '.join(s.strip().upper().split())

    def _normalize_filename(self, filename: str) -> str:
        """
        Dosya adını normalize et.
        - Küçük harfe çevir
        - Boşlukları temizle
        - Özel karakterleri kaldır
        """
        normalized = filename.lower().strip()
        # Türkçe karakterler ve temel noktalama dışındakileri temizle
        normalized = normalized.replace(' ', '_')
        return normalized
