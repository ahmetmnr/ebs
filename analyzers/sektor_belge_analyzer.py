"""
Sektör belgesi analyzer.
"""

import logging
from typing import Dict, Optional, Any

from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)


class SektorBelgeAnalyzer(BaseAnalyzer):
    """Sektör belgesi analiz sınıfı"""

    def __init__(self, sektor: str = "Enerji"):
        """
        Args:
            sektor: Enerji, Metal, Mineral, Kimya, Atık, Diğer
        """
        super().__init__()
        self.sektor = sektor

    def get_document_type(self) -> str:
        sektor_map = {
            "Enerji": "Enerji Üretimi",
            "Metal": "Metal Üretimi ve İşlemesi",
            "Mineral": "Mineral Endüstrisi",
            "Kimya": "Kimya Endüstrisi",
            "Atık": "Atık Yönetimi",
            "Diğer": "Diğer Üretim Faaliyetleri",
        }
        return sektor_map.get(self.sektor, "Sektör Belgesi")

    def get_prompt_template(self) -> str:
        return f"""Sen bir sektör belgesi analiz uzmanısın. Aşağıdaki {self.sektor} SEKTÖR BELGESİNİ analiz et.

=== BELGE İÇERİĞİ ===
{{document_text}}

=== ÇIKARILMASı GEREKEN BİLGİLER ===

1. SEKTÖR: "{self.sektor}" (DEĞİŞTİRME!)
2. KURUM/FİRMA ADI: Belgede yazan firma/kurum
3. KİŞİ BİLGİLERİ:
   - Ad Soyad
   - Pozisyon (Mühendis/Uzman/Müfettiş/vb.)
4. ÇALIŞMA SÜRESİ:
   - Başlangıç tarihi
   - Bitiş tarihi
   - Toplam süre (yıl ve ay)
5. BELGE BİLGİLERİ:
   - Belge tarihi
   - Düzenleyen kurum

=== ÇIKTI FORMATI ===
SADECE AŞAĞIDAKİ JSON FORMATINDA DÖNDÜR!

{{{{
  "sektor": "{self.sektor}",
  "firma_adi": "ABC Enerji A.Ş.",
  "ad_soyad": "AHMET YILMAZ",
  "pozisyon": "Mühendis",
  "baslangic_tarihi": "2015-01-15",
  "bitis_tarihi": "2023-06-30",
  "calisma_suresi_yil": 8,
  "calisma_suresi_ay": 5,
  "belge_tarihi": "2023-07-01",
  "duzenleyen_kurum": "ABC Enerji A.Ş."
}}}}

=== ÖNEMLİ KURALLAR ===
1. **SADECE BELGEDE AÇIKÇA YAZILI BİLGİLERİ ÇIKAR!**
2. **UYDURMA YAPMA! Eğer bir bilgi BULUNAMAZSA: null yaz**
3. **TAHMİN YAPMA! Belirsiz ise null yaz**
4. **sektor alanını DEĞİŞTİRME!** Her zaman "{self.sektor}" olmalı
5. **Tarihler ISO 8601 formatında:** "YYYY-MM-DD"
6. **Süre hesaplarını DİKKATLE yap:**
   - SADECE belgede yazan tarihleri kullan!
   - Eğer tarih yoksa → null
   - Toplam süreyi kendin hesaplama!
7. Boolean değerler: true/false (string değil!)
8. JSON formatı GEÇERLİ olmalı

🚨 KRİTİK: OLMAYAN BİLGİYİ UYDURMA! BİLMİYORSAN NULL YAZ! 🚨

SADECE JSON DÖNDÜR. AÇIKLAMA, YORUM, MARKDOWN YAPMA!
"""

    def _analyze_text(self, text: str, belge_id: int) -> Optional[Dict[str, Any]]:
        """
        Metin analizi - SEKTÖR BELGELERİ İÇİN SADECE 1 CHUNK!

        Sektör belgeleri çok uzun olabiliyor ve LLM hallüsinasyon yapabiliyor.
        Bu yüzden sadece ilk chunk boyutuna kadar olan kısmı analiz ediyoruz.

        Args:
            text: Belge metni
            belge_id: Belge ID

        Returns:
            Dict: Analiz sonucu
        """
        # Chunk'lara böl
        chunks = self.chunk_manager.create_chunks(text)

        logger.info(f"Sektör Belgesi {belge_id}: {len(chunks)} chunk oluşturuldu, SADECE İLK CHUNK işlenecek")

        if not chunks:
            return None

        # SADECE İLK CHUNK'I İŞLE
        first_chunk = chunks[0]

        chunk_result = self.ollama.analyze_document(
            document_text=first_chunk.text,
            document_type=self.get_document_type(),
            prompt_template=self.get_prompt_template()
        )

        if chunk_result and chunk_result.get('success'):
            result = chunk_result['data']

            # CRITICAL FIX: _chunk_data eklemeden ÖNCE data'nın shallow copy'sini al
            # Yoksa circular reference oluşur (result içinde _chunk_data, _chunk_data içinde result...)
            data_copy = {k: v for k, v in result.items() if k != '_chunk_data'}

            # Chunk verisini kaydetmek için sakla
            result['_chunk_data'] = [{
                'index': 0,
                'start': first_chunk.start,
                'end': first_chunk.end,
                'data': data_copy,  # Shallow copy kullan, recursive yapı olmasın
                'model': chunk_result.get('model'),
                'duration': chunk_result.get('duration')
            }]

            return result

        return None
