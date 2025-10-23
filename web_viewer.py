"""
Sanayide Yeşil Dönüşüm Başvuru Analiz Sonuçları - Web Görüntüleyici
Streamlit tabanlı web arayüzü
"""

import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime

# Proje kök dizinini path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

from models.database import db

# Sayfa yapılandırması
st.set_page_config(
    page_title="Yeşil Dönüşüm Başvuru Analiz Sistemi",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Başlık
st.title("🌱 Sanayide Yeşil Dönüşüm Başvuru Değerlendirme Sistemi")
st.markdown("---")

# Sidebar - Filtreler
with st.sidebar:
    st.header("📊 Arama ve Filtreler")

    # Arama seçenekleri
    search_type = st.radio(
        "Arama Tipi",
        ["Takip No", "Başvuru ID", "TC Kimlik", "Ad Soyad"],
        index=0
    )

    # Session state'den gelen değeri al (görüntüle butonundan)
    if 'selected_basvuru_id' in st.session_state and st.session_state.selected_basvuru_id:
        # Başvuru ID'yi takip no'ya çevir
        query = "SELECT takipNo FROM basvurular WHERE basvuruId = ?"
        result = db.fetchone(query, (st.session_state.selected_basvuru_id,))
        if result:
            default_value = result['takipNo']
            search_type = "Takip No"
        else:
            default_value = ""
        st.session_state.selected_basvuru_id = None  # Temizle
    else:
        default_value = ""

    search_value = st.text_input(f"{search_type} Girin", value=default_value)

    st.markdown("---")

    # İstatistikler
    st.header("📈 Genel İstatistikler")

    # Toplam başvuru sayısı
    query = "SELECT COUNT(*) as count FROM basvurular"
    total_apps = db.fetchone(query)['count']
    st.metric("Toplam Başvuru", f"{total_apps:,}")

    # İşlenen başvuru sayısı
    query = "SELECT COUNT(*) as count FROM basvurular WHERE islendiMi = 1"
    processed_apps = db.fetchone(query)['count']
    st.metric("İşlenen Başvuru", f"{processed_apps:,}")

    # Başarılı analiz sayısı
    query = "SELECT COUNT(*) as count FROM belge_analiz_log WHERE basarili = 1"
    successful_analysis = db.fetchone(query)['count']
    st.metric("Başarılı Analiz", f"{successful_analysis:,}")

    # Kaydedilen chunk sayısı
    query = "SELECT COUNT(*) as count FROM chunk_sonuclari"
    total_chunks = db.fetchone(query)['count']
    st.metric("Kaydedilen Chunk", f"{total_chunks:,}")

# Ana içerik
if search_value:
    # Başvuruyu bul
    if search_type == "Takip No":
        query = """
            SELECT * FROM basvurular
            WHERE takipNo = ?
        """
        basvuru = db.fetchone(query, (search_value,))
    elif search_type == "Başvuru ID":
        query = """
            SELECT * FROM basvurular
            WHERE basvuruId = ?
        """
        basvuru = db.fetchone(query, (int(search_value),))
    elif search_type == "TC Kimlik":
        query = """
            SELECT * FROM basvurular
            WHERE basvuruYapanVatandasTC = ?
        """
        basvuru = db.fetchone(query, (search_value,))
    else:  # Ad Soyad
        query = """
            SELECT * FROM basvurular
            WHERE basvuruYapanAd || ' ' || basvuruYapanSoyad LIKE ?
        """
        basvuru = db.fetchone(query, (f"%{search_value}%",))

    if basvuru:
        # Başvuru bilgileri
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("📋 Başvuru Bilgileri")
            st.write(f"**Takip No:** {basvuru['takipNo']}")
            st.write(f"**Başvuru ID:** {basvuru['basvuruId']}")
            st.write(f"**Tarih:** {basvuru['basvuruTarihi'][:10] if basvuru['basvuruTarihi'] else 'N/A'}")

        with col2:
            st.subheader("👤 Başvuran Bilgileri")
            st.write(f"**Ad Soyad:** {basvuru['basvuruYapanAd']} {basvuru['basvuruYapanSoyad']}")
            st.write(f"**TC:** {basvuru['basvuruYapanVatandasTC']}")

        with col3:
            st.subheader("📊 Durum")
            durum_icon = "✅" if basvuru['islendiMi'] else "⏳"
            st.write(f"**İşlendi:** {durum_icon}")
            st.write(f"**Durum:** {basvuru['basvuruDurum']}")

        st.markdown("---")

        # Hizmet bilgisi
        st.info(f"**Hizmet:** {basvuru['hizmetAdi']} ({basvuru['hizmetId']})")

        if basvuru.get('kararDurum'):
            st.warning(f"**Karar:** {basvuru['kararDurum']}")

        st.markdown("---")

        # Belgeler ve Analizler
        st.header("📄 Belgeler ve Analiz Sonuçları")

        # Belgeleri getir
        query = """
            SELECT b.*,
                   l.id as log_id,
                   l.basarili,
                   l.islem_suresi_sn,
                   l.chunk_sayisi
            FROM belgeler b
            LEFT JOIN belge_analiz_log l ON b.belgeId = l.belgeId
            WHERE b.basvuruId = ?
            ORDER BY b.belgeId
        """
        belgeler = db.fetchall(query, (basvuru['basvuruId'],))

        # Belgeleri tab'lara ayır
        tabs = st.tabs([f"{b['belgeAdi']}" for b in belgeler if b['log_id']])

        tab_index = 0
        for belge in belgeler:
            if not belge['log_id']:
                continue

            with tabs[tab_index]:
                tab_index += 1

                # Belge bilgileri
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Analiz Durumu", "✅ Başarılı" if belge['basarili'] else "❌ Başarısız")
                with col2:
                    st.metric("Süre", f"{belge['islem_suresi_sn']:.2f}s")
                with col3:
                    st.metric("Chunk Sayısı", belge['chunk_sayisi'])

                st.markdown("---")

                # Chunk sonuçlarını getir
                query = """
                    SELECT chunk_index, response_json, chunk_start, chunk_end
                    FROM chunk_sonuclari
                    WHERE log_id = ?
                    ORDER BY chunk_index
                """
                chunks = db.fetchall(query, (belge['log_id'],))

                if chunks:
                    # Tüm chunk'ları birleştir (merge edilmiş sonuç)
                    if len(chunks) == 1:
                        st.subheader("📊 Analiz Sonucu")
                        data = json.loads(chunks[0]['response_json'])

                        # Belge tipine göre özel görüntüleme
                        display_analysis_result(belge['belgeAdi'], data)
                    else:
                        st.subheader(f"📊 Analiz Sonuçları ({len(chunks)} Chunk)")

                        # Her chunk'ı göster
                        for chunk in chunks:
                            with st.expander(f"Chunk {chunk['chunk_index']} (Karakter {chunk['chunk_start']}-{chunk['chunk_end']})"):
                                data = json.loads(chunk['response_json'])
                                display_analysis_result(belge['belgeAdi'], data)

                    # Ham JSON görüntüleme
                    with st.expander("🔍 Ham JSON Verisi"):
                        for chunk in chunks:
                            st.code(chunk['response_json'], language='json')
                else:
                    st.warning("Bu belge için chunk sonucu bulunamadı.")
    else:
        st.error(f"❌ {search_type} '{search_value}' için başvuru bulunamadı!")

else:
    # Başlangıç ekranı - Son başvurular
    st.header("📋 Son İşlenen Başvurular")

    query = """
        SELECT basvuruId, takipNo,
               basvuruYapanAd || ' ' || basvuruYapanSoyad as ad_soyad,
               basvuruTarihi,
               hizmetAdi,
               basvuruDurum
        FROM basvurular
        WHERE islendiMi = 1
        ORDER BY basvuruId DESC
        LIMIT 20
    """
    latest = db.fetchall(query)

    if latest:
        # Tablo oluştur
        for app in latest:
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

                with col1:
                    st.write(f"**{app['takipNo']}**")

                with col2:
                    st.write(app['ad_soyad'])

                with col3:
                    st.write(app['hizmetAdi'][:40] + "..." if len(app['hizmetAdi']) > 40 else app['hizmetAdi'])

                with col4:
                    if st.button("Görüntüle", key=f"view_{app['basvuruId']}"):
                        st.session_state.selected_basvuru_id = app['basvuruId']
                        st.rerun()

                st.markdown("---")


def display_analysis_result(belge_tipi: str, data: dict):
    """Belge tipine göre özelleştirilmiş sonuç görüntüleme"""

    if "CV" in belge_tipi or "Özgeçmiş" in belge_tipi:
        display_cv_result(data)
    elif "SGK" in belge_tipi:
        display_sgk_result(data)
    elif "Diploma" in belge_tipi:
        display_diploma_result(data)
    elif "Adli Sicil" in belge_tipi:
        display_adli_sicil_result(data)
    elif "Proje" in belge_tipi or "Yayın" in belge_tipi:
        display_proje_result(data)
    else:
        # Varsayılan görüntüleme
        display_default_result(data)


def display_cv_result(data: dict):
    """CV analiz sonucu görüntüleme"""

    # Kişisel Bilgiler
    st.subheader("👤 Kişisel Bilgiler")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Ad Soyad:** {data.get('ad_soyad', 'N/A')}")
        st.write(f"**Doğum Yılı:** {data.get('dogum_yili', 'N/A')}")
    with col2:
        st.write(f"**Email:** {data.get('iletisim_email', 'N/A')}")
        st.write(f"**Telefon:** {data.get('iletisim_telefon', 'N/A')}")

    # Eğitim Bilgileri
    st.subheader("🎓 Eğitim Bilgileri")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Seviye:** {data.get('egitim_seviyesi', 'N/A')}")
        st.write(f"**Üniversite:** {data.get('mezun_universite', 'N/A')}")
    with col2:
        st.write(f"**Bölüm:** {data.get('mezun_bolum', 'N/A')}")
        st.write(f"**Mezuniyet:** {data.get('mezuniyet_yili', 'N/A')}")
    with col3:
        st.write(f"**Akademik Ünvan:** {data.get('akademik_unvan', 'N/A')}")
        st.write(f"**Aktif Kurum:** {data.get('aktif_kurum', 'N/A')}")

    # Deneyim
    st.subheader("💼 İş Deneyimi")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Toplam Deneyim", f"{data.get('toplam_is_deneyimi_yil', 0)} yıl {data.get('toplam_is_deneyimi_ay', 0)} ay")
    with col2:
        sektorler = data.get('sektorler', [])
        st.write(f"**Sektörler:** {', '.join(sektorler) if sektorler else 'N/A'}")

    # Sektör Deneyimleri
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⚡ Enerji", f"{data.get('tecrube_enerji', 0)} yıl")
        st.metric("⚙️ Metal", f"{data.get('tecrube_metal', 0)} yıl")
    with col2:
        st.metric("🏔️ Mineral", f"{data.get('tecrube_mineral', 0)} yıl")
        st.metric("🧪 Kimya", f"{data.get('tecrube_kimya', 0)} yıl")
    with col3:
        st.metric("♻️ Atık", f"{data.get('tecrube_atik', 0)} yıl")
        st.metric("🏭 Diğer", f"{data.get('tecrube_diger', 0)} yıl")

    # İş Deneyimi Listesi
    if data.get('is_deneyimi_listesi'):
        st.subheader("📋 Detaylı İş Geçmişi")
        for exp in data['is_deneyimi_listesi']:
            with st.expander(f"{exp.get('pozisyon', 'N/A')} - {exp.get('kurum', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Sektör:** {exp.get('sektor', 'N/A')}")
                    st.write(f"**Başlangıç:** {exp.get('baslangic', 'N/A')}")
                with col2:
                    st.write(f"**Bitiş:** {exp.get('bitis', 'N/A')}")
                    st.write(f"**Süre:** {exp.get('sure_yil', 0)} yıl")
                if exp.get('gorev_tanimi'):
                    st.write(f"**Görev:** {exp['gorev_tanimi']}")

    # Projeler ve Yayınlar
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📚 Projeler")
        projeler = data.get('projeler', [])
        if projeler:
            for proje in projeler:
                st.write(f"- **{proje.get('baslik', 'N/A')}** ({proje.get('yil', 'N/A')})")
                st.write(f"  {proje.get('tur', 'N/A')} - Rol: {proje.get('rol', 'N/A')}")
        else:
            st.write("Proje bilgisi yok")

    with col2:
        st.subheader("📄 Yayınlar")
        yayinlar = data.get('yayinlar', [])
        if yayinlar:
            for yayin in yayinlar:
                st.write(f"- **{yayin.get('baslik', 'N/A')}** ({yayin.get('yil', 'N/A')})")
                st.write(f"  {yayin.get('tur', 'N/A')} - Atıf: {yayin.get('atif_sayisi', 0)}")
        else:
            st.write("Yayın bilgisi yok")

    # Yeşil Dönüşüm Tecrübesi
    st.subheader("🌱 Yeşil Dönüşüm Tecrübesi")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Yeşil Dönüşüm:** {'✅ Var' if data.get('yeşil_donusum_tecrubesi') else '❌ Yok'}")
    with col2:
        st.write(f"**Çevre Mevzuatı:** {'✅ Var' if data.get('cevre_mevzuati_bilgisi') else '❌ Yok'}")
    with col3:
        st.write(f"**Enerji Verimliliği:** {'✅ Var' if data.get('enerji_verimliligi_tecrubesi') else '❌ Yok'}")

    if data.get('yeşil_donusum_aciklama'):
        st.info(f"**Açıklama:** {data['yeşil_donusum_aciklama']}")


def display_sgk_result(data: dict):
    """SGK analiz sonucu görüntüleme"""

    st.subheader("💼 SGK İş Deneyimi Özeti")

    # Toplam deneyim
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Deneyim",
                  f"{data.get('toplam_is_deneyimi_yil', 0)} yıl {data.get('toplam_is_deneyimi_ay', 0)} ay")
    with col2:
        st.metric("Toplam Prim Günü", f"{data.get('toplam_prim_gun', 0):,}")
    with col3:
        st.metric("İlk İşe Giriş", data.get('ilk_ise_giris_tarihi', 'N/A'))

    # Sektör deneyimleri
    st.subheader("🏭 Sektör Bazında Deneyim")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⚡ Enerji", f"{data.get('tecrube_enerji_yil', 0)}y {data.get('tecrube_enerji_ay', 0)}a")
        st.metric("⚙️ Metal", f"{data.get('tecrube_metal_yil', 0)}y {data.get('tecrube_metal_ay', 0)}a")
    with col2:
        st.metric("🏔️ Mineral", f"{data.get('tecrube_mineral_yil', 0)}y {data.get('tecrube_mineral_ay', 0)}a")
        st.metric("🧪 Kimya", f"{data.get('tecrube_kimya_yil', 0)}y {data.get('tecrube_kimya_ay', 0)}a")
    with col3:
        st.metric("♻️ Atık", f"{data.get('tecrube_atik_yil', 0)}y {data.get('tecrube_atik_ay', 0)}a")
        st.metric("🏭 Diğer", f"{data.get('tecrube_diger_yil', 0)}y {data.get('tecrube_diger_ay', 0)}a")

    # İş deneyimi detayı
    if data.get('is_deneyimi_detay'):
        st.subheader("📋 Detaylı Çalışma Geçmişi")
        for exp in data['is_deneyimi_detay']:
            with st.expander(f"{exp.get('isyeri_adi', 'N/A')} ({exp.get('pozisyon', 'N/A')})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Sektör:** {exp.get('sektor', 'N/A')}")
                    st.write(f"**Başlangıç:** {exp.get('baslangic_tarihi', 'N/A')}")
                    st.write(f"**Bitiş:** {exp.get('bitis_tarihi', 'N/A')}")
                with col2:
                    st.write(f"**Çalışma Süresi:** {exp.get('calisma_yil', 0)} yıl {exp.get('calisma_ay', 0)} ay")
                    st.write(f"**Çalışma Günü:** {exp.get('calisma_gun', 0):,}")
                    st.write(f"**SGK Kodu:** {exp.get('sgk_kodu', 'N/A')}")
                if exp.get('is_kolu'):
                    st.info(f"**İş Kolu:** {exp['is_kolu']}")


def display_diploma_result(data: dict):
    """Diploma analiz sonucu görüntüleme"""

    st.subheader("🎓 Diploma Bilgileri")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Öğrenci:** {data.get('ogrenci_ad_soyad', 'N/A')}")
        st.write(f"**TC:** {data.get('tc_kimlik_no', 'N/A')}")
        st.write(f"**Üniversite:** {data.get('universite', 'N/A')} ({data.get('universite_tur', 'N/A')})")
        st.write(f"**Fakülte:** {data.get('fakulte', 'N/A')}")
        st.write(f"**Bölüm:** {data.get('bolum', 'N/A')}")

    with col2:
        st.write(f"**Eğitim Seviyesi:** {data.get('egitim_seviyesi', 'N/A')}")
        st.write(f"**Mezuniyet Yılı:** {data.get('mezuniyet_yili', 'N/A')}")
        st.write(f"**Mezuniyet Tarihi:** {data.get('mezuniyet_tarihi', 'N/A')}")
        st.write(f"**Diploma No:** {data.get('diploma_no', 'N/A')}")
        st.write(f"**GANO:** {data.get('genel_not_ortalamasi', 'N/A')} ({data.get('not_sistemi', 'N/A')})")

    # Tez bilgileri (varsa)
    if data.get('tez_basligi'):
        st.subheader("📚 Tez Bilgileri")
        st.write(f"**Başlık:** {data['tez_basligi']}")
        if data.get('tez_danisman'):
            st.write(f"**Danışman:** {data['tez_danisman']}")
        if data.get('tez_tarihi'):
            st.write(f"**Tarih:** {data['tez_tarihi']}")


def display_adli_sicil_result(data: dict):
    """Adli sicil analiz sonucu görüntüleme"""

    st.subheader("⚖️ Adli Sicil Kaydı")

    # Durum
    has_record = data.get('adli_sicil_varmi', False)
    if has_record:
        st.error("❌ Adli sicil kaydı VAR")
    else:
        st.success("✅ Adli sicil kaydı YOK")

    # Kişi bilgileri
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Ad Soyad:** {data.get('ad_soyad', 'N/A')}")
        st.write(f"**TC:** {data.get('tc_kimlik_no', 'N/A')}")
        st.write(f"**Baba Adı:** {data.get('baba_adi', 'N/A')}")
        st.write(f"**Ana Adı:** {data.get('ana_adi', 'N/A')}")

    with col2:
        st.write(f"**Doğum Tarihi:** {data.get('dogum_tarihi', 'N/A')}")
        st.write(f"**Doğum Yeri:** {data.get('dogum_yeri', 'N/A')}")
        st.write(f"**Belge No:** {data.get('belge_no', 'N/A')}")
        st.write(f"**Belge Tarihi:** {data.get('belge_tarihi', 'N/A')}")

    if data.get('aciklama'):
        st.info(f"**Açıklama:** {data['aciklama']}")


def display_proje_result(data: dict):
    """Proje/Yayın analiz sonucu görüntüleme"""

    st.subheader("📚 Proje ve Yayın Bilgileri")

    # Projeler
    if data.get('projeler'):
        st.subheader("🔬 Projeler")
        for proje in data['projeler']:
            with st.expander(f"{proje.get('baslik', 'N/A')} ({proje.get('yil', 'N/A')})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Tür:** {proje.get('tur', 'N/A')}")
                    st.write(f"**Kurum:** {proje.get('kurum', 'N/A')}")
                    st.write(f"**Rol:** {proje.get('rol', 'N/A')}")
                with col2:
                    st.write(f"**Bütçe:** {proje.get('butce', 'N/A')}")
                if proje.get('aciklama'):
                    st.write(f"**Açıklama:** {proje['aciklama']}")

    # Yayınlar
    if data.get('yayinlar'):
        st.subheader("📄 Yayınlar")
        for yayin in data['yayinlar']:
            with st.expander(f"{yayin.get('baslik', 'N/A')} ({yayin.get('yil', 'N/A')})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Tür:** {yayin.get('tur', 'N/A')}")
                    st.write(f"**Dergi/Konferans:** {yayin.get('dergi_konferans', 'N/A')}")
                with col2:
                    st.write(f"**Atıf Sayısı:** {yayin.get('atif_sayisi', 0)}")
                    if yayin.get('doi'):
                        st.write(f"**DOI:** {yayin['doi']}")


def display_default_result(data: dict):
    """Varsayılan görüntüleme - tüm alanları listele"""

    for key, value in data.items():
        if isinstance(value, (list, dict)):
            st.subheader(key)
            st.json(value)
        else:
            st.write(f"**{key}:** {value}")


if __name__ == "__main__":
    st.sidebar.markdown("---")
    st.sidebar.info("💡 Başvuru aramak için sol menüdeki filtreleri kullanın.")
