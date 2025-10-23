"""
Global konfigürasyon ayarları.
Environment variable'lardan veya default değerlerden yüklenir.
"""

import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# =============================================================================
# PROJE YOLLARI
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
PROMPTS_DIR = BASE_DIR / "prompts"
IMPORT_DIR = BASE_DIR / "data" / "imports"
EXPORT_DIR = BASE_DIR / "data" / "exports"
TEMP_DIR = BASE_DIR / "temp"

# Klasörleri oluştur
for directory in [DATABASE_DIR, LOG_DIR, IMPORT_DIR, EXPORT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# =============================================================================
# VERİTABANI AYARLARI
# =============================================================================
DATABASE_PATH = DATABASE_DIR / "basvurular.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLite pragma ayarları
SQLITE_PRAGMAS = {
    "foreign_keys": 1,
    "journal_mode": "WAL",
    "synchronous": "NORMAL",
    "cache_size": -1024 * 64,  # 64MB cache
    "temp_store": "MEMORY",
    "mmap_size": 1024 * 1024 * 128,  # 128MB mmap
}

# =============================================================================
# OLLAMA AYARLARI
# =============================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_API_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))  # saniye
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
OLLAMA_RETRY_DELAY = int(os.getenv("OLLAMA_RETRY_DELAY", "5"))  # saniye

# Ollama request parametreleri
OLLAMA_OPTIONS = {
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.1")),  # Düşük: daha deterministik
    "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
    "top_k": int(os.getenv("OLLAMA_TOP_K", "40")),
    "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "2048")),  # Max token
    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),  # Context window
}

# =============================================================================
# CHUNK AYARLARI
# =============================================================================
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "4000"))  # karakter
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # karakter
MIN_CHUNK_SIZE = 500  # Minimum chunk boyutu
MAX_CHUNK_SIZE = 8000  # Maximum chunk boyutu

# Token tahmini (yaklaşık)
CHARS_PER_TOKEN = 4  # İngilizce için ~4, Türkçe için ~3-4

# =============================================================================
# HİZMET TİPLERİ VE BELGE MATRİSİ
# =============================================================================
HIZMET_IDS: List[str] = [
    "10307",  # Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)
    "10308",  # Sanayide Yeşil Dönüşüm Sorumlusu (Eski Bakanlık Personeli)
    "10309",  # Sanayide Yeşil Dönüşüm Sorumlusu (Sektör Çalışanı)
    "10310",  # Sanayide Yeşil Dönüşüm Baş Sorumlusu (Akademisyen)
    "10311",  # Sanayide Yeşil Dönüşüm Baş Sorumlusu (Eski Bakanlık Personeli)
    "10312",  # Sanayide Yeşil Dönüşüm Baş Sorumlusu (Sektör Çalışanı)
]

# Hizmet tipi kodlama
HIZMET_KATEGORILERI = {
    "akademisyen": ["10307", "10310"],
    "eski_bakanlik": ["10308", "10311"],
    "sektor_calisani": ["10309", "10312"],
}

HIZMET_UNVANLARI = {
    "sorumlu": ["10307", "10308", "10309"],
    "bas_sorumlu": ["10310", "10311", "10312"],
}

# =============================================================================
# BELGE TİPLERİ
# =============================================================================
BELGE_TIPLERI_GENEL = [
    "Yök Lisans Diploması",
    "SGK Hizmet Dökümü",
    "Adli Sicil Kaydı",
    "Hitap Hizmet Dökümü",
    "Özgeçmiş/CV",
    "Fotoğraf (vesikalık)",
]

BELGE_TIPLERI_PROJE = [
    "Proje Dosyası (1)",
    "Proje Dosyası (2)",
    "Proje Dosyası (3)",
]

BELGE_TIPLERI_SEKTOR = [
    "Enerji Üretimi",
    "Metal Üretimi ve İşlemesi",
    "Mineral Endüstrisi",
    "Kimya Endüstrisi",
    "Atık Yönetimi",
    "Diğer Üretim Faaliyetleri",
]

BELGE_TIPLERI_DIGER = [
    "Üst Yazı",  # belgeTipi=null olan belgeler
]

TUM_BELGE_TIPLERI = (
    BELGE_TIPLERI_GENEL +
    BELGE_TIPLERI_PROJE +
    BELGE_TIPLERI_SEKTOR +
    BELGE_TIPLERI_DIGER
)

# =============================================================================
# SEKTÖR TANIMLARI
# =============================================================================
SEKTOR_ISIMLERI = [
    "Enerji",
    "Metal",
    "Mineral",
    "Kimya",
    "Atık",
    "Diğer",
]

# Belge tipi -> Sektör mapping
BELGE_SEKTOR_MAP = {
    "Enerji Üretimi": "Enerji",
    "Metal Üretimi ve İşlemesi": "Metal",
    "Mineral Endüstrisi": "Mineral",
    "Kimya Endüstrisi": "Kimya",
    "Atık Yönetimi": "Atık",
    "Diğer Üretim Faaliyetleri": "Diğer",
}

# =============================================================================
# DOSYA İŞLEME AYARLARI
# =============================================================================
# Desteklenen dosya uzantıları
SUPPORTED_EXTENSIONS = {
    "pdf": [".pdf"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
    "document": [".doc", ".docx"],
}

# Base64 decode buffer boyutu
BASE64_DECODE_BUFFER_SIZE = 1024 * 1024  # 1MB

# Maximum dosya boyutu (bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# =============================================================================
# LOGLAMA AYARLARI
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_FILES = {
    "app": LOG_DIR / "app.log",
    "error": LOG_DIR / "error.log",
    "ollama": LOG_DIR / "ollama.log",
    "database": LOG_DIR / "database.log",
}

# Log rotation
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# =============================================================================
# İŞLEM AYARLARI
# =============================================================================
# Paralel işlem
ENABLE_PARALLEL = os.getenv("ENABLE_PARALLEL", "false").lower() == "true"
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# Batch processing
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))

# Progress bar
SHOW_PROGRESS = os.getenv("SHOW_PROGRESS", "true").lower() == "true"

# =============================================================================
# VALİDASYON KURALLARI
# =============================================================================
# TC Kimlik No validation
VALIDATE_TC_NO = True
TC_NO_LENGTH = 11

# Tarih validation
MIN_YEAR = 1950
MAX_YEAR = 2030

# İş deneyimi validation
MIN_EXPERIENCE_YEARS = 0
MAX_EXPERIENCE_YEARS = 50

# Mezuniyet validation
MIN_GRADUATION_YEAR = 1970
MAX_GRADUATION_YEAR = 2030

# =============================================================================
# HATA YÖNETİMİ
# =============================================================================
# Retry stratejisi
RETRY_STRATEGY = {
    "max_attempts": OLLAMA_MAX_RETRIES,
    "wait_exponential_multiplier": 1000,  # 1 saniye
    "wait_exponential_max": 10000,  # 10 saniye
    "retry_on_exceptions": (
        ConnectionError,
        TimeoutError,
        Exception,
    ),
}

# Hata mesajları
ERROR_MESSAGES = {
    "ollama_connection": "Ollama sunucusuna bağlanılamadı: {url}",
    "ollama_timeout": "Ollama API timeout: {timeout}s aşıldı",
    "invalid_json": "Geçersiz JSON formatı: {error}",
    "missing_field": "Zorunlu alan eksik: {field}",
    "invalid_belge_tipi": "Geçersiz belge tipi: {tip}",
    "file_not_found": "Dosya bulunamadı: {path}",
    "database_error": "Veritabanı hatası: {error}",
}

# =============================================================================
# DEBUGGİNG
# =============================================================================
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
SAVE_RAW_RESPONSES = DEBUG  # Ollama raw response'larını kaydet
VERBOSE_LOGGING = DEBUG

# =============================================================================
# PERFORMANS OPTİMİZASYONU
# =============================================================================
# Cache ayarları
ENABLE_CACHE = True
CACHE_SIZE = 100  # LRU cache size

# Database connection pool
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10

# =============================================================================
# PROMPT AYARLARI
# =============================================================================
PROMPT_CONFIG = {
    "output_format": "json",
    "include_confidence": True,
    "include_sources": True,
    "strict_mode": True,
    "language": "tr",
}

# =============================================================================
# EXPORT AYARLARI
# =============================================================================
EXPORT_FORMATS = ["json", "csv", "xlsx", "pdf"]
DEFAULT_EXPORT_FORMAT = "json"

# Excel export ayarları
EXCEL_SHEET_NAME = "Başvuru Analiz Sonuçları"
EXCEL_INCLUDE_CHARTS = True

# =============================================================================
# API ENDPOINT (Gelecekte REST API için)
# =============================================================================
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_PREFIX = "/api/v1"

# =============================================================================
# GÜVENLİK
# =============================================================================
# API key (eğer Ollama secured ise)
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", None)

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT", "60"))

# =============================================================================
# FONKSİYONLAR
# =============================================================================
def print_config():
    """Mevcut konfigürasyonu yazdır (debug için)"""
    import json
    config_dict = {
        "OLLAMA_BASE_URL": OLLAMA_BASE_URL,
        "OLLAMA_MODEL": OLLAMA_MODEL,
        "CHUNK_SIZE": CHUNK_SIZE,
        "DATABASE_PATH": str(DATABASE_PATH),
        "LOG_LEVEL": LOG_LEVEL,
        "DEBUG": DEBUG,
    }
    print(json.dumps(config_dict, indent=2, ensure_ascii=False))


def validate_config():
    """Konfigürasyonun geçerli olduğunu kontrol et"""
    errors = []

    # Ollama URL kontrolü
    if not OLLAMA_BASE_URL:
        errors.append("OLLAMA_BASE_URL tanımlanmamış")

    # Chunk ayarları kontrolü
    if CHUNK_SIZE < MIN_CHUNK_SIZE:
        errors.append(f"CHUNK_SIZE çok küçük: {CHUNK_SIZE} < {MIN_CHUNK_SIZE}")

    if CHUNK_SIZE > MAX_CHUNK_SIZE:
        errors.append(f"CHUNK_SIZE çok büyük: {CHUNK_SIZE} > {MAX_CHUNK_SIZE}")

    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append(f"CHUNK_OVERLAP >= CHUNK_SIZE: {CHUNK_OVERLAP} >= {CHUNK_SIZE}")

    if errors:
        raise ValueError(f"Konfigürasyon hataları:\n" + "\n".join(errors))


# Modül import edildiğinde config'i validate et
if os.getenv("SKIP_CONFIG_VALIDATION", "false").lower() != "true":
    try:
        validate_config()
    except ValueError as e:
        print(f"[UYARI] {e}")
