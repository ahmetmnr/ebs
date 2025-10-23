@echo off
echo ========================================
echo  Yeşil Dönüşüm Analiz Sonuçları Viewer
echo ========================================
echo.
echo Web arayüzü başlatılıyor...
echo Tarayıcınızda otomatik olarak açılacak.
echo.
echo Kapatmak için Ctrl+C tuşlarına basın.
echo ========================================
echo.

streamlit run web_viewer.py --server.port 8501 --server.address localhost

pause
