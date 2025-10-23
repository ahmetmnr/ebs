"""
Prompt Factory - SOLID: Factory Pattern + Dependency Inversion
Başvuru tipine göre özelleştirilmiş prompt seçimi
"""
from typing import Dict, Optional
from app.prompts.base_prompt import BasePromptTemplate
from app.prompts.ozgecmis_prompt import OzgecmisPromptTemplate
from app.prompts.ozgecmis_akademisyen_prompt import OzgecmisAkademisyenPromptTemplate
from app.prompts.ozgecmis_bakanlik_prompt import OzgecmisBakanlikPromptTemplate
from app.prompts.ozgecmis_sektor_prompt import OzgecmisSektorPromptTemplate
from app.prompts.sgk_prompt import SGKPromptTemplate
from app.prompts.diploma_prompt import DiplomaPromptTemplate
from app.prompts.adli_sicil_prompt import AdliSicilPromptTemplate
from app.prompts.ustyazi_prompt import UstYaziPromptTemplate
from app.prompts.hitap_prompt import HitapPromptTemplate
from app.prompts.akademik_proje_prompt import AkademikProjePromptTemplate
from app.prompts.sektor_belge_prompt import SektorBelgePromptTemplate


class PromptFactory:
    """
    Prompt factory - SOLID principles:
    - Single Responsibility: Sadece prompt seçimi
    - Open/Closed: Yeni prompt eklemek için extend edilebilir
    - Dependency Inversion: Interface'e bağımlı (BasePromptTemplate)
    """

    # Belge tipi → Prompt mapping
    # SADECE API'den gelen belgeTipi değerleri (DocumentClassifier turkish_lower ile normalize eder)
    _PROMPT_MAP: Dict[str, type[BasePromptTemplate]] = {
        "ustyazi": UstYaziPromptTemplate,
        "özgeçmiş/cv": OzgecmisPromptTemplate,
        "sgk hizmet dökümü": SGKPromptTemplate,
        "yök lisans diploması": DiplomaPromptTemplate,
        "adli sicil kaydı": AdliSicilPromptTemplate,
        "hitap hizmet dökümü": HitapPromptTemplate,
        "proje dosyası (1)": AkademikProjePromptTemplate,
        "proje dosyası (2)": AkademikProjePromptTemplate,
        "proje dosyası (3)": AkademikProjePromptTemplate,
        "enerji üretimi": SektorBelgePromptTemplate,
        "metal üretimi ve işlemesi": SektorBelgePromptTemplate,
        "mineral endüstrisi": SektorBelgePromptTemplate,
        "kimya endüstrisi": SektorBelgePromptTemplate,
        "atık yönetimi": SektorBelgePromptTemplate,
        "diğer üretim faaliyetleri": SektorBelgePromptTemplate,
    }

    @classmethod
    def create_prompt(
        cls,
        document_type: str,
        basvuru_turu: Optional[str] = None
    ) -> Optional[BasePromptTemplate]:
        """
        Belge tipine ve başvuru türüne göre uygun prompt template oluştur

        Args:
            document_type: Belge tipi (özgeçmiş, diploma, sgk vb.)
            basvuru_turu: Başvuru türü (Akademisyen, Bakanlık Personeli, Sektör Çalışanı)

        Returns:
            Prompt template instance veya None
        """
        doc_type_lower = document_type.lower()

        # Özgeçmiş için başvuru türüne göre özel prompt seç
        if "özgeçmiş" in doc_type_lower or "cv" in doc_type_lower:
            if basvuru_turu:
                basvuru_lower = basvuru_turu.lower()
                if "akademisyen" in basvuru_lower:
                    return OzgecmisAkademisyenPromptTemplate()
                elif "bakanlık" in basvuru_lower or "çşib" in basvuru_lower or "personel" in basvuru_lower:
                    return OzgecmisBakanlikPromptTemplate()
                elif "sektör" in basvuru_lower or "çalışan" in basvuru_lower:
                    return OzgecmisSektorPromptTemplate()
            # Başvuru türü belirtilmemişse genel özgeçmiş promptu kullan
            return OzgecmisPromptTemplate()

        # Önce tam eşleşme ara
        if doc_type_lower in cls._PROMPT_MAP:
            prompt_class = cls._PROMPT_MAP[doc_type_lower]
            return prompt_class()

        # Kısmi eşleşme ara (örn: "sgk hizmet dökümü" → "sgk")
        for key, prompt_class in cls._PROMPT_MAP.items():
            if key in doc_type_lower or doc_type_lower in key:
                return prompt_class()

        return None

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Desteklenen belge tiplerini döndür"""
        return list(set(cls._PROMPT_MAP.values()))

    @classmethod
    def register_prompt(cls, document_type: str, prompt_class: type[BasePromptTemplate]):
        """
        Yeni bir prompt template kaydet

        SOLID: Open/Closed - Runtime'da yeni prompt eklenebilir
        """
        cls._PROMPT_MAP[document_type.lower()] = prompt_class
