-- database.sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- =============================================================================
-- TABLO 1: BAŞVURULAR (JSON'dan direkt alınan bilgiler)
-- =============================================================================
CREATE TABLE IF NOT EXISTS basvurular (
    -- Primary Key
    basvuruId INTEGER PRIMARY KEY NOT NULL,

    -- JSON'dan gelen zorunlu alanlar
    takipNo TEXT NOT NULL,
    basvuruTarihi TEXT NOT NULL, -- ISO 8601 format: "2025-04-29T15:46:26.55+03:00"
    hizmetId TEXT NOT NULL CHECK(hizmetId IN ('10307', '10308', '10309', '10310', '10311', '10312')),
    hizmetAdi TEXT NOT NULL,
    basvuruYapanVatandasTC TEXT NOT NULL CHECK(length(basvuruYapanVatandasTC) = 11),
    basvuruYapanAd TEXT NOT NULL,
    basvuruYapanSoyad TEXT NOT NULL,
    basvuruDurum TEXT NOT NULL,
    kararDurum TEXT,

    -- Ham JSON saklama (debug ve audit için)
    json_ham TEXT NOT NULL,

    -- İşlem durumu takibi
    islendiMi INTEGER DEFAULT 0 CHECK(islendiMi IN (0, 1)), -- 0: İşlenmedi, 1: İşlendi
    islenme_baslangic TEXT, -- ISO 8601 datetime
    islenme_bitis TEXT, -- ISO 8601 datetime
    islenme_suresi_sn REAL, -- saniye cinsinden
    hata_mesaji TEXT,

    -- Metadata
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_basvurular_takipNo ON basvurular(takipNo);
CREATE INDEX IF NOT EXISTS idx_basvurular_hizmetId ON basvurular(hizmetId);
CREATE INDEX IF NOT EXISTS idx_basvurular_tc ON basvurular(basvuruYapanVatandasTC);
CREATE INDEX IF NOT EXISTS idx_basvurular_islendiMi ON basvurular(islendiMi);
CREATE INDEX IF NOT EXISTS idx_basvurular_basvuruTarihi ON basvurular(basvuruTarihi);

-- =============================================================================
-- TABLO 2: BELGELER (JSON'daki basvuruBelgeListesi)
-- =============================================================================
CREATE TABLE IF NOT EXISTS belgeler (
    -- Primary Key
    belgeId INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Foreign Key
    basvuruId INTEGER NOT NULL,

    -- Belge bilgileri
    belgeAdi TEXT NOT NULL,
    belgeTipi TEXT, -- NULL olabilir, dosya adından tahmin edilecek
    belgeTipi_tahmini TEXT, -- Sistem tarafından tahmin edilen tip
    belgeIcerik TEXT NOT NULL, -- Base64 encoded string
    belge_boyutu_bytes INTEGER, -- Base64 decode edilmiş boyut
    belge_uzantisi TEXT, -- .pdf, .jpg, .jpeg, .png

    -- Analiz durumu
    analiz_edildi INTEGER DEFAULT 0 CHECK(analiz_edildi IN (0, 1)),
    analiz_baslangic TEXT, -- ISO 8601 datetime
    analiz_bitis TEXT, -- ISO 8601 datetime
    analiz_suresi_sn REAL,
    analiz_hata TEXT,

    -- Metadata
    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (basvuruId) REFERENCES basvurular(basvuruId) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_belgeler_basvuruId ON belgeler(basvuruId);
CREATE INDEX IF NOT EXISTS idx_belgeler_belgeTipi ON belgeler(belgeTipi);
CREATE INDEX IF NOT EXISTS idx_belgeler_analiz_edildi ON belgeler(analiz_edildi);

-- =============================================================================
-- TABLO 3: ANALİZ SONUÇLARI (Tüm belge analizlerinin birleştirilmiş sonucu)
-- =============================================================================
CREATE TABLE IF NOT EXISTS analiz_sonuclari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    basvuruId INTEGER NOT NULL UNIQUE,

    -- === SEKTÖR BAŞVURULARI (Boolean: 0 veya 1) ===
    sektor_enerji INTEGER DEFAULT 0 CHECK(sektor_enerji IN (0, 1)),
    sektor_metal INTEGER DEFAULT 0 CHECK(sektor_metal IN (0, 1)),
    sektor_mineral INTEGER DEFAULT 0 CHECK(sektor_mineral IN (0, 1)),
    sektor_kimya INTEGER DEFAULT 0 CHECK(sektor_kimya IN (0, 1)),
    sektor_atik INTEGER DEFAULT 0 CHECK(sektor_atik IN (0, 1)),
    sektor_diger INTEGER DEFAULT 0 CHECK(sektor_diger IN (0, 1)),

    -- === SEKTÖR TECRÜBELERİ (Yıl olarak, NULL olabilir) ===
    tecrube_enerji INTEGER CHECK(tecrube_enerji >= 0 OR tecrube_enerji IS NULL),
    tecrube_metal INTEGER CHECK(tecrube_metal >= 0 OR tecrube_metal IS NULL),
    tecrube_mineral INTEGER CHECK(tecrube_mineral >= 0 OR tecrube_mineral IS NULL),
    tecrube_kimya INTEGER CHECK(tecrube_kimya >= 0 OR tecrube_kimya IS NULL),
    tecrube_atik INTEGER CHECK(tecrube_atik >= 0 OR tecrube_atik IS NULL),
    tecrube_diger INTEGER CHECK(tecrube_diger >= 0 OR tecrube_diger IS NULL),

    -- === ADLİ SİCİL ===
    adli_sicil_varmi INTEGER CHECK(adli_sicil_varmi IN (0, 1, NULL)),
    adli_sicil_kodu TEXT,
    adli_sicil_aciklama TEXT, -- Belgedeki detaylı açıklama

    -- === DOKÜMAN VARLIĞI (Belge eklenmiş mi?) ===
    dokuman_enerji INTEGER DEFAULT 0 CHECK(dokuman_enerji IN (0, 1)),
    dokuman_metal INTEGER DEFAULT 0 CHECK(dokuman_metal IN (0, 1)),
    dokuman_mineral INTEGER DEFAULT 0 CHECK(dokuman_mineral IN (0, 1)),
    dokuman_kimya INTEGER DEFAULT 0 CHECK(dokuman_kimya IN (0, 1)),
    dokuman_atik INTEGER DEFAULT 0 CHECK(dokuman_atik IN (0, 1)),
    dokuman_diger INTEGER DEFAULT 0 CHECK(dokuman_diger IN (0, 1)),

    -- === MEZUNİYET BİLGİLERİ ===
    mezun_universite TEXT,
    mezun_bolum TEXT,
    mezuniyet_yili INTEGER CHECK(mezuniyet_yili >= 1950 AND mezuniyet_yili <= 2030 OR mezuniyet_yili IS NULL),
    egitim_seviyesi TEXT CHECK(egitim_seviyesi IN ('Lisans', 'Yüksek Lisans', 'Doktora', NULL)),

    -- === PROJE/YAYIN ===
    proje_yayin_sayisi INTEGER DEFAULT 0 CHECK(proje_yayin_sayisi >= 0),

    -- === İŞ DENEYİMİ (SGK'dan) ===
    toplam_is_deneyimi_yil INTEGER CHECK(toplam_is_deneyimi_yil >= 0 OR toplam_is_deneyimi_yil IS NULL),
    toplam_is_deneyimi_ay INTEGER CHECK(toplam_is_deneyimi_ay >= 0 AND toplam_is_deneyimi_ay <= 11 OR toplam_is_deneyimi_ay IS NULL),

    -- === VERİ KAYNAĞI İZLEME (Hangi belgeden geldi?) ===
    kaynak_cv INTEGER DEFAULT 0, -- CV'den bilgi alındı mı?
    kaynak_sgk INTEGER DEFAULT 0, -- SGK'dan bilgi alındı mı?
    kaynak_diploma INTEGER DEFAULT 0, -- Diplomadan bilgi alındı mı?
    kaynak_adli_sicil INTEGER DEFAULT 0, -- Adli sicilden bilgi alındı mı?
    kaynak_proje_dosyasi INTEGER DEFAULT 0, -- Proje dosyasından bilgi alındı mı?
    kaynak_sektor_belgeleri INTEGER DEFAULT 0, -- Sektör belgelerinden bilgi alındı mı?

    -- === UYUMLULUK KONTROL ===
    zorunlu_belgeler_tam INTEGER DEFAULT 0 CHECK(zorunlu_belgeler_tam IN (0, 1)), -- Tüm zorunlu belgeler var mı?
    eksik_belgeler TEXT, -- JSON array: ["Proje Dosyası (1)", "Hitap"]

    -- === METADATA ===
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (basvuruId) REFERENCES basvurular(basvuruId) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analiz_basvuruId ON analiz_sonuclari(basvuruId);

-- =============================================================================
-- TABLO 4: PROJE/YAYIN DETAYLARI (1-N ilişkisi)
-- =============================================================================
CREATE TABLE IF NOT EXISTS proje_yayinlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    basvuruId INTEGER NOT NULL,

    -- Proje bilgileri
    sira_no INTEGER NOT NULL CHECK(sira_no >= 1), -- 1, 2, 3, ...
    tur TEXT CHECK(tur IN ('Proje', 'Yayın', 'Bildiri', 'Patent', 'Diğer', NULL)),
    baslik TEXT,
    aciklama TEXT,
    yil INTEGER CHECK(yil >= 1950 AND yil <= 2030 OR yil IS NULL),
    kurum TEXT, -- TÜBİTAK, BAP, Horizon 2020, vb.
    butce REAL CHECK(butce >= 0 OR butce IS NULL), -- Proje bütçesi (TL)
    rol TEXT, -- Yürütücü, Araştırmacı, Danışman, vb.

    -- Belge kaynağı
    kaynak_belgeId INTEGER, -- Hangi belgeden çıkarıldı?

    -- Metadata
    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (basvuruId) REFERENCES basvurular(basvuruId) ON DELETE CASCADE,
    FOREIGN KEY (kaynak_belgeId) REFERENCES belgeler(belgeId) ON DELETE SET NULL,
    UNIQUE(basvuruId, sira_no) -- Her başvuruda sıra no tekil olmalı
);

CREATE INDEX IF NOT EXISTS idx_proje_basvuruId ON proje_yayinlar(basvuruId);
CREATE INDEX IF NOT EXISTS idx_proje_tur ON proje_yayinlar(tur);
CREATE INDEX IF NOT EXISTS idx_proje_yil ON proje_yayinlar(yil);

-- =============================================================================
-- TABLO 5: BELGE ANALİZ LOGLARI (Her belge için ayrı kayıt)
-- =============================================================================
CREATE TABLE IF NOT EXISTS belge_analiz_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    belgeId INTEGER NOT NULL,
    basvuruId INTEGER NOT NULL,

    -- Analiz detayları
    belgeTipi TEXT NOT NULL,
    chunk_sayisi INTEGER DEFAULT 1 CHECK(chunk_sayisi >= 1),
    chunk_size INTEGER, -- Karakter sayısı
    overlap_size INTEGER, -- Overlap karakter sayısı
    toplam_karakter INTEGER,
    toplam_token_tahmini INTEGER, -- token count tahmini

    -- Ollama detayları
    ollama_url TEXT NOT NULL,
    ollama_model TEXT NOT NULL,
    ollama_timeout_sn INTEGER DEFAULT 120,

    -- Sonuç
    basarili INTEGER NOT NULL CHECK(basarili IN (0, 1)),
    hata_mesaji TEXT,
    hata_kodu TEXT, -- timeout, connection_error, json_parse_error, vb.
    retry_sayisi INTEGER DEFAULT 0,

    -- Performans
    islem_baslangic TEXT NOT NULL,
    islem_bitis TEXT NOT NULL,
    islem_suresi_sn REAL NOT NULL,

    -- Ham response (debug için)
    ollama_response_ham TEXT, -- JSON string olarak sakla

    -- Metadata
    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (belgeId) REFERENCES belgeler(belgeId) ON DELETE CASCADE,
    FOREIGN KEY (basvuruId) REFERENCES basvurular(basvuruId) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_log_belgeId ON belge_analiz_log(belgeId);
CREATE INDEX IF NOT EXISTS idx_log_basvuruId ON belge_analiz_log(basvuruId);
CREATE INDEX IF NOT EXISTS idx_log_basarili ON belge_analiz_log(basarili);
CREATE INDEX IF NOT EXISTS idx_log_created ON belge_analiz_log(created_at);

-- =============================================================================
-- TABLO 6: CHUNK SONUÇLARI (Her chunk için ham JSON)
-- =============================================================================
CREATE TABLE IF NOT EXISTS chunk_sonuclari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id INTEGER NOT NULL, -- belge_analiz_log tablosuna referans
    chunk_index INTEGER NOT NULL CHECK(chunk_index >= 0),

    -- Chunk içeriği
    chunk_start INTEGER NOT NULL, -- Başlangıç karakteri
    chunk_end INTEGER NOT NULL, -- Bitiş karakteri
    chunk_text_hash TEXT, -- SHA256 hash (tekrar analiz önleme)

    -- Ollama response
    response_json TEXT NOT NULL, -- Ham JSON string
    response_valid INTEGER CHECK(response_valid IN (0, 1)), -- JSON geçerli mi?

    -- Performans
    api_call_suresi_sn REAL,

    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY (log_id) REFERENCES belge_analiz_log(id) ON DELETE CASCADE,
    UNIQUE(log_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunk_log ON chunk_sonuclari(log_id);

-- =============================================================================
-- TABLO 7: SİSTEM KONFİGÜRASYON
-- =============================================================================
CREATE TABLE IF NOT EXISTS sistem_config (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT CHECK(value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
    description TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Default config değerleri
INSERT OR IGNORE INTO sistem_config (key, value, value_type, description) VALUES
    ('ollama_url', 'http://localhost:11434', 'string', 'Ollama API base URL'),
    ('ollama_model', 'llama3.2-vision:latest', 'string', 'Varsayılan Ollama model'),
    ('chunk_size', '4000', 'integer', 'Chunk karakter sayısı'),
    ('chunk_overlap', '200', 'integer', 'Chunk overlap karakter sayısı'),
    ('max_retries', '3', 'integer', 'Maksimum retry sayısı'),
    ('timeout_seconds', '120', 'integer', 'API timeout (saniye)'),
    ('parallel_processing', 'false', 'boolean', 'Paralel işlem aktif mi?'),
    ('max_workers', '4', 'integer', 'Paralel worker sayısı');

-- =============================================================================
-- TABLO 8: BELGE TİPİ TAHMİN KURALLARI
-- =============================================================================
CREATE TABLE IF NOT EXISTS belge_tipi_kurallar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dosya_adi_pattern TEXT NOT NULL UNIQUE, -- Regex pattern
    tahmin_edilen_tip TEXT NOT NULL,
    oncelik INTEGER DEFAULT 1, -- Yüksek öncelik önce kontrol edilir
    aktif INTEGER DEFAULT 1 CHECK(aktif IN (0, 1))
);

-- Tahmin kuralları
INSERT OR IGNORE INTO belge_tipi_kurallar (dosya_adi_pattern, tahmin_edilen_tip, oncelik) VALUES
    ('(?i).*cv.*', 'Özgeçmiş/CV', 10),
    ('(?i).*özgeçmiş.*', 'Özgeçmiş/CV', 10),
    ('(?i).*resume.*', 'Özgeçmiş/CV', 10),
    ('(?i).*sgk.*', 'SGK Hizmet Dökümü', 10),
    ('(?i).*diploma.*', 'Yök Lisans Diploması', 10),
    ('(?i).*adli.*sicil.*', 'Adli Sicil Kaydı', 10),
    ('(?i).*sabıka.*', 'Adli Sicil Kaydı', 10),
    ('(?i).*hitap.*', 'Hitap Hizmet Dökümü', 10),
    ('(?i).*vesikalık.*', 'Fotoğraf (vesikalık)', 10),
    ('(?i).*foto.*', 'Fotoğraf (vesikalık)', 5),
    ('(?i).*proje.*', 'Proje Dosyası (1)', 5),
    ('(?i).*tubitak.*', 'Proje Dosyası (1)', 8),
    ('(?i).*bap.*', 'Proje Dosyası (2)', 8),
    ('(?i).*horizon.*', 'Proje Dosyası (3)', 8),
    ('(?i).*enerji.*', 'Enerji Üretimi', 7),
    ('(?i).*metal.*', 'Metal Üretimi ve İşlemesi', 7),
    ('(?i).*mineral.*', 'Mineral Endüstrisi', 7),
    ('(?i).*kimya.*', 'Kimya Endüstrisi', 7),
    ('(?i).*atık.*', 'Atık Yönetimi', 7),
    ('(?i).*üretim.*', 'Diğer Üretim Faaliyetleri', 5),
    ('(?i).*ustyazi.*', 'Üst Yazı', 10),
    ('(?i).*üst.*yazı.*', 'Üst Yazı', 10);

-- =============================================================================
-- TABLO 9: ZORUNLU BELGELER MATRİSİ
-- =============================================================================
CREATE TABLE IF NOT EXISTS zorunlu_belgeler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hizmetId TEXT NOT NULL,
    belgeTipi TEXT NOT NULL,
    zorunlu INTEGER NOT NULL CHECK(zorunlu IN (0, 1)), -- 1: Zorunlu, 0: Opsiyonel
    aciklama TEXT,
    UNIQUE(hizmetId, belgeTipi)
);

-- 10307: Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)
INSERT OR IGNORE INTO zorunlu_belgeler (hizmetId, belgeTipi, zorunlu, aciklama) VALUES
    ('10307', 'Yök Lisans Diploması', 1, 'Lisans veya üstü diploma'),
    ('10307', 'SGK Hizmet Dökümü', 1, 'Çalışma geçmişi'),
    ('10307', 'Adli Sicil Kaydı', 1, 'Sabıka kaydı'),
    ('10307', 'Hitap Hizmet Dökümü', 1, 'Kamu çalışma belgesi'),
    ('10307', 'Özgeçmiş/CV', 1, 'Detaylı özgeçmiş'),
    ('10307', 'Fotoğraf (vesikalık)', 1, 'Vesikalık fotoğraf'),
    ('10307', 'Proje Dosyası (1)', 1, 'En az 1 proje belgesi'),
    ('10307', 'Enerji Üretimi', 0, 'Opsiyonel sektör belgesi'),
    ('10307', 'Metal Üretimi ve İşlemesi', 0, 'Opsiyonel sektör belgesi'),
    ('10307', 'Mineral Endüstrisi', 0, 'Opsiyonel sektör belgesi'),
    ('10307', 'Kimya Endüstrisi', 0, 'Opsiyonel sektör belgesi'),
    ('10307', 'Atık Yönetimi', 0, 'Opsiyonel sektör belgesi'),
    ('10307', 'Diğer Üretim Faaliyetleri', 0, 'Opsiyonel sektör belgesi');

-- 10308: Sanayide Yeşil Dönüşüm Sorumlusu (Eski Bakanlık Personeli)
INSERT OR IGNORE INTO zorunlu_belgeler (hizmetId, belgeTipi, zorunlu, aciklama) VALUES
    ('10308', 'Yök Lisans Diploması', 1, 'Lisans veya üstü diploma'),
    ('10308', 'SGK Hizmet Dökümü', 1, 'Çalışma geçmişi'),
    ('10308', 'Adli Sicil Kaydı', 1, 'Sabıka kaydı'),
    ('10308', 'Hitap Hizmet Dökümü', 1, 'ZORUNLU - Bakanlık çalışma belgesi'),
    ('10308', 'Özgeçmiş/CV', 1, 'Detaylı özgeçmiş'),
    ('10308', 'Fotoğraf (vesikalık)', 1, 'Vesikalık fotoğraf'),
    ('10308', 'Enerji Üretimi', 0, 'Opsiyonel - Denetim raporu'),
    ('10308', 'Metal Üretimi ve İşlemesi', 0, 'Opsiyonel - Denetim raporu'),
    ('10308', 'Mineral Endüstrisi', 0, 'Opsiyonel - Denetim raporu'),
    ('10308', 'Kimya Endüstrisi', 0, 'Opsiyonel - Denetim raporu'),
    ('10308', 'Atık Yönetimi', 0, 'Opsiyonel - Denetim raporu'),
    ('10308', 'Diğer Üretim Faaliyetleri', 0, 'Opsiyonel - Denetim raporu');

-- 10309: Sanayide Yeşil Dönüşüm Sorumlusu (Sektör Çalışanı)
INSERT OR IGNORE INTO zorunlu_belgeler (hizmetId, belgeTipi, zorunlu, aciklama) VALUES
    ('10309', 'Yök Lisans Diploması', 1, 'Lisans veya üstü diploma'),
    ('10309', 'SGK Hizmet Dökümü', 1, 'Min 5 yıl iş deneyimi'),
    ('10309', 'Adli Sicil Kaydı', 1, 'Sabıka kaydı'),
    ('10309', 'Özgeçmiş/CV', 1, 'Detaylı özgeçmiş'),
    ('10309', 'Fotoğraf (vesikalık)', 1, 'Vesikalık fotoğraf'),
    ('10309', 'Enerji Üretimi', 0, 'Opsiyonel - İş deneyimi belgesi'),
    ('10309', 'Metal Üretimi ve İşlemesi', 0, 'Opsiyonel - İş deneyimi belgesi'),
    ('10309', 'Mineral Endüstrisi', 0, 'Opsiyonel - İş deneyimi belgesi'),
    ('10309', 'Kimya Endüstrisi', 0, 'Opsiyonel - İş deneyimi belgesi'),
    ('10309', 'Atık Yönetimi', 0, 'Opsiyonel - İş deneyimi belgesi'),
    ('10309', 'Diğer Üretim Faaliyetleri', 0, 'Opsiyonel - İş deneyimi belgesi');

-- 10310: Sanayide Yeşil Dönüşüm Baş Sorumlusu (Akademisyen)
INSERT OR IGNORE INTO zorunlu_belgeler (hizmetId, belgeTipi, zorunlu, aciklama) VALUES
    ('10310', 'Yök Lisans Diploması', 1, 'Lisans veya üstü diploma'),
    ('10310', 'SGK Hizmet Dökümü', 1, 'Çalışma geçmişi'),
    ('10310', 'Adli Sicil Kaydı', 1, 'Sabıka kaydı'),
    ('10310', 'Hitap Hizmet Dökümü', 1, 'Kamu çalışma belgesi'),
    ('10310', 'Özgeçmiş/CV', 1, 'Detaylı özgeçmiş'),
    ('10310', 'Fotoğraf (vesikalık)', 1, 'Vesikalık fotoğraf'),
    ('10310', 'Proje Dosyası (1)', 1, 'ZORUNLU - 1. proje belgesi'),
    ('10310', 'Proje Dosyası (2)', 1, 'ZORUNLU - 2. proje belgesi'),
    ('10310', 'Proje Dosyası (3)', 1, 'ZORUNLU - 3. proje belgesi'),
    ('10310', 'Enerji Üretimi', 0, 'Opsiyonel sektör belgesi'),
    ('10310', 'Metal Üretimi ve İşlemesi', 0, 'Opsiyonel sektör belgesi'),
    ('10310', 'Mineral Endüstrisi', 0, 'Opsiyonel sektör belgesi'),
    ('10310', 'Kimya Endüstrisi', 0, 'Opsiyonel sektör belgesi'),
    ('10310', 'Atık Yönetimi', 0, 'Opsiyonel sektör belgesi'),
    ('10310', 'Diğer Üretim Faaliyetleri', 0, 'Opsiyonel sektör belgesi');

-- 10311 ve 10312 için aynı mantık (şimdilik 10310 ile aynı)
INSERT OR IGNORE INTO zorunlu_belgeler (hizmetId, belgeTipi, zorunlu, aciklama)
SELECT '10311', belgeTipi, zorunlu, aciklama FROM zorunlu_belgeler WHERE hizmetId = '10310';

INSERT OR IGNORE INTO zorunlu_belgeler (hizmetId, belgeTipi, zorunlu, aciklama)
SELECT '10312', belgeTipi, zorunlu, aciklama FROM zorunlu_belgeler WHERE hizmetId = '10309';

-- =============================================================================
-- VIEWS (Raporlama için hazır viewlar)
-- =============================================================================

-- View 1: Başvuru özeti
CREATE VIEW IF NOT EXISTS v_basvuru_ozet AS
SELECT
    b.basvuruId,
    b.takipNo,
    b.basvuruTarihi,
    b.hizmetAdi,
    b.basvuruYapanAd || ' ' || b.basvuruYapanSoyad AS ad_soyad,
    b.basvuruYapanVatandasTC AS tc,
    b.basvuruDurum,
    b.kararDurum,
    b.islendiMi,
    COUNT(bel.belgeId) AS toplam_belge_sayisi,
    SUM(CASE WHEN bel.analiz_edildi = 1 THEN 1 ELSE 0 END) AS analiz_edilen_belge_sayisi,
    a.zorunlu_belgeler_tam,
    a.eksik_belgeler,
    b.islenme_suresi_sn
FROM basvurular b
LEFT JOIN belgeler bel ON b.basvuruId = bel.basvuruId
LEFT JOIN analiz_sonuclari a ON b.basvuruId = a.basvuruId
GROUP BY b.basvuruId;

-- View 2: Sektör dağılımı
CREATE VIEW IF NOT EXISTS v_sektor_dagilim AS
SELECT
    basvuruId,
    SUM(sektor_enerji) AS enerji_sayisi,
    SUM(sektor_metal) AS metal_sayisi,
    SUM(sektor_mineral) AS mineral_sayisi,
    SUM(sektor_kimya) AS kimya_sayisi,
    SUM(sektor_atik) AS atik_sayisi,
    SUM(sektor_diger) AS diger_sayisi
FROM analiz_sonuclari
GROUP BY basvuruId;

-- View 3: Belge analiz performansı
CREATE VIEW IF NOT EXISTS v_analiz_performans AS
SELECT
    belgeTipi,
    COUNT(*) AS toplam_analiz,
    SUM(CASE WHEN basarili = 1 THEN 1 ELSE 0 END) AS basarili_analiz,
    AVG(islem_suresi_sn) AS ortalama_sure_sn,
    AVG(chunk_sayisi) AS ortalama_chunk,
    AVG(retry_sayisi) AS ortalama_retry
FROM belge_analiz_log
GROUP BY belgeTipi;

-- =============================================================================
-- TRIGGERS (Otomatik güncelleme)
-- =============================================================================

-- Trigger 1: basvurular updated_at otomatik güncelleme
CREATE TRIGGER IF NOT EXISTS trg_basvurular_updated
AFTER UPDATE ON basvurular
FOR EACH ROW
BEGIN
    UPDATE basvurular
    SET updated_at = datetime('now')
    WHERE basvuruId = NEW.basvuruId;
END;

-- Trigger 2: analiz_sonuclari updated_at otomatik güncelleme
CREATE TRIGGER IF NOT EXISTS trg_analiz_updated
AFTER UPDATE ON analiz_sonuclari
FOR EACH ROW
BEGIN
    UPDATE analiz_sonuclari
    SET updated_at = datetime('now')
    WHERE id = NEW.id;
END;

-- Trigger 3: Belge silindiğinde analiz_sonuclari'ndan ilgili bilgiyi temizle
CREATE TRIGGER IF NOT EXISTS trg_belge_silme
AFTER DELETE ON belgeler
FOR EACH ROW
BEGIN
    -- Bu trigger ile ilgili cleanup yapılabilir
    SELECT 1;
END;
