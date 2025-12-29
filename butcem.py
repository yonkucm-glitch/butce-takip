import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Canlı Bütçe", page_icon="💰", layout="wide")

# --- YARDIMCI FONKSİYON: VİRGÜL DÜZELTİCİ ---
def sayiya_cevir(deger):
    """
    Kullanıcı '10,5' de yazsa '10.5' de yazsa bunu doğru sayıya (float) çevirir.
    Hatalı giriş olursa 0.0 döndürür.
    """
    if not deger:
        return 0.0
    try:
        # Eğer zaten sayıysa direkt döndür
        if isinstance(deger, (int, float)):
            return float(deger)
        
        # Eğer metinse (str), önce virgülü noktaya çevir, sonra sayı yap
        deger_str = str(deger)
        deger_str = deger_str.replace(",", ".") # İşte sihirli değnek burası!
        return float(deger_str)
    except:
        return 0.0

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def baglanti_kur():
    # Secrets kontrolü
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets ayarları eksik!")
        st.stop()
        
    secrets_dict = st.secrets["gcp_service_account"]
    creds_dict = {
        "type": secrets_dict["type"],
        "project_id": secrets_dict["project_id"],
        "private_key_id": secrets_dict["private_key_id"],
        "private_key": secrets_dict["private_key"],
        "client_email": secrets_dict["client_email"],
        "client_id": secrets_dict["client_id"],
        "auth_uri": secrets_dict["auth_uri"],
        "token_uri": secrets_dict["token_uri"],
        "auth_provider_x509_cert_url": secrets_dict["auth_provider_x509_cert_url"],
        "client_x509_cert_url": secrets_dict["client_x509_cert_url"]
    }
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open("ButceVerileri").sheet1
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("Google Sheets dosyası bulunamadı.")
        st.stop()

# --- VERİ ÇEKME ---
try:
    sheet = baglanti_kur()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Başlık kontrolü ve otomatik düzeltme
    beklenen_basliklar = ["Tur", "Isim", "Adet", "Fiyat"]
    if df.empty or not all(col in df.columns for col in beklenen_basliklar):
        if len(data) == 0:
            sheet.clear()
            sheet.append_row(beklenen_basliklar)
            st.rerun()

except Exception as e:
    df = pd.DataFrame(columns=["Tur", "Isim", "Adet", "Fiyat"])

# --- UYGULAMA ARAYÜZÜ ---
st.title("💸 Kişisel Finans Takipçisi")
st.markdown("---")

# YAN MENÜ (Artık Metin Kutusu Kullanıyoruz - Virgül Serbest!)
with st.sidebar:
    st.header("➕ Yeni Varlık Ekle")
    with st.form("ekle_form", clear_on_submit=True):
        tur = st.selectbox("Tür Seç", ["Hisse", "Fon", "Altın/Döviz", "Nakit"])
        isim = st.text_input("Varlık Adı (Örn: TTE, Gram Altın)")
        
        # BURASI DEĞİŞTİ: Sayı kutusu yerine yazı kutusu (text_input) koyduk
        # Böylece virgül koysan da hata vermeyecek, biz düzelteceğiz.
        adet_giris = st.text_input("Adet (Örn: 10 veya 10,5)", value="0")
        fiyat_giris = st.text_input("Güncel Fiyat (TL) (Örn: 4,20)", value="0")
        
        if st.form_submit_button("Listeye Ekle"):
            # Arka planda çeviriyoruz
            adet_temiz = sayiya_cevir(adet_giris)
            fiyat_temiz = sayiya_cevir(fiyat_giris)
            
            if isim and adet_temiz > 0:
                # Google Sheets'e düzeltilmiş (noktalı) halini kaydediyoruz
                sheet.append_row([tur, isim, adet_temiz, fiyat_temiz])
                st.success(f"{isim} eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen geçerli bir isim ve adet giriniz.")

# --- HESAPLAMALAR ---
if not df.empty:
    # Tablodaki eski verileri de temizleyip hesaplayalım
    # (Google Sheets'te elle virgüllü yazılmış olsa bile düzeltir)
    df["Adet"] = df["Adet"].apply(sayiya_cevir)
    df["Fiyat"] = df["Fiyat"].apply(sayiya_cevir)
    
    df["Toplam"] = df["Adet"] * df["Fiyat"]
    
    toplam_varlik = df["Toplam"].sum()
    
    col1, col2 = st.columns(2)
    col1.metric("TOPLAM VARLIK", f"{toplam_varlik:,.2f} ₺")
    col2.info("Veriler otomatik olarak sayıya çevrildi.")

    st.markdown("---")
    st.subheader("📋 Varlıklarınız")
    
    # Silme Fonksiyonu
    varliklar_listesi = df["Isim"].tolist()
    if varliklar_listesi:
        silinecek = st.selectbox("Silmek istediğin varlığı seç:", ["Seçiniz..."] + varliklar_listesi)
        if silinecek != "Seçiniz...":
            if st.button(f"🗑️ '{silinecek}' adlı kaydı sil"):
                cell = sheet.find(silinecek)
                sheet.delete_rows(cell.row)
                st.success("Silindi!")
                st.rerun()

    st.dataframe(df, use_container_width=True)
else:
    st.info("Listeniz boş.")
