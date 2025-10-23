-- Migration 001: Kişisel bilgiler ve cross-validation kolonları ekle
-- Tarih: 2025-10-22

-- Kişisel bilgiler
ALTER TABLE analiz_sonuclari ADD COLUMN iletisim_email TEXT;
ALTER TABLE analiz_sonuclari ADD COLUMN iletisim_telefon TEXT;
ALTER TABLE analiz_sonuclari ADD COLUMN gsm TEXT;
ALTER TABLE analiz_sonuclari ADD COLUMN adres TEXT;
ALTER TABLE analiz_sonuclari ADD COLUMN baba_adi TEXT;
ALTER TABLE analiz_sonuclari ADD COLUMN ana_adi TEXT;

-- SGK detayları (yıl/ay ayrımı)
ALTER TABLE analiz_sonuclari ADD COLUMN deneyim_4a_yil INTEGER;
ALTER TABLE analiz_sonuclari ADD COLUMN deneyim_4a_ay INTEGER;
ALTER TABLE analiz_sonuclari ADD COLUMN deneyim_4b_yil INTEGER;
ALTER TABLE analiz_sonuclari ADD COLUMN deneyim_4b_ay INTEGER;
ALTER TABLE analiz_sonuclari ADD COLUMN staj_gun INTEGER;
ALTER TABLE analiz_sonuclari ADD COLUMN toplam_gun INTEGER;

-- Cross-validation
ALTER TABLE analiz_sonuclari ADD COLUMN validation_status TEXT; -- 'PASS', 'FAIL', 'WARNING'
ALTER TABLE analiz_sonuclari ADD COLUMN validation_errors TEXT; -- JSON
ALTER TABLE analiz_sonuclari ADD COLUMN validation_warnings TEXT; -- JSON
ALTER TABLE analiz_sonuclari ADD COLUMN ground_truth_source TEXT; -- 'Üst Yazı'

-- Index'ler
CREATE INDEX IF NOT EXISTS idx_analiz_validation ON analiz_sonuclari(validation_status);
