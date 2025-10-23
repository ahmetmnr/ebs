"""
Belge işleme servisi.
PDF, görsel ve diğer belge formatlarını işler.
"""

import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import io

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logging.warning("Pillow yüklü değil, görsel işleme devre dışı")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logging.warning("pdfplumber yüklü değil, PDF işleme sınırlı")

from config.settings import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Belge işleme servisi"""

    @staticmethod
    def decode_base64(base64_string: str) -> Optional[bytes]:
        """
        Base64 string'i decode et.

        Args:
            base64_string: Base64 encoded string

        Returns:
            bytes: Decode edilmiş veri, başarısızsa None
        """
        try:
            # Base64 padding düzelt
            missing_padding = len(base64_string) % 4
            if missing_padding:
                base64_string += '=' * (4 - missing_padding)

            decoded = base64.b64decode(base64_string)

            # Boyut kontrolü
            if len(decoded) > MAX_FILE_SIZE:
                logger.warning(f"Dosya çok büyük: {len(decoded)} bytes")
                return None

            return decoded

        except Exception as e:
            logger.error(f"Base64 decode hatası: {e}")
            return None

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes, use_ocr: bool = True) -> Optional[str]:
        """
        PDF'den metin çıkar. Metin yoksa OCR kullan.

        Args:
            pdf_bytes: PDF dosya bytes'ı
            use_ocr: Metin yoksa OCR kullan mı?

        Returns:
            str: Çıkarılan metin, başarısızsa None
        """
        if not PDFPLUMBER_AVAILABLE:
            logger.error("pdfplumber yüklü değil")
            # OCR ile denemeye devam et
            if use_ocr:
                logger.info("pdfplumber olmadan OCR denenecek")
                return DocumentProcessor._extract_text_with_ocr_from_bytes(pdf_bytes)
            return None

        text_parts = []
        ocr_needed_pages = []
        page_count = 0

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)

                # PDF'in sayfa sayısını kontrol et
                if page_count == 0:
                    logger.warning("PDF'de sayfa bulunamadı (0 sayfa)")
                    # OCR ile tüm PDF'i işle
                    if use_ocr:
                        logger.info("0 sayfalı PDF için OCR denenecek")
                        return DocumentProcessor._extract_text_with_ocr_from_bytes(pdf_bytes)
                    return None

                # Her sayfayı işle
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:  # En az 50 karakter varsa
                        text_parts.append(f"--- Sayfa {page_num} ---\n{text}")
                    else:
                        # Metin yok veya çok az - OCR gerekli
                        ocr_needed_pages.append((page_num, page))

            # OCR gerekiyorsa
            if ocr_needed_pages and use_ocr:
                logger.info(f"OCR gerekiyor: {len(ocr_needed_pages)} sayfa")
                ocr_text = DocumentProcessor._extract_text_with_ocr(ocr_needed_pages)
                if ocr_text:
                    text_parts.extend(ocr_text)

            full_text = '\n\n'.join(text_parts)

            logger.info(f"PDF'den {len(full_text)} karakter metin çıkarıldı ({page_count} sayfa)")

            # Hiç metin çıkmadıysa ve OCR kullanılacaksa, tüm PDF'i OCR ile dene
            if not full_text.strip() and use_ocr:
                logger.warning("PDF'den hiç metin çıkarılamadı, tüm PDF OCR ile işlenecek")
                return DocumentProcessor._extract_text_with_ocr_from_bytes(pdf_bytes)

            return full_text if full_text.strip() else None

        except Exception as e:
            logger.error(f"PDF açma/işleme hatası: {e}")
            # PDF açılamadıysa veya hata olduysa, OCR ile denemeye devam et
            if use_ocr:
                logger.info("PDF işlenemedi, OCR ile deneniyor")
                return DocumentProcessor._extract_text_with_ocr_from_bytes(pdf_bytes)
            return None

    @staticmethod
    def _extract_text_with_ocr(pages_list) -> list:
        """
        OCR ile PDF sayfalarından metin çıkar.

        Args:
            pages_list: [(page_num, page), ...] listesi

        Returns:
            list: Metin listesi
        """
        try:
            import easyocr
            import numpy as np
            from PIL import Image
        except ImportError:
            logger.warning("OCR için easyocr veya Pillow yüklü değil")
            return []

        # EasyOCR reader'ı oluştur (singleton pattern - tek seferlik)
        if not hasattr(DocumentProcessor, '_easyocr_reader'):
            logger.info("EasyOCR reader başlatılıyor (Türkçe + İngilizce)...")
            DocumentProcessor._easyocr_reader = easyocr.Reader(['tr', 'en'], gpu=False)

        reader = DocumentProcessor._easyocr_reader
        ocr_texts = []

        for page_num, page in pages_list:
            try:
                # PDF sayfasını görsel olarak render et
                pil_image = page.to_image(resolution=300).original

                # PIL Image'i numpy array'e çevir (EasyOCR için gerekli)
                image_array = np.array(pil_image)

                # OCR uygula
                result = reader.readtext(image_array)

                # Sonuçları birleştir
                ocr_text = '\n'.join([detection[1] for detection in result])

                if ocr_text and len(ocr_text.strip()) > 20:
                    ocr_texts.append(f"--- Sayfa {page_num} (OCR) ---\n{ocr_text}")
                    logger.info(f"Sayfa {page_num}: OCR ile {len(ocr_text)} karakter çıkarıldı")
                else:
                    logger.warning(f"Sayfa {page_num}: OCR başarısız veya boş")

            except Exception as e:
                logger.error(f"Sayfa {page_num} OCR hatası: {e}")
                continue

        return ocr_texts

    @staticmethod
    def _extract_text_with_ocr_from_bytes(pdf_bytes: bytes) -> Optional[str]:
        """
        PDF bytes'ını görsel olarak render edip OCR uygula.
        PDF açılamadığında veya 0 sayfa olduğunda kullanılır.

        Args:
            pdf_bytes: PDF dosya bytes'ı

        Returns:
            str: OCR ile çıkarılan metin, başarısızsa None
        """
        try:
            import easyocr
            import numpy as np
            from PIL import Image
            from pdf2image import convert_from_bytes
        except ImportError:
            logger.error("OCR için easyocr, Pillow veya pdf2image yüklü değil")
            logger.info("pip install easyocr pillow pdf2image")
            return None

        try:
            logger.info("PDF'i görsele çevirip OCR yapılıyor...")

            # PDF'i görsellere çevir (300 DPI)
            images = convert_from_bytes(pdf_bytes, dpi=300)

            if not images:
                logger.error("PDF'den görsel çıkarılamadı")
                return None

            logger.info(f"{len(images)} görsel oluşturuldu, OCR uygulanıyor...")

            # EasyOCR reader'ı oluştur (singleton pattern)
            if not hasattr(DocumentProcessor, '_easyocr_reader'):
                logger.info("EasyOCR reader başlatılıyor (Türkçe + İngilizce)...")
                DocumentProcessor._easyocr_reader = easyocr.Reader(['tr', 'en'], gpu=False)

            reader = DocumentProcessor._easyocr_reader
            ocr_texts = []

            for page_num, image in enumerate(images, 1):
                try:
                    # PIL Image'i numpy array'e çevir
                    image_array = np.array(image)

                    # OCR uygula
                    result = reader.readtext(image_array)

                    # Sonuçları birleştir
                    ocr_text = '\n'.join([detection[1] for detection in result])

                    if ocr_text and len(ocr_text.strip()) > 20:
                        ocr_texts.append(f"--- Sayfa {page_num} (OCR-Full) ---\n{ocr_text}")
                        logger.info(f"Sayfa {page_num}: OCR ile {len(ocr_text)} karakter çıkarıldı")
                    else:
                        logger.warning(f"Sayfa {page_num}: OCR boş sonuç verdi")

                except Exception as e:
                    logger.error(f"Sayfa {page_num} OCR hatası: {e}")
                    continue

            full_text = '\n\n'.join(ocr_texts)

            if full_text.strip():
                logger.info(f"OCR tamamlandı: {len(full_text)} karakter çıkarıldı")
                return full_text
            else:
                logger.warning("OCR hiç metin çıkaramadı")
                return None

        except Exception as e:
            logger.error(f"PDF-to-Image OCR hatası: {e}")
            return None

    @staticmethod
    def process_image(image_bytes: bytes) -> Optional[str]:
        """
        Görsel dosyayı işle ve Base64'e çevir.

        Args:
            image_bytes: Görsel dosya bytes'ı

        Returns:
            str: Base64 encoded görsel, başarısızsa None
        """
        if not PILLOW_AVAILABLE:
            logger.error("Pillow yüklü değil")
            return None

        try:
            # Görseli yükle
            image = Image.open(io.BytesIO(image_bytes))

            # RGBA ise RGB'ye çevir
            if image.mode == 'RGBA':
                image = image.convert('RGB')

            # Boyut küçült (gereksiz büyük görsel varsa)
            max_dimension = 2000
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Base64'e çevir
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)

            encoded = base64.b64encode(buffer.read()).decode('utf-8')

            logger.info(f"Görsel işlendi: {image.size} -> Base64 ({len(encoded)} karakter)")

            return encoded

        except Exception as e:
            logger.error(f"Görsel işleme hatası: {e}")
            return None

    @staticmethod
    def detect_file_type(file_bytes: bytes) -> Optional[str]:
        """
        Dosya tipini tespit et (magic bytes).

        Args:
            file_bytes: Dosya bytes'ı

        Returns:
            str: Dosya tipi ('pdf', 'image', 'unknown')
        """
        if not file_bytes:
            return 'unknown'

        # PDF
        if file_bytes.startswith(b'%PDF'):
            return 'pdf'

        # JPEG
        if file_bytes.startswith(b'\xff\xd8\xff'):
            return 'image'

        # PNG
        if file_bytes.startswith(b'\x89PNG'):
            return 'image'

        # GIF
        if file_bytes.startswith(b'GIF'):
            return 'image'

        return 'unknown'

    @staticmethod
    def process_document(
        base64_content: str,
        file_extension: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Belgeyi işle (tip otomatik tespit).

        Args:
            base64_content: Base64 encoded belge
            file_extension: Dosya uzantısı (opsiyonel)

        Returns:
            Dict: {
                'type': 'pdf' | 'image' | 'unknown',
                'text': str (PDF ise),
                'image_base64': str (görsel ise),
                'success': bool,
                'error': str (hata varsa)
            }
        """
        result = {
            'type': 'unknown',
            'text': None,
            'image_base64': None,
            'success': False,
            'error': None,
        }

        try:
            # Decode
            file_bytes = DocumentProcessor.decode_base64(base64_content)
            if not file_bytes:
                result['error'] = 'Base64 decode başarısız'
                return result

            # Tip tespit
            file_type = DocumentProcessor.detect_file_type(file_bytes)

            if file_extension:
                # Extension'dan tip tahmin
                ext = file_extension.lower()
                if ext == '.pdf':
                    file_type = 'pdf'
                elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    file_type = 'image'

            result['type'] = file_type

            # PDF ise metin çıkar
            if file_type == 'pdf':
                text = DocumentProcessor.extract_text_from_pdf(file_bytes)
                if text:
                    result['text'] = text
                    result['success'] = True
                else:
                    result['error'] = 'PDF metin çıkarma başarısız'

            # Görsel ise işle
            elif file_type == 'image':
                image_b64 = DocumentProcessor.process_image(file_bytes)
                if image_b64:
                    result['image_base64'] = image_b64
                    result['success'] = True
                else:
                    result['error'] = 'Görsel işleme başarısız'

            else:
                result['error'] = f'Bilinmeyen dosya tipi: {file_type}'

            return result

        except Exception as e:
            logger.error(f"Belge işleme hatası: {e}")
            result['error'] = str(e)
            return result
