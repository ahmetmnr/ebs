#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from app.core.document_classifier import turkish_lower

test_cases = [
    'Proje Dosyası (1)',
    'Proje Dosyası (2)',
    'Proje Dosyası (3)',
    'Yök Lisans Diploması',
    'SGK Hizmet Dökümü',
    'Özgeçmiş/CV',
    'Enerji Üretimi',
    'Metal Üretimi ve İşlemesi',
]

for test in test_cases:
    result = turkish_lower(test)
    # Check if result exists in DOCUMENT_SCHEMAS
    from app.models.schemas import DOCUMENT_SCHEMAS
    exists = result in DOCUMENT_SCHEMAS
    print(f'{test} -> {result} | Schema exists: {exists}')
