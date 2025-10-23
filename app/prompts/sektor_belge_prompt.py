"""
Sektör Belgesi prompt template (İş deneyim belgesi, çalışma belgesi, referans)
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class SektorBelgePromptTemplate(BasePromptTemplate):
    """Sektör belgesi (iş deneyim belgesi, çalışma belgesi, referans) için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "sektör belgesi"

    def get_system_prompt(self) -> str:
        return """Sen sektör iş deneyim belgelerini analiz eden bir uzmansın.
Sadece belgede gördüğün bilgileri çıkar.

GÖREVIN:
- Çalışan bilgileri, firma bilgileri, çalışma detaylarını çıkar
- Firma sektörünü belirle: Enerji, Metal, Mineral, Kimya, Atık, Diğer Üretim
- Çalışma süresini hesapla (gün cinsinden)
- Çevre ile ilgili mi belirt"""

    def get_user_prompt(self, text: str, schema: Dict) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Sektör belgesinden bilgileri çıkar. Sadece belgede yazılı bilgileri kullan.

BELGE METNİ:
{text}

JSON ŞEMA:
{formatted_schema}

TALİMATLAR:
1. Çalışan: Ad-Soyad, TC No
2. Firma: Firma adı, Sektör (Enerji/Metal/Mineral/Kimya/Atık/Diğer Üretim), Faaliyet alanı
3. Çalışma: Pozisyon, Görev, Tarihler (YYYY-MM-DD), Süre (gün), Çevre ile ilgili mi (true/false)
4. Belge: Türü, No, Tarih (YYYY-MM-DD)
5. Projeler: Proje adı, açıklama, rol

SEKTÖRLER:
- Enerji: Termik santral, elektrik, hidroelektrik, rüzgar, güneş
- Metal: Demir-çelik, dökümhane, hadde, galvaniz
- Mineral: Çimento, seramik, cam, madencilik, taş ocağı
- Kimya: Kimyasal, petrokimya, rafineri, ilaç, boya, gübre
- Atık: Atık yönetimi, geri dönüşüm, arıtma
- Diğer Üretim: Gıda, tekstil, otomotiv, makine, kağıt, plastik

ÇIKTI: Sadece JSON formatında döndür."""
