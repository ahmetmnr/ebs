"""
Analiz sonuçlarını görüntüleme script'i.

Kullanım:
    python scripts/view_results.py --basvuru-id 5927843
    python scripts/view_results.py --takip-no 5927843
    python scripts/view_results.py --latest 5
    python scripts/view_results.py --stats
"""

import sys
import io
import json
import argparse
from pathlib import Path

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import db


def print_header(text):
    """Başlık yazdır"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text):
    """Bölüm başlığı"""
    print(f"\n--- {text} ---")


def view_basvuru_by_id(basvuru_id: int):
    """Başvuru ID'sine göre detaylı sonuçları göster"""

    # Başvuru bilgisi
    query = "SELECT * FROM basvurular WHERE basvuruId = ?"
    basvuru = db.fetchone(query, (basvuru_id,))

    if not basvuru:
        print(f"[HATA] Başvuru bulunamadı: {basvuru_id}")
        return

    print_header(f"BAŞVURU DETAYI - {basvuru['takipNo']}")

    print(f"Başvuru ID: {basvuru['basvuruId']}")
    print(f"Takip No: {basvuru['takipNo']}")
    print(f"Başvuru Tarihi: {basvuru['basvuruTarihi']}")
    print(f"Hizmet: {basvuru['hizmetAdi']} ({basvuru['hizmetId']})")
    print(f"Başvuran: {basvuru['basvuruYapanAd']} {basvuru['basvuruYapanSoyad']}")
    print(f"TC: {basvuru['basvuruYapanVatandasTC']}")
    print(f"Durum: {basvuru['basvuruDurum']}")
    print(f"Karar: {basvuru['kararDurum']}")
    print(f"İşlendi mi: {'✓ Evet' if basvuru['islendiMi'] else '✗ Hayır'}")

    if basvuru['islenme_suresi_sn']:
        print(f"İşlenme Süresi: {basvuru['islenme_suresi_sn']:.2f} saniye")

    # Belgeler
    print_section("BELGELER")
    query = """
        SELECT belgeId, belgeTipi, belgeTipi_tahmini, analiz_edildi, analiz_suresi_sn
        FROM belgeler
        WHERE basvuruId = ?
        ORDER BY belgeId
    """
    belgeler = db.fetchall(query, (basvuru_id,))

    print(f"Toplam Belge: {len(belgeler)}")
    analiz_edilen = sum(1 for b in belgeler if b['analiz_edildi'])
    print(f"Analiz Edilen: {analiz_edilen}/{len(belgeler)}")

    for belge in belgeler:
        belge_tip = belge['belgeTipi'] or belge['belgeTipi_tahmini'] or 'Bilinmiyor'
        status = "✓" if belge['analiz_edildi'] else "✗"
        sure = f"({belge['analiz_suresi_sn']:.2f}s)" if belge['analiz_suresi_sn'] else ""
        print(f"  {status} [{belge['belgeId']}] {belge_tip} {sure}")

    # Analiz Logları
    print_section("ANALİZ LOGLARI")
    query = """
        SELECT belgeTipi, basarili, islem_suresi_sn, chunk_sayisi, hata_mesaji
        FROM belge_analiz_log
        WHERE basvuruId = ?
        ORDER BY id
    """
    logs = db.fetchall(query, (basvuru_id,))

    if logs:
        for log in logs:
            status = "✓ BAŞARILI" if log['basarili'] else "✗ BAŞARISIZ"
            chunks = f"{log['chunk_sayisi']} chunk" if log['chunk_sayisi'] else ""
            sure = f"{log['islem_suresi_sn']:.2f}s" if log['islem_suresi_sn'] else ""

            print(f"  [{status}] {log['belgeTipi']} - {sure} {chunks}")

            if log['hata_mesaji']:
                print(f"      Hata: {log['hata_mesaji']}")
    else:
        print("  Henüz analiz logu yok")

    # Chunk Sonuçları (Ham JSON)
    print_section("ANALİZ SONUÇLARI (Ham JSON)")
    query = """
        SELECT c.chunk_index, c.response_json, l.belgeTipi
        FROM chunk_sonuclari c
        JOIN belge_analiz_log l ON c.log_id = l.id
        WHERE l.basvuruId = ?
        ORDER BY l.id, c.chunk_index
    """
    chunks = db.fetchall(query, (basvuru_id,))

    if chunks:
        current_belge = None
        for chunk in chunks:
            if chunk['belgeTipi'] != current_belge:
                current_belge = chunk['belgeTipi']
                print(f"\n  {current_belge}:")

            try:
                data = json.loads(chunk['response_json'])
                print(f"    Chunk {chunk['chunk_index']}:")
                print(f"      {json.dumps(data, ensure_ascii=False, indent=6)}")
            except json.JSONDecodeError:
                print(f"    Chunk {chunk['chunk_index']}: [JSON parse hatası]")
    else:
        print("  Henüz chunk sonucu yok")


def view_latest_basvurular(limit: int = 10):
    """Son başvuruları listele"""
    print_header(f"SON {limit} BAŞVURU")

    query = """
        SELECT basvuruId, takipNo, basvuruTarihi, hizmetAdi,
               basvuruYapanAd, basvuruYapanSoyad, islendiMi,
               (SELECT COUNT(*) FROM belgeler WHERE basvuruId = b.basvuruId) as belge_sayisi,
               (SELECT COUNT(*) FROM belgeler WHERE basvuruId = b.basvuruId AND analiz_edildi = 1) as analiz_edilen
        FROM basvurular b
        ORDER BY basvuruId DESC
        LIMIT ?
    """
    basvurular = db.fetchall(query, (limit,))

    print(f"\n{'ID':<10} {'Takip No':<12} {'Ad Soyad':<30} {'Hizmet':<15} {'Belgeler':<10} {'Durum':<10}")
    print("-" * 100)

    for b in basvurular:
        ad_soyad = f"{b['basvuruYapanAd']} {b['basvuruYapanSoyad']}"
        belgeler = f"{b['analiz_edilen']}/{b['belge_sayisi']}"
        durum = "✓ İşlendi" if b['islendiMi'] else "○ Bekliyor"
        hizmet_short = b['hizmetAdi'][:13] + ".." if len(b['hizmetAdi']) > 15 else b['hizmetAdi']

        print(f"{b['basvuruId']:<10} {b['takipNo']:<12} {ad_soyad:<30} {hizmet_short:<15} {belgeler:<10} {durum:<10}")


def show_stats():
    """Genel istatistikleri göster"""
    print_header("GENEL İSTATİSTİKLER")

    # Başvuru istatistikleri
    query = "SELECT COUNT(*) as toplam FROM basvurular"
    toplam = db.fetchone(query)['toplam']

    query = "SELECT COUNT(*) as islenen FROM basvurular WHERE islendiMi = 1"
    islenen = db.fetchone(query)['islenen']

    print_section("BAŞVURULAR")
    print(f"Toplam Başvuru: {toplam}")
    print(f"İşlenen: {islenen} ({islenen/toplam*100:.1f}%)")
    print(f"Bekleyen: {toplam - islenen} ({(toplam-islenen)/toplam*100:.1f}%)")

    # Belge istatistikleri
    query = "SELECT COUNT(*) as toplam FROM belgeler"
    toplam_belge = db.fetchone(query)['toplam']

    query = "SELECT COUNT(*) as analiz_edilen FROM belgeler WHERE analiz_edildi = 1"
    analiz_edilen_belge = db.fetchone(query)['analiz_edilen']

    print_section("BELGELER")
    print(f"Toplam Belge: {toplam_belge}")
    print(f"Analiz Edilen: {analiz_edilen_belge} ({analiz_edilen_belge/toplam_belge*100:.1f}%)")

    # Belge tipi dağılımı
    query = """
        SELECT belgeTipi, COUNT(*) as adet
        FROM belgeler
        WHERE belgeTipi IS NOT NULL
        GROUP BY belgeTipi
        ORDER BY adet DESC
    """
    belge_tipleri = db.fetchall(query)

    print_section("BELGE TİPİ DAĞILIMI")
    for bt in belge_tipleri:
        print(f"  {bt['belgeTipi']}: {bt['adet']}")

    # Analiz performansı
    query = """
        SELECT
            belgeTipi,
            COUNT(*) as toplam,
            SUM(CASE WHEN basarili = 1 THEN 1 ELSE 0 END) as basarili,
            AVG(islem_suresi_sn) as ort_sure,
            AVG(chunk_sayisi) as ort_chunk
        FROM belge_analiz_log
        GROUP BY belgeTipi
        ORDER BY toplam DESC
    """
    performans = db.fetchall(query)

    print_section("ANALİZ PERFORMANSI")
    print(f"{'Belge Tipi':<30} {'Toplam':<10} {'Başarılı':<10} {'Ort. Süre':<12} {'Ort. Chunk':<10}")
    print("-" * 80)

    for p in performans:
        basari_oran = f"{p['basarili']}/{p['toplam']}"
        ort_sure = f"{p['ort_sure']:.2f}s" if p['ort_sure'] else "-"
        ort_chunk = f"{p['ort_chunk']:.1f}" if p['ort_chunk'] else "-"

        print(f"{p['belgeTipi']:<30} {p['toplam']:<10} {basari_oran:<10} {ort_sure:<12} {ort_chunk:<10}")


def export_to_json(basvuru_id: int, output_file: str = None):
    """Başvuru sonuçlarını JSON olarak export et"""

    # Başvuru bilgisi
    query = "SELECT * FROM basvurular WHERE basvuruId = ?"
    basvuru = db.fetchone(query, (basvuru_id,))

    if not basvuru:
        print(f"[HATA] Başvuru bulunamadı: {basvuru_id}")
        return

    # Belgeler
    query = "SELECT * FROM belgeler WHERE basvuruId = ?"
    belgeler = db.fetchall(query, (basvuru_id,))

    # Chunk sonuçları
    query = """
        SELECT c.*, l.belgeTipi
        FROM chunk_sonuclari c
        JOIN belge_analiz_log l ON c.log_id = l.id
        WHERE l.basvuruId = ?
        ORDER BY l.id, c.chunk_index
    """
    chunks = db.fetchall(query, (basvuru_id,))

    # JSON oluştur
    result = {
        "basvuru": dict(basvuru),
        "belgeler": [dict(b) for b in belgeler],
        "analiz_sonuclari": {}
    }

    # Chunk sonuçlarını grupla
    for chunk in chunks:
        belge_tipi = chunk['belgeTipi']
        if belge_tipi not in result['analiz_sonuclari']:
            result['analiz_sonuclari'][belge_tipi] = []

        try:
            data = json.loads(chunk['response_json'])
            result['analiz_sonuclari'][belge_tipi].append({
                'chunk_index': chunk['chunk_index'],
                'data': data
            })
        except json.JSONDecodeError:
            pass

    # Dosyaya yaz veya ekrana bas
    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    if output_file:
        output_path = Path(output_file)
        output_path.write_text(json_str, encoding='utf-8')
        print(f"[OK] Sonuçlar kaydedildi: {output_file}")
    else:
        print(json_str)


def main():
    parser = argparse.ArgumentParser(description="Analiz sonuçlarını görüntüle")

    parser.add_argument('--basvuru-id', type=int, help='Başvuru ID')
    parser.add_argument('--takip-no', type=str, help='Takip numarası')
    parser.add_argument('--latest', type=int, help='Son N başvuruyu listele')
    parser.add_argument('--stats', action='store_true', help='Genel istatistikleri göster')
    parser.add_argument('--export', type=str, help='JSON olarak export et (dosya adı)')

    args = parser.parse_args()

    if args.stats:
        show_stats()

    elif args.latest:
        view_latest_basvurular(args.latest)

    elif args.takip_no:
        # Takip no'dan basvuru_id bul
        query = "SELECT basvuruId FROM basvurular WHERE takipNo = ?"
        result = db.fetchone(query, (args.takip_no,))
        if result:
            if args.export:
                export_to_json(result['basvuruId'], args.export)
            else:
                view_basvuru_by_id(result['basvuruId'])
        else:
            print(f"[HATA] Takip no bulunamadı: {args.takip_no}")

    elif args.basvuru_id:
        if args.export:
            export_to_json(args.basvuru_id, args.export)
        else:
            view_basvuru_by_id(args.basvuru_id)

    else:
        # Hiçbir argüman verilmediyse son 10 başvuruyu göster
        view_latest_basvurular(10)


if __name__ == "__main__":
    main()
