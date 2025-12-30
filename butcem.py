import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Net Bütçe", page_icon="💵", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def baglanti_kur():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets ayarları eksik!")
        st.stop()
    
    secrets = st.secrets["gcp_service_account"]
    creds_dict = {
        "type": secrets["type"],
        "project_id": secrets["project_id"],
        "private_key_id": secrets["private_key_id"],
        "private_key": secrets["private_key"],
        "client_email": secrets["client_email"],
        "client_id": secrets["client_id"],
        "auth_uri": secrets["auth_uri"],
        "token_uri": secrets["token_uri"],
        "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": secrets["client_x509_cert_url"]
    }
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    try:
        return client.open("ButceVerileri").sheet1
    except:
        st.error("Google Sheets dosyası bulunamadı.")
        st.stop()

# --- VERİ ÇEKME ---
try:
    sheet = baglanti_kur()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    beklenen = ["Tur", "Isim", "Adet", "Fiyat"]
    if df.empty or not all(col in df.columns for col in beklenen):
        if len(data) == 0:
            sheet.clear()
            sheet.append_row(beklenen)
            st.rerun()
except:
    df = pd.DataFrame(columns=["Tur", "Isim", "Adet", "Fiyat"])

# --- ARAYÜZ ---
st.title("💰 Kurşun Geçirmez Bütçe (V3)")
st.caption("Virgülleri ve noktaları otomatik düzeltir.")
st.markdown("---")

# YAN MENÜ
with st.sidebar:
    st.header("➕ Varlık Ekle")
    with st.form("ekle", clear_on_submit=True):
        tur = st.selectbox("Tür", ["Hisse", "Fon", "Altın/Döviz", "Nakit"])
        isim = st.text_input("İsim", placeholder="Örn: TTE")
        
        # Kullanıcı buraya "10,5" veya "1.000" yazabilir, biz metin (string) olarak alacağız
        adet_giris = st.text_input("Adet", value="0")
        fiyat_giris = st.text_input("Fiyat", value="0")
        
        submitted = st.form_submit_button("Kaydet")
        
        if submitted:
            if isim:
                # Veriyi olduğu gibi (virgüllü de olsa) Sheets'e atıyoruz.
                # Hesaplarken düzelteceğiz.
                sheet.append_row([tur, isim, adet_giris, fiyat_giris])
                st.success("Eklendi!")
                st.rerun()

# --- KRİTİK BÖLÜM: HESAPLAMA ---
if not df.empty:
    
    # 1. ADIM: Temizlik (String -> Float Dönüşümü)
    # Türkiye standardı: Nokta binlik (yoksay), Virgül ondalık (nokta yap)
    # Örn: "1.000,50" -> "1000.50"
    
    for col in ["Adet", "Fiyat"]:
        # Önce her şeyi string (yazı) yap
        df[col] = df[col].astype(str)
        # Noktaları sil (1.000 -> 1000)
        df[col] = df[col].str.replace(".", "", regex=False)
        # Virgülleri nokta yap (10,5 -> 10.5)
        df[col] = df[col].str.replace(",", ".", regex=False)
        # Sayıya çevir, çeviremezsen 0 yaz
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # 2. ADIM: Artık hepsi matematiksel sayı. Çarpabiliriz.
    df["Toplam"] = df["Adet"] * df["Fiyat"]
    genel_toplam = df["Toplam"].sum()

    # GÖSTERGE
    col1, col2 = st.columns(2)
    col1.metric("TOPLAM VARLIK", f"{genel_toplam:,.2f} ₺")
    
    st.dataframe(df)
    
    # SİLME BUTONU
    if len(df) > 0:
        silinecek = st.selectbox("Silinecek:", ["Seçiniz..."] + df["Isim"].tolist())
        if silinecek != "Seçiniz..." and st.button("Sil"):
            cell = sheet.find(silinecek)
            sheet.delete_rows(cell.row)
            st.rerun()
else:
    st.info("Tablo boş.")
