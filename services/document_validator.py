"""
Document Validator
Belge varlık ve format kontrolü.
"""

import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentValidator:
    """
    Belge varlık ve format kontrolü.
    """

    # Maksimum dosya boyutları (bytes)
    MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
    MIN_PHOTO_SIZE = 10 * 1024  # 10 KB

    def validate_photo(self, photo_bytes: bytes, belge_adi: str) -> Dict[str, Any]:
        """
        Fotoğraf doğrulaması.

        Args:
            photo_bytes: Fotoğraf binary data
            belge_adi: Dosya adı

        Returns:
            Dict: Validation sonucu
        """
        errors = []
        warnings = []

        # 1. Boyut kontrolü
        size_bytes = len(photo_bytes)
        size_kb = size_bytes / 1024

        if size_bytes < self.MIN_PHOTO_SIZE:
            errors.append(f"Dosya cok kucuk (< 10 KB): {size_kb:.1f} KB")
        elif size_bytes > self.MAX_PHOTO_SIZE:
            errors.append(f"Dosya cok buyuk (> 5 MB): {size_kb / 1024:.1f} MB")

        # 2. MIME type kontrolü (magic number ile)
        mime_type = self._detect_mime_type(photo_bytes)

        if not mime_type.startswith('image/'):
            errors.append(f"Dosya bir resim degil (MIME: {mime_type})")
        elif mime_type not in ['image/jpeg', 'image/png', 'image/jpg']:
            warnings.append(f"Desteklenen format degil (tercih: JPEG/PNG, mevcut: {mime_type})")

        # 3. Dosya uzantısı kontrolü
        file_ext = Path(belge_adi).suffix.lower()
        if file_ext not in ['.jpg', '.jpeg', '.png']:
            warnings.append(f"Desteklenmeyen uzanti: {file_ext}")

        # 4. PIL ile image validation (opsiyonel - hata verirse skip)
        image_check = self._check_with_pil(photo_bytes)
        if image_check.get('error'):
            errors.append(image_check['error'])
        elif image_check.get('warning'):
            warnings.append(image_check['warning'])

        # Sonuç
        is_valid = len(errors) == 0

        return {
            'valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'size_kb': size_kb,
            'mime_type': mime_type,
            'file_ext': file_ext,
            'message': 'Fotograf gecerli' if is_valid else f"{len(errors)} hata tespit edildi"
        }

    def _detect_mime_type(self, data: bytes) -> str:
        """
        Magic number ile MIME type tespit et.
        """
        if len(data) < 12:
            return 'unknown'

        # JPEG
        if data[:2] == b'\xff\xd8':
            return 'image/jpeg'

        # PNG
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'

        # GIF
        if data[:6] in [b'GIF87a', b'GIF89a']:
            return 'image/gif'

        # BMP
        if data[:2] == b'BM':
            return 'image/bmp'

        # TIFF
        if data[:4] in [b'II*\x00', b'MM\x00*']:
            return 'image/tiff'

        # PDF
        if data[:5] == b'%PDF-':
            return 'application/pdf'

        return 'unknown'

    def _check_with_pil(self, data: bytes) -> Dict[str, Any]:
        """
        PIL/Pillow ile resim kontrolü (opsiyonel).
        """
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(data))
            img.verify()

            # Yeniden aç (verify sonrası kapalı)
            img = Image.open(io.BytesIO(data))

            # Boyut kontrolü
            width, height = img.size
            if width < 200 or height < 200:
                return {'warning': f"Cozunurluk dusuk ({width}x{height})"}

            return {'success': True, 'width': width, 'height': height}

        except ImportError:
            # PIL yüklü değil, skip
            logger.debug("PIL/Pillow kurulu degil, image validation atlanıyor")
            return {}

        except Exception as e:
            return {'error': f"Resim acilamadi: {str(e)}"}
