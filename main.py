"""
Ana uygulama entry point.

Kullanım:
    python main.py --import json_file.json
    python main.py --analyze --limit 10
    python main.py --validate --basvuru-id 123
"""

import argparse
import logging
import sys
import io
from pathlib import Path

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import LOG_LEVEL, LOG_FORMAT, DEBUG
from services import JSONParser
from models import Basvuru, Belge
from analyzers import CVAnalyzer, DiplomaAnalyzer, SGKAnalyzer, AdliSicilAnalyzer, ProjeAnalyzer
from services.validation_service import ValidationService

# Logging yapılandırması
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def import_json(file_path: str):
    """JSON dosyasını import et"""
    print(f"[INFO] JSON import ediliyor: {file_path}")
    
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Tek başvuru mu, liste mi?
    if isinstance(data, dict):
        data = [data]
    
    for item in data:
        json_str = json.dumps(item, ensure_ascii=False)
        hizmet_id = item.get('hizmetId', '10307')
        
        basvuru_id = JSONParser.parse_basvuru_json(json_str, hizmet_id)
        if basvuru_id:
            print(f"[OK] Başvuru kaydedildi: {item.get('takipNo')} (ID: {basvuru_id})")
        else:
            print(f"[HATA] Başvuru kaydedilemedi: {item.get('takipNo')}")


def analyze_basvuru(limit: int = None):
    """İşlenmemiş başvuruları analiz et - YENİ GELİŞMİŞ İŞ AKIŞI"""
    print(f"[INFO] İşlenmemiş başvurular analiz ediliyor (Gelişmiş İş Akışı)...")

    from services.analysis_orchestrator import AnalysisOrchestrator

    basvurular = Basvuru.get_unprocessed(limit=limit)
    print(f"[INFO] {len(basvurular)} başvuru bulundu")

    for i, basvuru in enumerate(basvurular, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(basvurular)}] Başvuru {basvuru['takipNo']} işleniyor...")
        print(f"{'='*80}")

        try:
            # Gelişmiş orchestrator ile analiz
            orchestrator = AnalysisOrchestrator(basvuru['basvuruId'])
            success = orchestrator.run()

            if success:
                print(f"\n✓✓✓ Başvuru başarıyla işlendi: {basvuru['takipNo']}")
            else:
                print(f"\n✗✗✗ Başvuru işlenemedi: {basvuru['takipNo']}")

        except Exception as e:
            logger.error(f"Başvuru işleme hatası: {e}", exc_info=True)
            print(f"\n✗✗✗ Kritik hata: {e}")

            # Hata durumunda başvuru durumunu güncelle
            Basvuru.mark_as_processed(basvuru['basvuruId'], success=False, error_msg=str(e))


def validate_basvuru(basvuru_id: int):
    """Başvuruyu validate et"""
    print(f"[INFO] Başvuru {basvuru_id} validate ediliyor...")
    
    report = ValidationService.get_validation_report(basvuru_id)
    
    print(f"\n{'='*60}")
    print(f"VALIDASYON RAPORU - Başvuru {report['takip_no']}")
    print(f"{'='*60}")
    
    print(f"\nGenel Durum: {'✓ GEÇERLİ' if report['overall_valid'] else '✗ GEÇERSİZ'}")
    
    print(f"\nBaşvuru Bilgileri:")
    print(f"  Geçerli: {report['basvuru']['valid']}")
    if report['basvuru']['errors']:
        for err in report['basvuru']['errors']:
            print(f"  - {err}")
    
    print(f"\nBelgeler:")
    print(f"  Tam: {report['documents']['complete']}")
    if report['documents']['missing']:
        print(f"  Eksik belgeler:")
        for belge in report['documents']['missing']:
            print(f"    - {belge}")
    
    print(f"\nAnaliz:")
    print(f"  Analiz mevcut: {report['analiz']['exists']}")
    print(f"  Geçerli: {report['analiz']['valid']}")


def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description="Başvuru Analiz Sistemi")
    
    parser.add_argument('--import', dest='import_file', help='JSON dosyasını import et')
    parser.add_argument('--analyze', action='store_true', help='Başvuruları analiz et')
    parser.add_argument('--validate', action='store_true', help='Başvuruyu validate et')
    parser.add_argument('--limit', type=int, help='İşlenecek başvuru sayısı')
    parser.add_argument('--basvuru-id', type=int, help='Başvuru ID')
    
    args = parser.parse_args()
    
    if args.import_file:
        import_json(args.import_file)
    
    elif args.analyze:
        analyze_basvuru(limit=args.limit)
    
    elif args.validate:
        if not args.basvuru_id:
            print("[HATA] --basvuru-id belirtilmeli")
            sys.exit(1)
        validate_basvuru(args.basvuru_id)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
