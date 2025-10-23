"""
SGK Hizmet Dökümü analyzer.
"""

import base64
import logging
from typing import Dict, Any, Optional
from .base_analyzer import BaseAnalyzer
from services.sgk_parser import SGKParser
from models.belge import Belge

logger = logging.getLogger(__name__)


class SGKAnalyzer(BaseAnalyzer):
    """SGK analiz sınıfı - Özel parser kullanır"""

    def __init__(self):
        super().__init__()
        self.parser = SGKParser()

    def get_document_type(self) -> str:
        return "SGK Hizmet Dökümü"

    def analyze(self, belge_id: int, belge_content: str = None, belgeTipi: str = None) -> Optional[Dict[str, Any]]:
        """
        SGK belgesi için özel parse (chunk'sız).
        Fallback: Eğer parse başarısız olursa LLM chunk analizi.
        """
        logger.info(f"SGK belgesi özel parser ile analiz ediliyor (belgeId={belge_id})...")

        # PDF bytes al
        belge = Belge.get_by_id(belge_id)
        if not belge or not belge.get('belgeIcerik'):
            logger.error(f"Belge içeriği bulunamadı: {belge_id}")
            return None

        try:
            pdf_bytes = base64.b64decode(belge['belgeIcerik'])
        except Exception as e:
            logger.error(f"Base64 decode hatası: {e}")
            return None

        # Özel parser kullan (chunk'lamadan!)
        try:
            result = self.parser.parse_sgk_document(pdf_bytes)

            if result:
                logger.info(f"✓ SGK parse başarılı: {result['toplam_is_deneyimi_yil']}y {result['toplam_is_deneyimi_ay']}a")

                # ÖNEMLİ: Sektör bilgilerini NULL yap!
                # SGK belgesinde sektör bilgisi YOK, sadece toplam deneyim var
                # Sektör bilgileri SADECE sektör belgelerinden gelecek
                result['tecrube_enerji'] = None
                result['tecrube_enerji_yil'] = None
                result['tecrube_enerji_ay'] = None
                result['tecrube_metal'] = None
                result['tecrube_metal_yil'] = None
                result['tecrube_metal_ay'] = None
                result['tecrube_mineral'] = None
                result['tecrube_mineral_yil'] = None
                result['tecrube_mineral_ay'] = None
                result['tecrube_kimya'] = None
                result['tecrube_kimya_yil'] = None
                result['tecrube_kimya_ay'] = None
                result['tecrube_atik'] = None
                result['tecrube_atik_yil'] = None
                result['tecrube_atik_ay'] = None
                result['tecrube_diger'] = None
                result['tecrube_diger_yil'] = None
                result['tecrube_diger_ay'] = None

                logger.info("Sektör bilgileri NULL olarak işaretlendi (sektör belgelerinden gelecek)")

                return result
            else:
                logger.warning("SGK parser sonuç döndürmedi")

        except Exception as e:
            logger.error(f"SGK parse hatası: {e}", exc_info=True)

        # Fallback: LLM chunk analizi
        logger.warning("⚠️ FALLBACK: LLM chunk analizi denenecek...")
        logger.warning("⚠️ DİKKAT: LLM chunk analizi güvenilir değil! Manuel kontrol gerekli!")

        return super().analyze(belge_id, belge_content, belgeTipi)

    def get_prompt_template(self) -> str:
        return """Sen bir SGK belgesi analiz uzmanısın. Aşağıdaki SGK Hizmet Dökümü belgesini DETAYLI analiz et ve TÜM iş deneyimi bilgilerini JSON formatında çıkar.

=== BELGE İÇERİĞİ ===
{document_text}

=== ÇIKARILMASı GEREKEN TÜM BİLGİLER ===

1. TOPLAM İŞ DENEYİMİ:
   - Belgede yazan TOPLAM çalışma süresini yıl ve ay olarak hesapla
   - toplam_is_deneyimi_yil: Tam yıl kısmı (örn: 12 yıl 5 ay ise -> 12)
   - toplam_is_deneyimi_ay: Kalan ay kısmı (örn: 12 yıl 5 ay ise -> 5)

2. İŞYERİ BAZINDA DETAYLI KAYITLAR:
   - Her işyerindeki çalışma süresini, pozisyonu, sektörü tespit et
   - is_deneyimi_detay: [
       {{
         "isyeri_adi": "ABC Enerji A.Ş.",
         "sektor": "Enerji|Metal|Mineral|Kimya|Atık|Diğer",
         "pozisyon": "Mühendis|Teknisyen|Uzman|Müdür|Diğer",
         "baslangic_tarihi": "2015-01-15",
         "bitis_tarihi": "2020-06-30",
         "calisma_gun": 1825,
         "calisma_yil": 5,
         "calisma_ay": 5,
         "sgk_kodu": "1234567",
         "is_kolu": "Enerji üretimi ve dağıtımı"
       }}
     ]

3. SEKTÖR BAZINDA TOPLAM DENEYİMLER:
   NOT: Her sektördeki TOPLAM çalışma süresini hesapla
   - sektor_deneyimleri: [
       {{
         "sektor": "Enerji",
         "yil": 5,
         "ay": 6,
         "gun": 180,
         "toplam_gun": 2010,
         "isyeri_sayisi": 2
       }}
     ]

   Ayrıca direkt alanlarda da ver:
   - tecrube_enerji_yil: Enerji sektöründe toplam yıl (0 ise 0)
   - tecrube_enerji_ay: Enerji sektöründe kalan ay
   - tecrube_metal_yil: Metal sektöründe toplam yıl (0 ise 0)
   - tecrube_metal_ay: Metal sektöründe kalan ay
   - tecrube_mineral_yil: Mineral sektöründe toplam yıl (0 ise 0)
   - tecrube_mineral_ay: Mineral sektöründe kalan ay
   - tecrube_kimya_yil: Kimya sektöründe toplam yıl (0 ise 0)
   - tecrube_kimya_ay: Kimya sektöründe kalan ay
   - tecrube_atik_yil: Atık sektöründe toplam yıl (0 ise 0)
   - tecrube_atik_ay: Atık sektöründe kalan ay
   - tecrube_diger_yil: Diğer sektörlerde toplam yıl (0 ise 0)
   - tecrube_diger_ay: Diğer sektörlerde kalan ay

4. SEKTÖR TESPİTİ İPUÇLARI:
   - Enerji: Elektrik üretimi, enerji santrali, rüzgar, güneş enerjisi, doğalgaz
   - Metal: Demir-çelik, alüminyum, döküm, metalurji
   - Mineral: Çimento, seramik, cam, madencilik
   - Kimya: Kimyasal üretim, petrokimya, gübre, ilaç
   - Atık: Atık yönetimi, geri dönüşüm, arıtma tesisi
   - Diğer: Yukarıdakilere uymayan tüm sektörler

5. SİGORTA PRİM GÜNLERİ:
   - toplam_prim_gun: Belgede yazan toplam prim gün sayısı
   - ilk_ise_giris_tarihi: İlk SGK kaydı tarihi
   - son_cikis_tarihi: Son çıkış tarihi (hala çalışıyorsa null)

6. HİZMET SÜRESİ FARKLARI (Varsa):
   - hizmet_eksiği_gun: Eksik gün sayısı (varsa)
   - hizmet_fazlasi_gun: Fazla gün sayısı (varsa)

=== ÇIKTI FORMATI ===
SADECE AŞAĞIDAKİ JSON FORMATINDA DÖNDÜR!

{{
  "toplam_is_deneyimi_yil": 12,
  "toplam_is_deneyimi_ay": 5,
  "toplam_prim_gun": 4565,
  "ilk_ise_giris_tarihi": "2010-01-15",
  "son_cikis_tarihi": "2022-06-30",
  "hizmet_eksiği_gun": 0,
  "hizmet_fazlasi_gun": 0,
  "tecrube_enerji_yil": 8,
  "tecrube_enerji_ay": 3,
  "tecrube_metal_yil": 2,
  "tecrube_metal_ay": 6,
  "tecrube_mineral_yil": 0,
  "tecrube_mineral_ay": 0,
  "tecrube_kimya_yil": 1,
  "tecrube_kimya_ay": 8,
  "tecrube_atik_yil": 0,
  "tecrube_atik_ay": 0,
  "tecrube_diger_yil": 0,
  "tecrube_diger_ay": 0,
  "sektor_deneyimleri": [
    {{
      "sektor": "Enerji",
      "yil": 8,
      "ay": 3,
      "gun": 180,
      "toplam_gun": 3000,
      "isyeri_sayisi": 3
    }},
    {{
      "sektor": "Metal",
      "yil": 2,
      "ay": 6,
      "gun": 0,
      "toplam_gun": 900,
      "isyeri_sayisi": 1
    }},
    {{
      "sektor": "Kimya",
      "yil": 1,
      "ay": 8,
      "gun": 0,
      "toplam_gun": 600,
      "isyeri_sayisi": 1
    }}
  ],
  "is_deneyimi_detay": [
    {{
      "isyeri_adi": "ABC Enerji A.Ş.",
      "sektor": "Enerji",
      "pozisyon": "Çevre Mühendisi",
      "baslangic_tarihi": "2015-01-15",
      "bitis_tarihi": "2020-06-30",
      "calisma_gun": 1825,
      "calisma_yil": 5,
      "calisma_ay": 0,
      "sgk_kodu": "1234567",
      "is_kolu": "Elektrik enerjisi üretimi"
    }},
    {{
      "isyeri_adi": "XYZ Metal San. Tic. A.Ş.",
      "sektor": "Metal",
      "pozisyon": "Çevre Uzmanı",
      "baslangic_tarihi": "2020-07-01",
      "bitis_tarihi": "2022-12-31",
      "calisma_gun": 900,
      "calisma_yil": 2,
      "calisma_ay": 6,
      "sgk_kodu": "7654321",
      "is_kolu": "Demir-çelik üretimi"
    }}
  ]
}}

=== ÖNEMLİ KURALLAR ===
1. Tarihler ISO 8601 formatında: "YYYY-MM-DD"
2. Gün sayısını yıl/ay'a çevir: 365 gün = 1 yıl, 30 gün = 1 ay
3. Sektör tespit edilemiyorsa: "Diğer" yaz
4. Eğer bir bilgi BULUNAMAZSA: null yaz
5. Toplam hesapları DİKKATLİCE yap (hatalı hesaplama kabul edilmez!)
6. Aynı sektörde birden fazla işyeri varsa süreleri TOPLA
7. JSON formatı MUTLAKA GEÇERLİ olmalı

SADECE JSON DÖNDÜR. BAŞKA BİR ŞEY YAZMA!
"""
