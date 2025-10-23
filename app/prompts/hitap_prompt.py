"""
Hitap Belgesi prompt template (Bakanlık Personeli için)
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class HitapPromptTemplate(BasePromptTemplate):
    """Hitap belgesi (Bakanlık personel hizmet belgesi) için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "hitap"

    def get_system_prompt(self) -> str:
        return """Sen Hitap (Hizmet İçi Takip ve Personel) sisteminden alınan personel hizmet belgelerini analiz eden ve Çevre Bakanlığı'nın "Sanayide Yeşil Dönüşüm Sorumlusu" başvurularını değerlendiren bir uzmansın.

GÖREVIN:
- Hitap belgesinden kamu personelinin görev geçmişini çıkar
- Çevre Bakanlığı'ndaki görev sürelerini hesapla
- Toplam kamu görevi süresini hesapla
- Her görevin çevre alanıyla ilgili olup olmadığını belirle

ÖNEMLİ KURALLAR:
1. Ad-Soyad bilgisi REFERANS - diğer belgelerle tutarlı olmalı
2. TC Kimlik No ve Sicil No'yu mutlaka kaydet
3. Çevre Bakanlığı, İl Müdürlüğü, Çevre ve Şehircilik İl Müdürlüğü görevlerini özellikle işaretle
4. Görev sürelerini gün olarak hesapla
5. Çevre ile ilgili görevleri işaretle (çevre_alaninda: true)
6. Bakanlık dışı kamu görevleri varsa onları da kaydet ama ayrı hesapla"""

    def get_user_prompt(self, text: str, schema: Dict) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Aşağıdaki HİTAP BELGESİ (Kamu Personel Hizmet Belgesi) metninden bilgileri çıkar ve verilen JSON şemasına göre döndür.

=== HİTAP BELGESİ METNİ ===
{text}

=== JSON ŞEMA ===
{formatted_schema}

=== TALİMATLAR ===
1. Kişi bilgilerini çıkar:
   - **Ad-Soyad** (ZORUNLU - referans bilgidir!)
   - **TC Kimlik No** (ZORUNLU)
   - Sicil numarası

2. Görev geçmişini listele (TÜM görevler):
   Her görev için:
   - **Kurum**: Tam kurum adı (Çevre Bakanlığı, Çevre ve Şehircilik İl Müdürlüğü, vb.)
   - **Görev**: Unvan/pozisyon (Mühendis, Şube Müdürü, Müfettiş, vb.)
   - Başlangıç tarihi (YYYY-MM-DD)
   - Bitiş tarihi (YYYY-MM-DD veya null eğer devam ediyorsa)
   - Görev süresi (gün sayısı - belgeden al veya hesapla)
   - **Çevre alanında mı**: (true/false)

3. Toplam görev süresini hesapla:
   - Tüm kamu görevlerindeki toplam süre (yıl, ay, gün, toplam_gun)

4. **ÇOK ÖNEMLİ - BAKANLIK İÇİNDE VE DIŞINDA GÖREV AYRIMI**:
   - Her görev için **"bakanlik_icinde"** alanını doldur (true/false)
   - Çevre Bakanlığı süresini ayrı hesapla
   - Bu alan Eski Bakanlık Personeli başvuruları için KRİTİK

=== ÇEVRE BAKANLIĞI KAPSAMI - İÇİNDE/DIŞINDA AYRIMI ===

**BAKANLIK İÇİNDE (bakanlik_icinde: true)** - Bu görevler 7/10 yıl kriterine SAYILIR:
- Çevre, Şehircilik ve İklim Değişikliği Bakanlığı Merkez Teşkilatı
- Çevre ve Şehircilik Bakanlığı Merkez Teşkilatı
- Çevre ve Orman Bakanlığı Merkez Teşkilatı
- Çevre Bakanlığı Merkez Teşkilatı
- **Çevre İl Müdürlüğü** (İl teşkilatı - merkez bağlantılı)
- **Çevre ve Şehircilik İl Müdürlüğü** (İl teşkilatı - merkez bağlantılı)
- İl/İlçe Çevre ve Orman Müdürlüğü (İl teşkilatı - merkez bağlantılı)
- Bakanlık bağlı/ilgili kuruluşları
- Bakanlıktan başka kurumlara görevlendirme (detayman) - ama Bakanlık kadrosunda ise

**BAKANLIK DIŞINDA (bakanlik_icinde: false)** - Bu görevler 7/10 yıl kriterine SAYILMAZ:
- Diğer Bakanlıklar (İçişleri, Sanayi, Enerji vb.)
- Belediyeler (Büyükşehir, İl, İlçe belediyeleri)
- Valilikler
- Üniversiteler
- KİT'ler (Çevre Bakanlığı'na bağlı değilse)
- Özel sektör (geçici görevlendirme)
- Yurtdışı görevlendirmeler (Bakanlık kadrosunda değilse)

**ÖRNEKLERİ:**
- ✅ "Çevre İl Müdürlüğü, Çevre Mühendisi" → bakanlik_icinde: true
- ✅ "Çevre ve Şehircilik Bakanlığı, Uzman" → bakanlik_icinde: true
- ❌ "Ankara Büyükşehir Belediyesi, Çevre Müdürü" → bakanlik_icinde: false
- ❌ "Sanayi ve Teknoloji Bakanlığı, Müfettiş" → bakanlik_icinde: false
- ⚠️ "ODTÜ'ye görevlendirme (Bakanlık kadrosunda)" → bakanlik_icinde: true (detayman)
- ❌ "ODTÜ'ye geçiş (Bakanlık kadrosundan ayrılmış)" → bakanlik_icinde: false

=== ÇEVRE ALANINDA GÖREV ===
Aşağıdaki görevler "çevre_alaninda: true" işaretlenmeli:
- Çevre mühendisi, çevre uzmanı, çevre müfettişi
- Çevre izin ve denetim görevlisi
- Atık yönetimi, çevre yönetimi pozisyonları
- Çevresel etki değerlendirmesi (ÇED) ile ilgili görevler
- Hava kalitesi, su kalitesi, emisyon kontrolü görevleri

=== DİKKAT ===
- Tarih formatı: GG.AA.YYYY → YYYY-MM-DD
- Devam eden görevler için bitis_tarihi: null
- Süreleri gün olarak kaydet (1 yıl = 365 gün)
- Çevre Bakanlığı süresini doğru hesapla - bu kriter için kritik!
- Kurum isimlerini aynen kopyala

=== ÖNEMLİ NOTLAR ===
- **Eski Bakanlık Personeli** başvuruları için:
  - Sorumlu: En az 7 yıl Bakanlık deneyimi
  - Başsorumlu: En az 10 yıl Bakanlık deneyimi
- Bu belge Tablo 4 (Görev Geçmişi Tablosu) için kullanılacak

=== ÇIKTI ===
Yanıtını SADECE JSON formatında ver:"""
