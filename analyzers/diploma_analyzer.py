"""
Diploma analyzer.
"""

import logging
from typing import Dict, Optional, Any
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)


class DiplomaAnalyzer(BaseAnalyzer):
    """Diploma analiz sınıfı"""

    def get_document_type(self) -> str:
        return "Yök Lisans Diploması"

    def analyze(self, belge_id: int) -> Optional[Dict[str, Any]]:
        """
        Diploma belgesini analiz et ve sonuca mezuniyet alanlarını ekle.

        Args:
            belge_id: Belge ID

        Returns:
            Dict: Analiz sonucu (diplomalar + mezuniyet alanları)
        """
        # Base analyze çalıştır
        result = super().analyze(belge_id)

        if not result:
            return None

        # Diplomalar varsa, ilk diploma kaydından mezuniyet bilgilerini çıkar
        if 'diplomalar' in result and result['diplomalar']:
            diplomalar = result['diplomalar']

            # Birden fazla diploma olabilir, en yüksek seviyeyi al (YL > Lisans)
            # Öncelik: Doktora > Yüksek Lisans > Lisans
            sorted_diplomas = sorted(
                diplomalar,
                key=lambda d: self._diploma_priority(d.get('program_bolum', '')),
                reverse=True
            )

            # En yüksek seviyedeki diplomayı kullan
            primary_diploma = sorted_diplomas[0]

            # Mezuniyet alanlarını ekle
            result['mezun_universite'] = primary_diploma.get('universite')
            result['mezun_bolum'] = primary_diploma.get('program_bolum')

            # Mezuniyet tarihi DD/MM/YYYY formatında, sadece yılı al
            mezuniyet_tarihi = primary_diploma.get('mezuniyet_tarihi')
            if mezuniyet_tarihi:
                try:
                    # DD/MM/YYYY -> YYYY
                    if isinstance(mezuniyet_tarihi, str) and '/' in mezuniyet_tarihi:
                        yil = mezuniyet_tarihi.split('/')[-1]
                        result['mezuniyet_yili'] = int(yil)
                    elif isinstance(mezuniyet_tarihi, int):
                        result['mezuniyet_yili'] = mezuniyet_tarihi
                except (ValueError, IndexError) as e:
                    logger.warning(f"Mezuniyet yılı parse edilemedi: {mezuniyet_tarihi} - {e}")
                    result['mezuniyet_yili'] = None

            # TC kimlik ve ad-soyad bilgilerini de ekle
            result['tc_kimlik_no'] = primary_diploma.get('tc_kimlik_no')

            # Ad soyad birleştir
            ad = primary_diploma.get('ad', '')
            soyad = primary_diploma.get('soyad', '')
            if ad and soyad:
                result['ad_soyad'] = f"{ad} {soyad}"

            # Eğitim seviyesini belirle
            program = primary_diploma.get('program_bolum', '').upper()
            if 'DOKTORA' in program or 'DR' in program:
                result['egitim_seviyesi'] = 'Doktora'
            elif 'YL' in program or 'YÜKSEK LİSANS' in program or 'MASTER' in program:
                result['egitim_seviyesi'] = 'Yüksek Lisans'
            else:
                result['egitim_seviyesi'] = 'Lisans'

            logger.info(f"✓ Diploma bilgileri eklendi: {result.get('mezun_universite')} - {result.get('mezun_bolum')} ({result.get('mezuniyet_yili')})")

        return result

    def _diploma_priority(self, program_bolum: str) -> int:
        """
        Diploma öncelik seviyesi belirle.

        Args:
            program_bolum: Program/bölüm adı

        Returns:
            int: Öncelik seviyesi (yüksek = daha önemli)
        """
        program_upper = program_bolum.upper()

        if 'DOKTORA' in program_upper or 'DR' in program_upper:
            return 3
        elif 'YL' in program_upper or 'YÜKSEK LİSANS' in program_upper or 'MASTER' in program_upper:
            return 2
        else:
            return 1  # Lisans

    def get_prompt_template(self) -> str:
        return """Sen bir diploma analiz uzmanısın. YÖK diploma belgesinden SADECE BELGEDEKİ bilgileri çıkar.

=== BELGE İÇERİĞİ ===
{document_text}

=== ÇIKARILMASı GEREKEN BİLGİLER ===

NOT: Bir öğrenci BIRDEN FAZLA diploma/eğitim kaydına sahip olabilir (Lisans, Yüksek Lisans, Doktora vb.)
Her MEZUNİYET BİLGİSİ satırını AYRI BİR DİPLOMA olarak çıkar!

Her diploma için:
1. TC_KIMLIK_NO: 11 haneli T.C. Kimlik Numarası
2. AD: Öğrencinin adı (BÜYÜK HARFLE)
3. SOYAD: Öğrencinin soyadı (BÜYÜK HARFLE, evlilik sonrası değişmiş olabilir)
4. UNIVERSITE: Üniversitenin TAM resmi adı (kısaltma YAPMA!)
5. FAKULTE: Fakülte/Enstitü/MYO adı (olduğu gibi)
6. PROGRAM_BOLUM: Program/Bölüm adı (parantez içindeki detayları KORU! Örn: "ÇEVRE MÜHENDİSLİĞİ (YL) (TEZLİ)")
7. MEZUNIYET_TARIHI: DD/MM/YYYY formatında
8. DIPLOMA_NUMARASI: Diploma numarası
9. DIPLOMA_NOTU: Sayısal değer (2.89 veya 86.75 gibi)
10. DURUM: Genellikle "Mezuniyet"

=== ÇIKTI FORMATI ===
{{
  "diplomalar": [
    {{
      "tc_kimlik_no": "23492253976",
      "ad": "ELİF",
      "soyad": "TURKYILMAZ",
      "universite": "ONDOKUZ MAYIS ÜNİVERSİTESİ",
      "fakulte": "MÜHENDİSLİK FAKÜLTESİ",
      "program_bolum": "ÇEVRE MÜHENDİSLİĞİ PR.",
      "mezuniyet_tarihi": "24/08/2016",
      "diploma_numarasi": "1606.A-046",
      "diploma_notu": 2.89,
      "durum": "Mezuniyet"
    }},
    {{
      "tc_kimlik_no": "23492253976",
      "ad": "ELİF",
      "soyad": "SARI",
      "universite": "NECMETTİN ERBAKAN ÜNİVERSİTESİ",
      "fakulte": "FEN BİLİMLERİ ENSTİTÜSÜ",
      "program_bolum": "ÇEVRE MÜHENDİSLİĞİ (YL) (TEZLİ)",
      "mezuniyet_tarihi": "26/06/2019",
      "diploma_numarasi": "190820100002",
      "diploma_notu": 86.75,
      "durum": "Mezuniyet"
    }}
  ]
}}

=== KURALLAR ===
1. **SADECE BELGEDE YAZILI BİLGİLERİ ÇIKAR!**
2. **UYDURMA YAPMA! Bilgi yoksa null yaz**
3. Her diploma kaydını ayrı obje olarak "diplomalar" dizisine ekle
4. Üniversite adını TAM yaz (kısaltma YAPMA!)
5. Program/bölüm adındaki parantez içi bilgileri KORU
6. Diploma notu sayısal olmalı (string değil!)
7. Tek diploma bile olsa DİZİ formatında döndür!

🚨 OLMAYAN BİLGİYİ UYDURMA! BİLMİYORSAN NULL YAZ! 🚨
🚨 HER MEZUNİYET KAYDI AYRI BİR DİPLOMA! 🚨

SADECE JSON DÖNDÜR!
"""
