"""
Belge gereksinimleri kontrolü
Her başvuru tipi için hangi belgelerin zorunlu olduğunu tanımlar
"""
from typing import Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class DocumentRequirementsChecker:
    """HizmetAdi'ye göre gerekli belgeleri kontrol eder"""

    # Hizmet Adı → Zorunlu Belgeler Mapping
    # API'den gelen GERÇEK belgeTipi isimleri kullanılıyor (turkish_lower ile normalize edilmiş)
    REQUIREMENTS_BY_HIZMET = {
        "sanayide yeşil dönüşüm sorumlusu (akademisyen)": {
            "yök lisans diploması": True,
            "sgk hizmet dökümü": True,
            "adli sicil kaydı": True,
            "hitap hizmet dökümü": True,
            "özgeçmiş/cv": True,
            "fotoğraf (vesikalık)": True,
            "proje dosyası (1)": True,
            # Sektör belgeleri zorunlu değil
            "enerji üretimi": False,
            "metal üretimi ve işlemesi": False,
            "mineral endüstrisi": False,
            "kimya endüstrisi": False,
            "atık yönetimi": False,
            "diğer üretim faaliyetleri": False,
        },
        "sanayide yeşil dönüşüm sorumlusu (eski bakanlık personeli)": {
            "yök lisans diploması": True,
            "sgk hizmet dökümü": True,
            "adli sicil kaydı": True,
            "hitap hizmet dökümü": True,
            "özgeçmiş/cv": True,
            "fotoğraf (vesikalık)": True,
            # Sektör belgeleri zorunlu değil
            "enerji üretimi": False,
            "metal üretimi ve işlemesi": False,
            "mineral endüstrisi": False,
            "kimya endüstrisi": False,
            "atık yönetimi": False,
            "diğer üretim faaliyetleri": False,
        },
        "sanayide yeşil dönüşüm sorumlusu (sektör çalışanı)": {
            "yök lisans diploması": True,
            "sgk hizmet dökümü": True,
            "adli sicil kaydı": True,
            "hitap hizmet dökümü": False,  # Sektör çalışanı için zorunlu DEĞİL
            "özgeçmiş/cv": True,
            "fotoğraf (vesikalık)": True,
            # Sektör belgeleri zorunlu değil
            "enerji üretimi": False,
            "metal üretimi ve işlemesi": False,
            "mineral endüstrisi": False,
            "kimya endüstrisi": False,
            "atık yönetimi": False,
            "diğer üretim faaliyetleri": False,
        },
        "sanayide yeşil dönüşüm baş sorumlusu (akademisyen)": {
            "yök lisans diploması": True,
            "sgk hizmet dökümü": True,
            "adli sicil kaydı": True,
            "hitap hizmet dökümü": True,
            "özgeçmiş/cv": True,
            "fotoğraf (vesikalık)": True,
            "proje dosyası (1)": True,
            "proje dosyası (2)": True,
            "proje dosyası (3)": True,
            # Sektör belgeleri zorunlu değil
            "enerji üretimi": False,
            "metal üretimi ve işlemesi": False,
            "mineral endüstrisi": False,
            "kimya endüstrisi": False,
            "atık yönetimi": False,
            "diğer üretim faaliyetleri": False,
        },
        "sanayide yeşil dönüşüm baş sorumlusu (eski bakanlık personeli)": {
            "yök lisans diploması": True,
            "sgk hizmet dökümü": True,
            "adli sicil kaydı": True,
            "hitap hizmet dökümü": True,
            "özgeçmiş/cv": True,
            "fotoğraf (vesikalık)": True,
            # Sektör belgeleri zorunlu değil
            "enerji üretimi": False,
            "metal üretimi ve işlemesi": False,
            "mineral endüstrisi": False,
            "kimya endüstrisi": False,
            "atık yönetimi": False,
            "diğer üretim faaliyetleri": False,
        },
        "sanayide yeşil dönüşüm baş sorumlusu (sektör çalışanı)": {
            "yök lisans diploması": True,
            "sgk hizmet dökümü": True,
            "adli sicil kaydı": True,
            "hitap hizmet dökümü": False,  # Sektör çalışanı için zorunlu DEĞİL
            "özgeçmiş/cv": True,
            "fotoğraf (vesikalık)": True,
            # Sektör belgeleri zorunlu değil
            "enerji üretimi": False,
            "metal üretimi ve işlemesi": False,
            "mineral endüstrisi": False,
            "kimya endüstrisi": False,
            "atık yönetimi": False,
            "diğer üretim faaliyetleri": False,
        },
    }

    def __init__(self):
        self.required_documents = {}
        self.found_documents = {}
        self.missing_documents = []
        self.warnings = []
        self.errors = []

    def check_requirements(
        self,
        hizmet_adi: str,
        processed_documents: List[Dict]
    ) -> Dict:
        """
        Gerekli belgelerin varlığını kontrol et

        Args:
            hizmet_adi: Hizmet adı (örn: "Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)")
            processed_documents: İşlenmiş belgeler

        Returns:
            {
                "valid": bool,
                "missing_documents": List[str],
                "warnings": List[str],
                "errors": List[str],
                "completeness_score": float  # 0-100
            }
        """
        self.errors = []
        self.warnings = []
        self.missing_documents = []

        # HizmetAdi'yi normalize et (turkish_lower)
        from app.core.document_classifier import turkish_lower
        hizmet_normalized = turkish_lower(hizmet_adi or "")

        # Gerekli belgeleri al
        required_docs = self.REQUIREMENTS_BY_HIZMET.get(hizmet_normalized)

        if not required_docs:
            logger.warning(f"⚠️  Bilinmeyen hizmet: {hizmet_adi}")
            return {
                "valid": False,
                "missing_documents": [],
                "warnings": [f"⚠️  Bilinmeyen hizmet adı: {hizmet_adi}"],
                "errors": ["❌ Hizmet adı tanınmıyor"],
                "completeness_score": 0,
                "total_required": 0,
                "total_found": 0
            }

        logger.info(f"📋 Gereksinim kontrolü: {hizmet_adi}")

        # Hangi belge tipleri bulunmuş?
        found_types = set()
        for doc in processed_documents:
            belge_tipi = turkish_lower(doc.get("belge_tipi") or "")
            if belge_tipi:
                found_types.add(belge_tipi)

        # Zorunlu belgeleri kontrol et (BelgeZorunluMu == Evet)
        total_required = sum(1 for is_required in required_docs.values() if is_required)
        total_found = 0

        for belge_adi, is_required in required_docs.items():
            if not is_required:
                continue  # Zorunlu değilse atla

            # Bu belge bulunmuş mu?
            if belge_adi in found_types:
                total_found += 1
            else:
                self.missing_documents.append(belge_adi.title())
                self.errors.append(f"❌ Eksik belge: {belge_adi.title()}")

        # Belge tipi uyuşmazlıklarını kontrol et
        self._check_document_type_consistency(processed_documents)

        # Tamamlanma skoru hesapla
        completeness_score = (total_found / total_required * 100) if total_required > 0 else 0

        return {
            "valid": len(self.errors) == 0,
            "missing_documents": self.missing_documents,
            "warnings": self.warnings,
            "errors": self.errors,
            "completeness_score": round(completeness_score, 1),
            "total_required": total_required,
            "total_found": total_found
        }

    def _check_document_type_consistency(self, processed_documents: List[Dict]):
        """
        API'den gelen belge tipi ile içerikten tespit edilen tip uyuşuyor mu?
        """
        for doc in processed_documents:
            belge_adi = doc.get("belge_adi", "")
            api_belge_tipi = doc.get("api_belge_tipi")  # API'den gelen tip
            tespit_edilen_tip = doc.get("belge_tipi")  # İçerikten tespit edilen

            # API'den belge tipi gelmişse kontrol et
            if api_belge_tipi and tespit_edilen_tip:
                api_lower = api_belge_tipi.lower()
                tespit_lower = tespit_edilen_tip.lower()

                # Tip uyumlu mu kontrol et
                if not self._are_types_compatible(api_lower, tespit_lower):
                    self.warnings.append(
                        f"⚠️ Belge tipi uyuşmazlığı: '{belge_adi}' "
                        f"API='{api_belge_tipi}' vs İçerik='{tespit_edilen_tip}'"
                    )

    def _are_types_compatible(self, type1: str, type2: str) -> bool:
        """İki belge tipi uyumlu mu?"""
        # Özgeçmiş tipleri
        if any(x in type1 for x in ["özgeçmiş", "cv"]) and any(x in type2 for x in ["özgeçmiş", "cv"]):
            return True

        # Diploma tipleri
        if any(x in type1 for x in ["diploma", "lisans"]) and any(x in type2 for x in ["diploma", "lisans"]):
            return True

        # SGK tipleri
        if any(x in type1 for x in ["sgk", "sigorta", "hizmet"]) and any(x in type2 for x in ["sgk", "sigorta", "hizmet"]):
            return True

        # Adli sicil
        if any(x in type1 for x in ["adli", "sicil", "sabıka"]) and any(x in type2 for x in ["adli", "sicil", "sabıka"]):
            return True

        # Tam eşleşme
        if type1 == type2:
            return True

        return False

    def _get_category_display_name(self, category: str) -> str:
        """Kategori adını kullanıcı dostu hale getir"""
        names = {
            "özgeçmiş": "Özgeçmiş/CV",
            "diploma": "Diploma/Mezuniyet Belgesi",
            "adli_sicil": "Adli Sicil Kaydı",
            "kimlik": "Kimlik Belgesi/Nüfus Cüzdanı Fotokopisi",
            "sgk": "SGK Hizmet Dökümü",
            "hitap": "Hitap Hizmet Dökümü",
            "hizmet_belgesi": "Hizmet Belgesi (Hitap/Görev Belgesi)",
            "fotograf": "Fotoğraf (vesikalık)",
            "proje_1": "Proje 1",
            "proje_2": "Proje 2",
            "proje_3": "Proje 3"
        }
        return names.get(category, category.replace("_", " ").title())
