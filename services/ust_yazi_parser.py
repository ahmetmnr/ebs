"""
Üst Yazı/Dilekçe Parser
Ground truth bilgileri ve belge listesini çıkarır.
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UstYaziParser:
    """
    Üst yazı/dilekçe belgesinden ground truth bilgileri çıkarır.
    """

    def parse_ust_yazi(self, text: str) -> Dict:
        """
        Üst yazıdan kişisel bilgileri ve belge listesini çıkar.

        Returns:
            Dict: Ground truth data
        """
        try:
            # 1. Kişisel bilgiler (Ground Truth)
            personal_info = self._extract_personal_info(text)

            # 2. Belge listesi
            document_list = self._extract_document_list(text)

            # 3. Başvuru bilgileri
            application_info = self._extract_application_info(text)

            result = {
                'ad_soyad': personal_info.get('ad_soyad'),
                'tc_kimlik_no': personal_info.get('tc'),
                'adres': personal_info.get('adres'),
                'email': personal_info.get('email'),
                'gsm': personal_info.get('gsm'),
                'basvuru_tarihi': application_info.get('tarih'),
                'basvuru_hizmet': application_info.get('hizmet'),
                'belge_listesi': [d['dosya_adi'] for d in document_list],
                'belge_listesi_detay': document_list,
                'toplam_belge_sayisi': len(document_list)
            }

            logger.info(f"✓ Üst yazı parse edildi: {result['ad_soyad']} ({result['tc_kimlik_no']}), {result['toplam_belge_sayisi']} belge")

            return result

        except Exception as e:
            logger.error(f"Üst yazı parse hatası: {e}", exc_info=True)
            return {}

    def _extract_personal_info(self, text: str) -> Dict:
        """
        Kişisel bilgileri regex ile çıkar.
        """
        info = {}

        # Ad Soyad (birçok farklı format olabilir)
        patterns = [
            r'Başvuru\s+Yapan\s*[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)(?:\s*\n|\s*T\.?C\.?|\s*Kimlik|\s*Adres|\s*GSM|$)',
            r'Ad\s*Soyad\s*[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)(?:\s*\n|\s*T\.?C\.?|\s*Kimlik|\s*Adres|\s*GSM|$)',
            r'Adı\s*Soyadı\s*[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)(?:\s*\n|\s*T\.?C\.?|\s*Kimlik|\s*Adres|\s*GSM|$)',
            r'Ad\s*[:]\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]+?)(?:\s*\n|\s*Soyad|\s*T\.?C\.?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                ad_soyad = match.group(1).strip()
                # En az 2 kelime olmalı (ad ve soyad), sadece harf ve boşluk
                if len(ad_soyad) >= 3 and re.match(r'^[A-ZÇĞİÖŞÜa-zçğıöşü\s]+$', ad_soyad):
                    # Büyük harfe çevir
                    info['ad_soyad'] = ad_soyad.upper()
                    break

        # TC Kimlik No
        tc_patterns = [
            r'T\.?C\.?\s*Kimlik\s*(?:No|Numarası)\s*[:\-]?\s*(\d{11})',
            r'TC\s*[:\-]?\s*(\d{11})',
            r'Kimlik\s*No\s*[:\-]?\s*(\d{11})'
        ]

        for pattern in tc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['tc'] = match.group(1)
                break

        # Adres (birden fazla satır olabilir)
        adres_patterns = [
            r'Adres\s*[:\-]?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:E-?Mail|GSM|Telefon|Tarih|\d|$))',
            r'İkamet\s+Adresi\s*[:\-]?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*(?:E-?Mail|GSM|Telefon|Tarih|\d|$))',
        ]

        for pattern in adres_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Birden fazla satırı birleştir, gereksiz boşlukları temizle
                adres = ' '.join(match.group(1).strip().split())
                info['adres'] = adres
                break

        # Email
        email_patterns = [
            r'E-?Mail\s*[:\-]?\s*([^\s\n]+@[^\s\n]+)',
            r'E-?Posta\s*[:\-]?\s*([^\s\n]+@[^\s\n]+)',
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]

        for pattern in email_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['email'] = match.group(1).strip()
                break

        # GSM / Telefon
        gsm_patterns = [
            r'GSM\s*(?:No)?\s*[:\-]?\s*(\d{10,11})',
            r'Cep\s*(?:Tel|Telefon)?\s*[:\-]?\s*(\d{10,11})',
            r'Telefon\s*[:\-]?\s*(\d{10,11})'
        ]

        for pattern in gsm_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['gsm'] = match.group(1)
                break

        return info

    def _extract_document_list(self, text: str) -> List[Dict]:
        """
        Ek belgeler listesini çıkar.

        Format örnekleri:
        1-Yök Lisans Diploması-Diploma LisansOnlisans.pdf (*)
        2-SGK Hizmet Dökümü-SGK Hizmet Dokumu.pdf (*)
        1. Diploma LisansOnlisans.pdf
        """
        documents = []

        # Pattern 1: "1-Belge Tipi-dosya.pdf (*)"
        pattern1 = r'(\d+)\s*[\-\.]\s*([^\-\n]+?)\s*[\-]\s*([^\n]+?\.(?:pdf|jpg|jpeg|png|doc|docx))\s*\(\*\)'

        for match in re.finditer(pattern1, text, re.IGNORECASE):
            sira, belge_tipi, dosya_adi = match.groups()

            documents.append({
                'sira_no': int(sira),
                'belge_tipi': belge_tipi.strip(),
                'dosya_adi': dosya_adi.strip()
            })

        # Pattern 2: "1. dosya.pdf" (basit format)
        if not documents:
            pattern2 = r'(\d+)\s*[\.\)]\s*([^\n]+?\.(?:pdf|jpg|jpeg|png|doc|docx))'

            for match in re.finditer(pattern2, text, re.IGNORECASE):
                sira, dosya_adi = match.groups()

                documents.append({
                    'sira_no': int(sira),
                    'belge_tipi': None,  # Belirtilmemiş
                    'dosya_adi': dosya_adi.strip()
                })

        # Pattern 3: Dilekçe metni (ayrı satır)
        dilekce_match = re.search(r'(\d+)\s*[\-\.]\s*(Dilekçe(?:\s+Metni)?)', text, re.IGNORECASE)
        if dilekce_match:
            sira = int(dilekce_match.group(1))
            documents.append({
                'sira_no': sira,
                'belge_tipi': 'Dilekçe Metni',
                'dosya_adi': 'dilekce.txt'  # Sanal dosya adı
            })

        # Sıra numarasına göre sırala
        documents.sort(key=lambda x: x['sira_no'])

        return documents

    def _extract_application_info(self, text: str) -> Dict:
        """
        Başvuru bilgilerini çıkar.
        """
        info = {}

        # Tarih
        tarih_patterns = [
            r'Tarih\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})',
            r'Tarih\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})',
            r'Başvuru\s+Tarihi\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})'
        ]

        for pattern in tarih_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['tarih'] = match.group(1)
                break

        # Hizmet / Konu
        hizmet_patterns = [
            r'Konu\s*[:\-]?\s*([^\n]+)',
            r'Başvuru\s+Konusu\s*[:\-]?\s*([^\n]+)',
            r'Hizmet\s*[:\-]?\s*([^\n]+)'
        ]

        for pattern in hizmet_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hizmet = match.group(1).strip()
                # Çok uzun değilse (max 200 karakter)
                if len(hizmet) < 200:
                    info['hizmet'] = hizmet
                    break

        return info
