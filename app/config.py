"""
Uygulama konfigürasyonu
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Uygulama ayarları"""

    # App
    APP_NAME: str = "Belge İşleme Servisi"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Ollama LLM
    # EVDE ÇALIŞIRKEN: .env dosyasında local ayarları aktif et
    # İŞ YERİNDE: .env dosyasında llm.csb.gov.tr ayarlarını aktif et
    OLLAMA_BASE_URL: str = "llm.csb.gov.tr"  # Default - .env ile override edilir
    OLLAMA_MODEL: str = "gemma3:27b"  # Default - .env ile override edilir
    OLLAMA_TIMEOUT: int = 600  # 10 dakika - belgeler uzun olabilir

    # OCR
    OCR_LANGUAGES: list = ["tr", "en"]
    OCR_GPU: bool = False

    # External API (CSB eBasvuru)
    # Test API: https://test-ebasv-s.csb.gov.tr
    EXTERNAL_API_URL: str = "https://ebasvuru.csb.gov.tr/ebasvuruadminapi"
    EXTERNAL_API_USERNAME: Optional[str] = None
    EXTERNAL_API_PASSWORD: Optional[str] = None
    EXTERNAL_API_TIMEOUT: int = 3600  # 1 saat - timeout istemiyoruz

    # Scheduler
    POLL_INTERVAL_MINUTES: int = 15
    # SYD Hizmet ID'leri (Production: 10307-10312, Test: 10251-10256)
    HIZMET_IDS: list = ["10307", "10308", "10309", "10310", "10311", "10312"]  # Tüm canlı SYD hizmetleri

    # Processing
    MAX_FILE_SIZE_MB: int = 10
    TEMP_DIR: str = "./temp"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
