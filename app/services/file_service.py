"""
Base64 dosya dönüşüm servisi
"""
import base64
import os
import logging
from pathlib import Path
from typing import Optional, Tuple
import tempfile

logger = logging.getLogger(__name__)


class FileService:
    """Base64 ve dosya işlemleri servisi"""

    def __init__(self, temp_dir: str = "./temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def base64_to_file(
        self,
        base64_data: str,
        file_name: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[Path, bytes]:
        """
        Base64 string'i dosyaya dönüştürür

        Args:
            base64_data: Base64 encoded string
            file_name: Dosya adı
            output_dir: Çıktı dizini (None ise temp_dir kullanılır)

        Returns:
            (file_path, binary_data)
        """
        try:
            # Base64 decode
            binary_data = base64.b64decode(base64_data)
            logger.info(f"Base64 decoded: {len(binary_data)} bytes")

            # Dosya yolu
            if output_dir is None:
                output_dir = self.temp_dir

            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / file_name

            # Dosyaya yaz
            with open(file_path, 'wb') as f:
                f.write(binary_data)

            logger.info(f"Dosya kaydedildi: {file_path}")
            return file_path, binary_data

        except Exception as e:
            logger.error(f"Base64 dönüşüm hatası: {str(e)}")
            raise

    def get_file_extension(self, file_name: str) -> str:
        """Dosya uzantısını döndürür"""
        return Path(file_name).suffix.lower()

    def is_pdf(self, file_name: str) -> bool:
        """PDF dosyası mı kontrol eder"""
        return self.get_file_extension(file_name) == '.pdf'

    def is_docx(self, file_name: str) -> bool:
        """DOCX dosyası mı kontrol eder"""
        return self.get_file_extension(file_name) in ['.docx', '.doc']

    def is_image(self, file_name: str) -> bool:
        """Resim dosyası mı kontrol eder"""
        return self.get_file_extension(file_name) in ['.jpg', '.jpeg', '.png', '.bmp']

    def cleanup_temp_files(self, file_path: Path) -> None:
        """Geçici dosyayı siler"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Geçici dosya silindi: {file_path}")
        except Exception as e:
            logger.warning(f"Dosya silme hatası: {str(e)}")

    def cleanup_temp_dir(self) -> None:
        """Tüm geçici dosyaları temizler"""
        try:
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file():
                    file_path.unlink()
            logger.info(f"Geçici dizin temizlendi: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Dizin temizleme hatası: {str(e)}")
