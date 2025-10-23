"""
External API (CSB eBasvuru) veri modelleri
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class HizmetModel(BaseModel):
    """Hizmet modeli"""
    hizmet_id: str = Field(..., alias="hizmetId")
    hizmet_adi: str = Field(..., alias="hizmetAdi")

    class Config:
        populate_by_name = True


class BasvuruListeModel(BaseModel):
    """Başvuru liste modeli"""
    takip_no: str = Field(..., alias="takipNo")
    hizmet_id: str = Field(..., alias="hizmetId")
    hizmet_adi: str = Field(..., alias="hizmetAdi")
    basvuru_durum: str = Field(..., alias="basvuruDurum")
    basvuru_tarihi: str = Field(..., alias="basvuruTarihi")

    class Config:
        populate_by_name = True


class BelgeInfoModel(BaseModel):
    """Belge bilgi modeli (detay içinde)"""
    belge_id: str = Field(..., alias="belgeId")
    belge_tipi: str = Field(..., alias="belgeTipi")
    dosya_adi: Optional[str] = Field(None, alias="dosyaAdi")

    class Config:
        populate_by_name = True


class BasvuruDetayModel(BaseModel):
    """Başvuru detay modeli"""
    basvuru_id: str = Field(..., alias="basvuruId")
    takip_no: str = Field(..., alias="takipNo")
    evrak_kayit_no: Optional[str] = Field(None, alias="evrakKayitNo")
    evrak_tarihi: Optional[str] = Field(None, alias="evrakTarihi")
    belgeler: List[BelgeInfoModel] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class BelgeModel(BaseModel):
    """Belge dosya modeli (base64 içerir)"""
    belge_id: str = Field(..., alias="belgeId")
    belge_tipi: str = Field(..., alias="belgeTipi")
    dosya_adi: Optional[str] = Field(None, alias="dosyaAdi")
    base64: str

    class Config:
        populate_by_name = True


class BasvuruWithBelgelerModel(BaseModel):
    """Başvuru + tüm belgeleri birlikte"""
    basvuru_id: str
    takip_no: str
    evrak_kayit_no: Optional[str] = None
    evrak_tarihi: Optional[str] = None
    belgeler: List[BelgeModel] = Field(default_factory=list)
