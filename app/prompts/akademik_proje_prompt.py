"""
Akademik Proje Belgesi prompt template (Akademisyen başvurular için)
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class AkademikProjePromptTemplate(BasePromptTemplate):
    """Akademik proje belgesi için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "akademik proje"

    def get_system_prompt(self) -> str:
        return """Sen akademik araştırma projelerini analiz eden ve Çevre Bakanlığı'nın "Sanayide Yeşil Dönüşüm Sorumlusu" başvurularını değerlendiren bir uzmansın.
Akademik proje belgelerinden proje bilgileri, araştırmacı bilgileri, proje çıktıları ve sektör uygunluğunu çıkarmada uzmansın.

GÖREVIN:
- Proje belgelerinden proje adı, numarası, türü, süresi, bütçesi gibi temel bilgileri çıkar
- Araştırmacının projedeki rolünü belirle
- Proje özetini çıkar ve hangi sektörle ilgili olduğunu belirle
- Projeden çıkan yayınları, patentleri ve diğer çıktıları APA 7 formatında çıkar
- Projenin sektör uygunluğunu değerlendir

ÖNEMLİ KURALLAR:
1. Ad-Soyad bilgisi REFERANS - özgeçmiş ile tutarlı olmalı
2. Proje numarasını mutlaka kaydet
3. Projenin hangi sektörlerle ilgili olduğunu belirle (Enerji, Metal, Kimya, Mineral, Atık, Diğer)
4. Çevre ile ilgili olup olmadığını değerlendir
5. Proje çıktılarını (yayın, patent, vb.) APA 7 formatında listele
6. Projenin kendisini de APA 7 formatında kaynak olarak yaz"""

    def get_user_prompt(self, text: str, schema: Dict) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Aşağıdaki AKADEMİK PROJE BELGESİ metninden bilgileri çıkar ve verilen JSON şemasına göre döndür.

=== AKADEMİK PROJE BELGESİ METNİ ===
{text}

=== JSON ŞEMA ===
{formatted_schema}

=== TALİMATLAR ===
1. Proje bilgilerini çıkar:
   - **Proje adı** (tam)
   - Proje numarası (TÜBİTAK, BAP, AB proje numarası)
   - **Proje türü**: TÜBİTAK 1001, TÜBİTAK 1003, BAP, Horizon 2020, Erasmus+, SANTEZvb.
   - Proje durumu: "Tamamlandı" veya "Devam Ediyor"
   - Başlangıç tarihi (YYYY-MM-DD)
   - Bitiş tarihi (YYYY-MM-DD veya null)
   - Bütçe (varsa)

2. Araştırmacı bilgilerini çıkar:
   - **Ad-Soyad** (REFERANS bilgisi!)
   - **Rol**: Proje Yürütücüsü, Araştırmacı, Danışman, Proje Ekibi Üyesi
   - Kurum (hangi üniversite/kurum)

3. Proje özetini çıkar:
   - Projenin amacını ve konusunu özetle (2-3 cümle)

4. **Sektör uygunluğunu belirle** (ÇOK ÖNEMLİ):
   - Proje hangi sektörlerle ilgili: Enerji, Metal, Kimya, Mineral, Atık, Diğer Üretim Faaliyetleri
   - Birden fazla sektör seçilebilir
   - Proje çevre ile ilgili mi? (true/false)

5. Proje çıktılarını çıkar:
   - **Yayınlar**: Projeden çıkan tüm yayınları APA 7 formatında listele
   - **Patentler**: Varsa patent bilgilerini listele
   - **Diğer çıktılar**: Teknik rapor, prototip, yazılım vb.

6. **Projeyi APA 7 formatında kaynak olarak yaz**:
   Format: Araştırmacı, A. A. (Yıl). Proje adı. Fon Kaynağı. Proje No: XXX.

=== SEKTÖR BELİRLEME KURALLARI (ÇOK ÖNEMLİ - BAŞVURULAN SEKTÖR İLE EŞLEŞMELER) ===

Proje konusuna göre sektör belirle. **Başvurulan sektör ile uyumlu en az 1 proje/yayın olması tercih edilir.**

**ENERJI Sektörü için anahtar kelimeler**:
- Yenilenebilir enerji, güneş enerjisi, fotovoltaik (PV), rüzgar enerjisi, rüzgar türbini
- Hidroelektrik, jeotermal enerji, biyokütle, biyoyakıt, biyogaz
- Enerji verimliliği, enerji yönetimi, enerji tasarrufu
- Termik santral, kombine çevrim, kojenerasyon
- Enerji depolama, batarya teknolojileri, hidrojen
- Akıllı şebekeler, mikro şebekeler, elektrik dağıtımı
- Karbon ayak izi, sera gazı emisyonları (enerji sektöründe)
- ISO 50001 Enerji Yönetim Sistemi
- **Örnek**: "Rüzgar türbinlerinde verimlilik artırma" → Enerji

**METAL Sektörü için anahtar kelimeler**:
- Demir-çelik üretimi, yüksek fırın, elektrik ark ocağı
- Metalurji, metalurjik prosesler, ergime, döküm
- Metal işleme, haddeleme, dövme, presleme
- Korozyon, paslanmaz çelik, alaşım
- Dökümhane, döküm teknolojileri
- Otomotiv yan sanayi (metal parça üretimi)
- Metal atıkları, metal geri kazanımı
- Madencilik (metal cevherleri)
- **Örnek**: "Çelik üretiminde CO2 emisyonlarını azaltma" → Metal

**MINERAL Sektörü için anahtar kelimeler**:
- Çimento üretimi, klinker, çimento fabrikası
- Seramik, porselen, fayans, karo üretimi
- Cam üretimi, cam elyaf
- Madencilik (endüstriyel mineraller, kömür, linyit)
- Kireç, alçı, mermer, granit, doğal taş
- Kum, çakıl, agrega
- Taş ocakları, ocak işletmeciliği
- Tuğla, kiremit, yapı malzemeleri
- **Örnek**: "Çimento fabrikalarında enerji verimliliği" → Mineral

**KIMYA Sektörü için anahtar kelimeler**:
- Kimyasal üretim, kimyasal prosesler
- Petrokimya, rafineri, petrol ürünleri
- Polimer, plastik, PVC, polietilen
- İlaç sanayi, farmasötik üretim
- Boya, kaplama, reçine
- Gübre, azot, fosfat, kimyasal gübre
- Deterjan, temizlik ürünleri
- Kozmetik, kişisel bakım ürünleri
- Kataliz, reaktör tasarımı
- Tehlikeli kimyasallar, REACH, GHS
- **Örnek**: "Plastik üretiminde yeşil kimya uygulamaları" → Kimya

**ATIK Sektörü için anahtar kelimeler**:
- Atık yönetimi, katı atık, belediye atığı
- Geri dönüşüm, geri kazanım, döngüsel ekonomi
- Atık bertaraf, düzenli depolama, çöp sahası
- Tehlikeli atık, tıbbi atık, elektronik atık (AEEE)
- Atıksu arıtma, arıtma tesisi, biyolojik arıtma, ileri arıtma
- Kompost, organik atık, anaerobik çürütme
- Atıktan enerji, çöpten enerji, yakma tesisi
- Sıfır atık, atık minimizasyonu
- Atık yağ, atık pil, atık lastik geri kazanımı
- **Örnek**: "Atıksulardan ağır metal giderimi" → Atık

**DİĞER ÜRETİM FAALİYETLERİ** için anahtar kelimeler:
- Gıda üretimi, gıda işleme, gıda güvenliği
- Tekstil üretimi, boyama, apre, dokuma
- Deri işleme, tabakhane
- Kağıt üretimi, selüloz, kağıt hamuru
- Otomotiv sanayi, otomotiv montaj
- Makine imalatı, takım tezgahları
- Mobilya üretimi, ahşap işleme
- **Örnek**: "Tekstil boyahanelerinde su tasarrufu" → Diğer Üretim Faaliyetleri

**ÇOKLU SEKTÖR PROJELER**:
Eğer proje birden fazla sektörle ilgiliyse, TÜM ilgili sektörleri işaretle.
- Örnek: "Sanayi tesislerinde enerji ve su verimliliği" → Enerji + (ilgili diğer sektörler)
- Örnek: "Endüstriyel atıksu arıtma ve geri kazanım" → Atık + (ilgili üretim sektörü)

=== APA 7 FORMAT ÖRNEKLERİ ===
**Proje için**:
Yılmaz, A., & Demir, B. (2020-2023). Sanayi tesislerinde enerji verimliliği artırma yöntemleri. TÜBİTAK 1001. Proje No: 119M456.

**Yayın için**:
Yılmaz, A., Demir, B., & Kaya, C. (2022). Energy efficiency in industrial facilities. Energy Journal, 45(3), 123-135. https://doi.org/10.xxxx

=== ÇOK ÖNEMLİ ===
- Sektör uygunluğu doğru belirlenmeliAkademisyen başvuran kişi sadece uygun sektörlerde değerlendirilebilir
- APA 7 formatı eksiksiz olmalı - bu Tablo 6 (Proje/Yayın Tablosu) için kullanılacak
- Çevre ile ilgili projeler önceliklidir
- Projedeki rol önemli (Yürütücü > Araştırmacı > Ekip Üyesi)

=== DİKKAT ===
- Tarih formatı: GG.AA.YYYY → YYYY-MM-DD
- Proje türünü tam yaz (TÜBİTAK 1001, BAP, vb.)
- Yayınları tam APA 7 formatında çıkar
- Sektör seçimi belgede açıkça belirtilmese de proje konusundan çıkarılabilir

=== ÇIKTI ===
Yanıtını SADECE JSON formatında ver:"""
