"""
SGK Hizmet Dökümü Parser
Chunk'lara bölmeden tüm belgeyi parse eder ve doğru deneyim hesaplaması yapar.
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pdfplumber
import io

logger = logging.getLogger(__name__)


class SGKParser:
    """
    SGK Hizmet Dökümü tablosunu parse eder.
    """

    # SGK hesaplama sabitleri
    SGK_DAYS_PER_YEAR = 360
    SGK_DAYS_PER_MONTH = 30

    def __init__(self):
        self.header_info = {}
        self.rows = []
        self.isyerleri = []

    def parse_sgk_document(self, pdf_bytes: bytes) -> Dict:
        """
        SGK belgesini parse et.

        Returns:
            Dict: Parsed SGK data with experience calculations
        """
        try:
            # 1. Tüm metni çıkar (chunk'lamadan!)
            full_text = self._extract_full_text(pdf_bytes)

            if not full_text or len(full_text) < 100:
                logger.error("SGK belgesi çok kısa veya boş")
                return None

            logger.info(f"SGK belgesi yüklendi: {len(full_text)} karakter")

            # 2. Kişi bilgilerini çıkar (header)
            self.header_info = self._extract_header_info(full_text)

            # 3. Tablo satırlarını parse et
            self.rows = self._extract_table_rows(full_text)
            logger.info(f"SGK tablosundan {len(self.rows)} satır bulundu")

            # 4. İşyeri listesini parse et (en alttaki özet tablo)
            self.isyerleri = self._extract_isyeri_list(full_text)

            # 5. Deneyim hesapla
            experience = self._calculate_experience(self.rows)

            # 6. Sonucu birleştir
            result = {
                **self.header_info,
                **experience,
                'kayit_sayisi': len(self.rows),
                'isyeri_sayisi': len(self.isyerleri),
                'kayitlar': self.rows[:10] if len(self.rows) > 10 else self.rows,  # İlk 10 kayıt
                'isyerleri': self.isyerleri
            }

            logger.info(f"✓ SGK parse başarılı: {experience['toplam_is_deneyimi_yil']}y {experience['toplam_is_deneyimi_ay']}a")

            return result

        except Exception as e:
            logger.error(f"SGK parse hatası: {e}", exc_info=True)
            return None

    def _extract_full_text(self, pdf_bytes: bytes) -> str:
        """
        PDF'den tüm metni çıkar.
        """
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"

                return full_text
        except Exception as e:
            logger.error(f"PDF metin çıkarma hatası: {e}")
            return ""

    def _extract_header_info(self, text: str) -> Dict:
        """
        SGK belgesinin header kısmından kişi bilgilerini çıkar.
        """
        info = {}

        # Ad Soyad (stop at next label or newline)
        ad_soyad_match = re.search(r'Ad\s+Soyad\s*[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)(?:\s*\n|\s*Sicil|\s*T\.?C\.?|\s*Kimlik|$)', text, re.IGNORECASE | re.MULTILINE)
        if ad_soyad_match:
            ad_soyad = ad_soyad_match.group(1).strip()
            # En az 3 karakter ve sadece harf+boşluk içermeli
            if len(ad_soyad) >= 3 and re.match(r'^[A-ZÇĞİÖŞÜa-zçğıöşü\s]+$', ad_soyad):
                info['ad_soyad'] = ad_soyad.upper()

        # TC Kimlik No
        tc_match = re.search(r'T\.?C\.?\s*Kimlik\s*No\s*[:\-]?\s*(\d{11})', text, re.IGNORECASE)
        if tc_match:
            info['tc_kimlik_no'] = tc_match.group(1)

        # İlk İşe Giriş Tarihi
        ilk_giris_match = re.search(r'İlk\s+İşe\s+Giriş\s+Tarihi\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})', text, re.IGNORECASE)
        if ilk_giris_match:
            info['ilk_ise_giris_tarihi'] = ilk_giris_match.group(1)

        # Son İşten Çıkış Tarihi
        son_cikis_match = re.search(r'Son\s+İşten\s+Çıkış\s+Tarihi\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})', text, re.IGNORECASE)
        if son_cikis_match:
            info['son_cikis_tarihi'] = son_cikis_match.group(1)

        # Toplam Prim Gün Sayısı
        prim_gun_match = re.search(r'Toplam\s+(?:Prim\s+)?(?:Gün\s+)?(?:Sayısı)?\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
        if prim_gun_match:
            info['toplam_prim_gun'] = int(prim_gun_match.group(1))

        return info

    def _extract_table_rows(self, text: str) -> List[Dict]:
        """
        SGK tablosundan satırları parse et.

        Tablo formatı:
        4a 2016/03 2012045271701 1005766 15.03.2016 30 Gıda Lab Elemanı
        """
        rows = []

        # Pattern: Sigorta kolu, Dönem, Sicil No, İşyeri No, Giriş, Gün, Çıkış (optional), Meslek
        # Örnek: "4a 2016/03 2012045271701 1005766 15.03.2016 30 15.11.2016 245 Gıda Lab Elemanı"
        # Örnek: "(4a) 2019/01 ... " (parantezli olanlar)
        # Örnek: "*4a 2012/07 ..." (yıldızlı olanlar - staj)

        pattern = r'(\*?\(?\*?\)?4[ab])\s+(\d{4}/\d{2})\s+(\d+)\s+(\d+)\s+(\d{2}\.\d{2}\.\d{4})?\s+(\d+)\s+(\d{2}\.\d{2}\.\d{4})?\s*(.*?)(?=\n|$)'

        for match in re.finditer(pattern, text, re.MULTILINE):
            sig_kolu_raw, donem, sicil, isyeri, giris, gun, cikis, meslek = match.groups()

            # Sigorta kolunu temizle
            sig_kolu = sig_kolu_raw.replace('(', '').replace(')', '').replace('*', '').strip()

            # Staj kontrolü
            is_staj = '*' in sig_kolu_raw or 'staj' in meslek.lower()

            rows.append({
                'sigorta_kolu': sig_kolu,
                'donem': donem,
                'sicil_no': sicil,
                'isyeri_no': isyeri,
                'giris_tarihi': giris if giris else None,
                'gun': int(gun) if gun else 0,
                'cikis_tarihi': cikis if cikis else None,
                'meslek': meslek.strip(),
                'is_staj': is_staj
            })

        return rows

    def _extract_isyeri_list(self, text: str) -> List[Dict]:
        """
        SGK belgesinin sonundaki işyeri listesini parse et.

        Format:
        1005766 GÜLEN DANIŞMANLIK ÇEVRE BİLİMLERİ MÜHENDİSLİK...
        """
        isyerleri = []

        # İşyeri listesi genellikle "İşyeri Listesi" başlığından sonra gelir
        isyeri_section_match = re.search(r'İşyeri\s+Listesi.*?(?=\n\n|$)', text, re.IGNORECASE | re.DOTALL)

        if isyeri_section_match:
            section_text = isyeri_section_match.group(0)

            # Pattern: İşyeri No + İşyeri Unvanı
            pattern = r'(\d{6,7})\s+([A-ZÇĞİÖŞÜ\s\.\-]+)'

            for match in re.finditer(pattern, section_text):
                isyeri_no, unvan = match.groups()
                isyerleri.append({
                    'isyeri_no': isyeri_no,
                    'unvan': unvan.strip()
                })

        return isyerleri

    def _calculate_experience(self, rows: List[Dict]) -> Dict:
        """
        Toplam deneyimi hesapla.

        Kurallar:
        - Stajlar dahil edilmez
        - 4a (çalışan) ve 4b (bağımsız) ayrı hesaplanır
        - SGK hesabı: 1 yıl = 360 gün, 1 ay = 30 gün
        """
        total_days_4a = 0  # 4A (çalışan)
        total_days_4b = 0  # 4B (bağımsız)
        staj_days = 0

        for row in rows:
            gun = row['gun']
            is_staj = row['is_staj']
            sig_kolu = row['sigorta_kolu']

            # Stajları ayır
            if is_staj:
                staj_days += gun
                continue

            # 4A / 4B ayrımı
            if sig_kolu == '4a':
                total_days_4a += gun
            elif sig_kolu == '4b':
                total_days_4b += gun

        # Yıl/ay hesapla
        y4a, m4a = self._days_to_years_months(total_days_4a)
        y4b, m4b = self._days_to_years_months(total_days_4b)

        # Toplam
        total_years = y4a + y4b
        total_months = m4a + m4b

        # Ay overflow kontrolü (12+ ay varsa yıla çevir)
        if total_months >= 12:
            total_years += total_months // 12
            total_months = total_months % 12

        return {
            'toplam_is_deneyimi_yil': total_years,
            'toplam_is_deneyimi_ay': total_months,
            'deneyim_4a_yil': y4a,
            'deneyim_4a_ay': m4a,
            'deneyim_4b_yil': y4b,
            'deneyim_4b_ay': m4b,
            'toplam_gun_4a': total_days_4a,
            'toplam_gun_4b': total_days_4b,
            'toplam_gun': total_days_4a + total_days_4b,
            'staj_gun': staj_days,
            'hizmet_eksigi_gun': 0,  # TODO: Hesaplanabilir
            'hizmet_fazlasi_gun': 0
        }

    def _days_to_years_months(self, days: int) -> Tuple[int, int]:
        """
        SGK gün sayısını yıl/ay'a çevir.

        SGK kuralı: 1 yıl = 360 gün, 1 ay = 30 gün
        """
        years = days // self.SGK_DAYS_PER_YEAR
        remaining_days = days % self.SGK_DAYS_PER_YEAR
        months = remaining_days // self.SGK_DAYS_PER_MONTH

        return years, months
