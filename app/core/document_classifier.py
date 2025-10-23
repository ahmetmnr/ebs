"""
Belge tipi sınıflandırıcı
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def turkish_lower(text: str) -> str:
    """
    Türkçe karakterleri doğru işleyen lowercase fonksiyonu
    Python'un standart lower() fonksiyonu Türkçe İ → i̇ (noktalı i) yapar
    Bu fonksiyon İ → i (normal i) dönüşümü yapar
    """
    replacements = {
        'İ': 'i',
        'I': 'ı',
        'Ğ': 'ğ',
        'Ü': 'ü',
        'Ş': 'ş',
        'Ö': 'ö',
        'Ç': 'ç'
    }
    result = text
    for upper, lower in replacements.items():
        result = result.replace(upper, lower)
    return result.lower()


class DocumentClassifier:
    """
    Belge tipini tespit eder ve schema key'ine map'ler

    ÖNEMLİ: Sadece belgeTipi alanına bakıyoruz!
    """

    # API'den gelen belge tiplerini schema key'lerine map'le
    BELGE_TIPI_MAP = {
        # null/empty → ustyazi
        None: "ustyazi",
        "": "ustyazi",

        # Temel belgeler
        "yök lisans diploması": "yök lisans diploması",
        "sgk hizmet dökümü": "sgk hizmet dökümü",
        "adli sicil kaydı": "adli sicil kaydı",
        "hitap hizmet dökümü": "hitap hizmet dökümü",
        "özgeçmiş/cv": "özgeçmiş/cv",
        "fotoğraf (vesikalık)": "fotoğraf (vesikalık)",

        # Sektör belgeleri
        "enerji üretimi": "enerji üretimi",
        "metal üretimi ve işlemesi": "metal üretimi ve işlemesi",
        "mineral endüstrisi": "mineral endüstrisi",
        "kimya endüstrisi": "kimya endüstrisi",
        "atık yönetimi": "atık yönetimi",
        "diğer üretim faaliyetleri": "diğer üretim faaliyetleri",

        # Akademik projeler
        "proje dosyası (1)": "proje dosyası (1)",
        "proje dosyası (2)": "proje dosyası (2)",
        "proje dosyası (3)": "proje dosyası (3)",
    }

    def classify(
        self,
        filename: str,
        text: Optional[str] = None,
        belge_tipi: Optional[str] = None
    ) -> str:
        """
        Belge tipini tespit et ve schema key'ine map'le

        Args:
            filename: Dosya adı (kullanılmıyor)
            text: Belge metni (kullanılmıyor)
            belge_tipi: API'den gelen belge tipi

        Returns:
            Schema key (lowercase)
        """
        # belgeTipi null ise ustYazi'dır
        if belge_tipi is None or not belge_tipi.strip():
            logger.info(f"belgeTipi null → ustyazi: {filename}")
            return "ustyazi"

        # Lowercase'e çevir
        normalized = turkish_lower(belge_tipi)

        # Map'te var mı kontrol et
        if normalized in self.BELGE_TIPI_MAP:
            mapped = self.BELGE_TIPI_MAP[normalized]
            logger.info(f"belgeTipi: '{belge_tipi}' → '{mapped}'")
            return mapped
        else:
            # Map'te yoksa uyarı ver ve olduğu gibi döndür
            logger.warning(f"⚠️  Bilinmeyen belgeTipi: '{belge_tipi}' (normalized: '{normalized}')")
            return normalized
