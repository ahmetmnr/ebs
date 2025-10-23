-- Migration 002: Add analiz_notu column to belgeler table
-- Tarih: 2025-10-23
-- Amaç: Photo validator için not alanı

-- Add analiz_notu column for validation notes
ALTER TABLE belgeler ADD COLUMN analiz_notu TEXT;
