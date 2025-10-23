"""
Belge tiplerine göre JSON şemaları
"""

# ustYazi (Üst Yazı/Başvuru Formu) Şeması
USTYAZI_SCHEMA = {
    "type": "object",
    "properties": {
        "evrak_bilgileri": {
            "type": "object",
            "properties": {
                "evrak_no": {"type": "string"},
                "evrak_tarihi": {"type": "string"}  # YYYY-MM-DD
            }
        },
        "basvuran_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "basvuru_turu": {"type": "string"},  # Akademisyen, Sektör Çalışanı, Eski Bakanlık Personeli
                "basvurulan_alan": {"type": "string"},  # Sorumlu, Başsorumlu
                "basvurulan_sektorler": {
                    "type": "array",
                    "items": {"type": "string"}  # Enerji, Metal, Kimya, Mineral, Atık, Diğer Üretim Faaliyetleri
                }
            }
        },
        "iletisim_bilgileri": {
            "type": "object",
            "properties": {
                "telefon": {"type": "string"},
                "eposta": {"type": "string"},
                "adres": {"type": "string"}
            }
        }
    }
}

# Özgeçmiş Şeması
OZGECMIS_SCHEMA = {
    "type": "object",
    "properties": {
        "kisisel_bilgiler": {
            "type": "object",
            "properties": {
                "ad": {"type": "string"},
                "soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "dogum_tarihi": {"type": "string"},  # YYYY-MM-DD
                "dogum_yeri": {"type": "string"},
                "cinsiyet": {"type": "string"},
                "medeni_durum": {"type": "string"},
                "telefon": {"type": "string"},
                "email": {"type": "string"},
                "adres": {"type": "string"}
            }
        },
        "egitim": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "seviye": {"type": "string"},  # Lisans, Yüksek Lisans, Doktora
                    "okul_adi": {"type": "string"},
                    "bolum": {"type": "string"},
                    "baslangic_yili": {"type": "string"},
                    "bitis_yili": {"type": "string"},
                    "derece": {"type": "string"}
                }
            }
        },
        "is_deneyimi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sirket_adi": {"type": "string"},
                    "pozisyon": {"type": "string"},
                    "sektor": {"type": "string"},  # Enerji, Metal, Mineral, Kimya, Atık, Diğer
                    "baslangic_tarihi": {"type": "string"},  # YYYY-MM-DD
                    "bitis_tarihi": {"type": "string"},  # YYYY-MM-DD veya "Devam Ediyor"
                    "gorev_tanimi": {"type": "string"},
                    "cevre_ile_ilgili": {"type": "boolean"}  # Çevre alanında mı?
                }
            }
        },
        "diller": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dil": {"type": "string"},
                    "seviye": {"type": "string"}
                }
            }
        },
        "sertifikalar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sertifika_adi": {"type": "string"},
                    "veren_kurum": {"type": "string"},
                    "tarih": {"type": "string"}
                }
            }
        },
        "projeler_ve_yayinlar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tip": {"type": "string"},  # Proje, Yayın, Bildiri, Makale, Kitap Bölümü
                    "baslik": {"type": "string"},
                    "aciklama": {"type": "string"},
                    "tarih": {"type": "string"},
                    "kurum": {"type": "string"},
                    "apa7_format": {"type": "string"},  # Tam APA 7 formatında kaynak (Akademisyen için)
                    "sektor_uygunlugu": {"type": "string"},  # Hangi sektöre uygun: Enerji, Metal, Kimya, vb.
                    "cevre_ile_ilgili": {"type": "boolean"}  # Çevre alanıyla ilgili mi?
                }
            }
        },
        "akademik_yayinlar": {
            "type": "object",
            "properties": {
                "toplam_sayi": {"type": "integer"},
                "makaleler": {"type": "array", "items": {"type": "string"}},  # APA 7 formatında
                "bildiriler": {"type": "array", "items": {"type": "string"}},  # APA 7 formatında
                "kitaplar": {"type": "array", "items": {"type": "string"}}  # APA 7 formatında
            }
        }
    }
}

# SGK Dökümü Şeması
SGK_SCHEMA = {
    "type": "object",
    "properties": {
        "kisi_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "sgk_sicil_no": {"type": "string"}
            }
        },
        "calisma_gecmisi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "isyeri_adi": {"type": "string"},
                    "ise_giris_tarihi": {"type": "string"},  # YYYY-MM-DD
                    "isten_cikis_tarihi": {"type": "string"},  # YYYY-MM-DD veya null (devam ediyorsa)
                    "calisma_suresi_gun": {"type": "integer"},
                    "meslek": {"type": "string"},
                    "sgk_kodu": {"type": "string"},
                    "sektor": {"type": "string"},  # Enerji, Metal, Mineral, Kimya, Atık, Diğer Üretim Faaliyetleri
                    "cevre_ile_ilgili": {"type": "boolean"}  # Çevre alanında mı?
                }
            }
        },
        "toplam_calisma_suresi": {
            "type": "object",
            "properties": {
                "yil": {"type": "integer"},
                "ay": {"type": "integer"},
                "gun": {"type": "integer"},
                "toplam_gun": {"type": "integer"}
            }
        },
        "sektor_dagilimi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sektor": {"type": "string"},
                    "sure_gun": {"type": "integer"},
                    "sure_yil": {"type": "number"}
                }
            }
        }
    }
}

# Diploma Şeması
DIPLOMA_SCHEMA = {
    "type": "object",
    "properties": {
        "ogrenci_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "ogrenci_no": {"type": "string"}
            }
        },
        "diploma_bilgileri": {
            "type": "object",
            "properties": {
                "diploma_turu": {"type": "string"},  # Lisans, Yüksek Lisans, Doktora, Önlisans
                "universite": {"type": "string"},
                "fakulte": {"type": "string"},
                "bolum": {"type": "string"},
                "program": {"type": "string"},
                "mezuniyet_tarihi": {"type": "string"},  # YYYY-MM-DD
                "mezuniyet_yili": {"type": "string"},  # YYYY
                "diploma_no": {"type": "string"},
                "diploma_tarihi": {"type": "string"}
            }
        }
    }
}

# Adli Sicil Belgesi Şeması
ADLI_SICIL_SCHEMA = {
    "type": "object",
    "properties": {
        "kisi_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "baba_adi": {"type": "string"},
                "ana_adi": {"type": "string"},
                "dogum_tarihi": {"type": "string"},
                "dogum_yeri": {"type": "string"}
            }
        },
        "belge_bilgileri": {
            "type": "object",
            "properties": {
                "belge_no": {"type": "string"},
                "duzenleme_tarihi": {"type": "string"},
                "gecerlilik_suresi": {"type": "string"},
                "sabika_kaydi": {"type": "boolean"},  # Adli sicil kaydı var mı?
                "yuz_kizartici_suc": {"type": "boolean"},  # Yüz kızartıcı suç var mı?
                "aciklama": {"type": "string"},  # Belge metni açıklama
                "suc_detaylari": {
                    "type": "array",
                    "items": {"type": "string"}  # Varsa suç detayları
                }
            }
        }
    }
}

# Hitap Belgesi Şeması (Bakanlık Personeli için)
HITAP_SCHEMA = {
    "type": "object",
    "properties": {
        "kisi_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "sicil_no": {"type": "string"}
            }
        },
        "gorev_gecmisi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kurum": {"type": "string"},  # Çevre Bakanlığı, İl Müdürlüğü vs.
                    "gorev": {"type": "string"},  # Unvan/pozisyon
                    "baslangic_tarihi": {"type": "string"},  # YYYY-MM-DD
                    "bitis_tarihi": {"type": "string"},  # YYYY-MM-DD veya null
                    "gorev_suresi_gun": {"type": "integer"},
                    "cevre_alaninda": {"type": "boolean"}  # Çevre ile ilgili görev mi?
                }
            }
        },
        "toplam_gorev_suresi": {
            "type": "object",
            "properties": {
                "yil": {"type": "integer"},
                "ay": {"type": "integer"},
                "gun": {"type": "integer"},
                "toplam_gun": {"type": "integer"}
            }
        },
        "cevre_bakanlik_suresi": {
            "type": "object",
            "properties": {
                "yil": {"type": "integer"},
                "ay": {"type": "integer"},
                "gun": {"type": "integer"},
                "toplam_gun": {"type": "integer"}
            }
        }
    }
}

# Akademik Proje Belgesi Şeması
AKADEMIK_PROJE_SCHEMA = {
    "type": "object",
    "properties": {
        "proje_bilgileri": {
            "type": "object",
            "properties": {
                "proje_adi": {"type": "string"},
                "proje_no": {"type": "string"},
                "proje_turu": {"type": "string"},  # TÜBİTAK, BAP, AB Projesi, Sanayi İşbirliği
                "proje_durumu": {"type": "string"},  # Tamamlandı, Devam Ediyor
                "baslangic_tarihi": {"type": "string"},
                "bitis_tarihi": {"type": "string"},
                "butce": {"type": "string"}
            }
        },
        "arastirmaci_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},  # REFERANS
                "rol": {"type": "string"},  # Proje Yürütücüsü, Araştırmacı, Danışman
                "kurum": {"type": "string"}
            }
        },
        "proje_ozeti": {
            "type": "string",
            "description": "Proje özeti ve amacı"
        },
        "sektor_uygunlugu": {
            "type": "array",
            "items": {"type": "string"},  # Hangi sektörlere uygun: Enerji, Metal, Kimya, vb.
            "description": "Projenin hangi sektörlerle ilgili olduğu"
        },
        "cevre_ile_ilgili": {
            "type": "boolean",
            "description": "Proje çevre alanıyla ilgili mi?"
        },
        "ciktilar": {
            "type": "object",
            "properties": {
                "yayinlar": {
                    "type": "array",
                    "items": {"type": "string"},  # APA 7 formatında yayınlar
                    "description": "Projeden çıkan yayınlar (APA 7 formatında)"
                },
                "patent_lar": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "diger_ciktilar": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "apa7_format": {
            "type": "string",
            "description": "Proje APA 7 formatında kaynak olarak yazılmış hali"
        }
    }
}

# Sektör Belgesi Şeması (İş deneyimi belgesi, çalışma belgesi, referans vs.)
SEKTOR_BELGE_SCHEMA = {
    "type": "object",
    "properties": {
        "calisan_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},  # REFERANS
                "tc_kimlik_no": {"type": "string"}
            }
        },
        "firma_bilgileri": {
            "type": "object",
            "properties": {
                "firma_adi": {"type": "string"},
                "sektor": {"type": "string"},  # Enerji, Metal, Kimya, Mineral, Atık, Diğer
                "faaliyet_alani": {"type": "string"},  # Detaylı faaliyet alanı
                "adres": {"type": "string"}
            }
        },
        "calisma_bilgileri": {
            "type": "object",
            "properties": {
                "pozisyon": {"type": "string"},
                "gorev_tanimi": {"type": "string"},
                "baslangic_tarihi": {"type": "string"},  # YYYY-MM-DD
                "bitis_tarihi": {"type": "string"},  # YYYY-MM-DD veya null
                "calisma_suresi": {"type": "string"},  # Belgede yazıldığı gibi
                "calisma_suresi_gun": {"type": "integer"},  # Hesaplanmış
                "cevre_ile_ilgili": {"type": "boolean"}  # Çevre alanında mı?
            }
        },
        "belge_bilgileri": {
            "type": "object",
            "properties": {
                "belge_turu": {"type": "string"},  # İş Deneyim Belgesi, Çalışma Belgesi, Referans Mektubu
                "belge_no": {"type": "string"},
                "duzenleme_tarihi": {"type": "string"},  # YYYY-MM-DD
                "duzenlenen_kurum": {"type": "string"}
            }
        },
        "proje_deneyimleri": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "proje_adi": {"type": "string"},
                    "proje_aciklama": {"type": "string"},
                    "rol": {"type": "string"}
                }
            },
            "description": "Belgede bahsedilen proje deneyimleri"
        }
    }
}

# Referans Mektubu Şeması
REFERANS_SCHEMA = {
    "type": "object",
    "properties": {
        "referans_veren": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "unvan": {"type": "string"},
                "kurum": {"type": "string"},
                "telefon": {"type": "string"},
                "email": {"type": "string"}
            }
        },
        "aday_bilgileri": {
            "type": "object",
            "properties": {
                "ad_soyad": {"type": "string"},
                "calistigi_pozisyon": {"type": "string"},
                "calisma_suresi": {"type": "string"}
            }
        },
        "degerlendirme": {
            "type": "object",
            "properties": {
                "genel_yorum": {"type": "string"},
                "guclü_yonler": {"type": "array", "items": {"type": "string"}},
                "tavsiye": {"type": "boolean"}
            }
        }
    }
}

# Master JSON Şeması (Tüm belgelerden çıkarılan toplam veri)
MASTER_SCHEMA = {
    "type": "object",
    "properties": {
        "basvuru_bilgileri": {
            "type": "object",
            "properties": {
                "basvuru_id": {"type": "string"},
                "takip_no": {"type": "string"},  # Evrak Kayıt No
                "basvuru_tarihi": {"type": "string"},  # Evrak Tarihi
                "hizmet_adi": {"type": "string"},
                "basvuru_turu": {"type": "string"},  # Sektör Çalışanı / Akademisyen / Eski Bakanlık
                "basvurulan_alan": {"type": "string"}  # Sorumlu / Başsorumlu
            }
        },
        "basvuran": {
            "type": "object",
            "properties": {
                "ad": {"type": "string"},
                "soyad": {"type": "string"},
                "tc_kimlik_no": {"type": "string"},
                "dogum_tarihi": {"type": "string"},
                "telefon": {"type": "string"},
                "email": {"type": "string"}
            }
        },
        "basvurulan_sektorler": {
            "type": "object",
            "properties": {
                "enerji": {"type": "boolean"},
                "metal": {"type": "boolean"},
                "mineral": {"type": "boolean"},
                "kimya": {"type": "boolean"},
                "atik": {"type": "boolean"},
                "diger": {"type": "boolean"}
            }
        },
        "egitim_durumu": {
            "type": "object",
            "properties": {
                "en_yuksek_egitim": {"type": "string"},
                "universite": {"type": "string"},
                "bolum": {"type": "string"},
                "mezuniyet_yili": {"type": "string"}
            }
        },
        "is_deneyimi": {
            "type": "object",
            "properties": {
                "toplam_sure_yil": {"type": "number"},
                "toplam_sure_gun": {"type": "integer"},
                "detaylar": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sirket": {"type": "string"},
                            "pozisyon": {"type": "string"},
                            "sektor": {"type": "string"},
                            "baslangic": {"type": "string"},
                            "bitis": {"type": "string"},
                            "sure_gun": {"type": "integer"},
                            "cevre_ile_ilgili": {"type": "boolean"}
                        }
                    }
                }
            }
        },
        "sektor_dagilimi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sektor_adi": {"type": "string"},
                    "sure_gun": {"type": "integer"},
                    "sure_yil": {"type": "number"},
                    "oran": {"type": "number"}
                }
            }
        },
        "sektor_belge_durumu": {
            "type": "object",
            "properties": {
                "enerji": {"type": "boolean"},
                "metal": {"type": "boolean"},
                "mineral": {"type": "boolean"},
                "kimya": {"type": "boolean"},
                "atik": {"type": "boolean"},
                "diger": {"type": "boolean"}
            }
        },
        "projeler_ve_yayinlar": {
            "type": "object",
            "properties": {
                "toplam_sayi": {"type": "integer"},
                "liste": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tip": {"type": "string"},
                            "baslik": {"type": "string"},
                            "aciklama": {"type": "string"},
                            "tarih": {"type": "string"}
                        }
                    }
                }
            }
        },
        "uygunluk": {
            "type": "object",
            "properties": {
                "adli_sicil_temiz": {"type": "boolean"},
                "egitim_uygun": {"type": "boolean"},
                "deneyim_uygun": {"type": "boolean"},
                "genel_degerlendirme": {"type": "string"}
            }
        }
    }
}

# Belge tipi → Şema mapping
# ÖNEMLİ: Belgenet'ten gelen GERÇEK isimler kullanılmalı!
DOCUMENT_SCHEMAS = {
    # ustYazi - belgeTipi null olduğunda
    "ustyazi": USTYAZI_SCHEMA,

    # API'den gelen GERÇEK belgeTipi değerleri (DocumentClassifier turkish_lower ile normalize eder)
    "özgeçmiş/cv": OZGECMIS_SCHEMA,
    "sgk hizmet dökümü": SGK_SCHEMA,
    "yök lisans diploması": DIPLOMA_SCHEMA,
    "adli sicil kaydı": ADLI_SICIL_SCHEMA,
    "hitap hizmet dökümü": HITAP_SCHEMA,
    "fotoğraf (vesikalık)": {},
    "proje dosyası (1)": AKADEMIK_PROJE_SCHEMA,
    "proje dosyası (2)": AKADEMIK_PROJE_SCHEMA,
    "proje dosyası (3)": AKADEMIK_PROJE_SCHEMA,
    "enerji üretimi": SEKTOR_BELGE_SCHEMA,
    "metal üretimi ve işlemesi": SEKTOR_BELGE_SCHEMA,
    "mineral endüstrisi": SEKTOR_BELGE_SCHEMA,
    "kimya endüstrisi": SEKTOR_BELGE_SCHEMA,
    "atık yönetimi": SEKTOR_BELGE_SCHEMA,
    "diğer üretim faaliyetleri": SEKTOR_BELGE_SCHEMA,
}
