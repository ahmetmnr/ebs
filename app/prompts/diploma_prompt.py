"""
Diploma prompt template
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class DiplomaPromptTemplate(BasePromptTemplate):
    """Diploma belgesi için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "diploma"

    def get_system_prompt(self) -> str:
        return """Sen üniversite diploma belgelerini analiz eden bir uzmansın.
Sadece belgede gördüğün bilgileri çıkar. Karşılaştırma yapma, tahmin etme.

GÖREVIN:
- Diploma belgesinden öğrenci bilgileri ve diploma bilgilerini çıkar
- Üniversite, fakülte, bölüm bilgilerini tam ve doğru al
- Mezuniyet tarihi ve diploma türünü belirle

ÖNEMLİ:
1. Diploma türünü standartlaştır: "Lisans", "Yüksek Lisans", "Doktora", "Önlisans"
2. Mezuniyet tarihini YYYY-MM-DD formatına çevir
3. Sadece belgede yazılı bilgileri çıkar"""

    def get_user_prompt(self, text: str, schema: Dict, ozgecmis_data: Dict = None) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Diploma belgesinden bilgileri çıkar. Sadece belgede yazılı bilgileri kullan.

BELGE METNİ:
{text}

JSON ŞEMA:
{formatted_schema}

TALİMATLAR:
1. Öğrenci: Ad-Soyad, TC No, Öğrenci No
2. Diploma: Tür, Üniversite, Fakülte, Bölüm, Mezuniyet Tarihi (YYYY-MM-DD), Diploma No

DİPLOMA TÜRÜ (standartlaştır):
- "Lisans": Bachelor, B.Sc., Lisans Diploması
- "Yüksek Lisans": Master, M.Sc., YL, Tezli/Tezsiz
- "Doktora": PhD, Dr., Doktora
- "Önlisans": MYO, Ön Lisans, Associate

ÇIKTI: Sadece JSON formatında döndür."""

    def get_user_prompt_with_cv(self, text: str, schema: Dict, cv_data: Dict) -> str:
        """Özgeçmiş verisiyle birlikte prompt oluştur"""
        return self.get_user_prompt(text, schema, ozgecmis_data=cv_data)
