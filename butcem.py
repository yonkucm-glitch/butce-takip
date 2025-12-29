import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- AYARLAR ---
st.set_page_config(page_title="Canlı Bütçe Takip", page_icon="💰", layout="wide")
st.title("💸 Kişisel Finans (Google Sheets Bağlantılı)")

# --- GOOGLE SHEETS BAĞLANTISI ---
# Bu fonksiyon bağlantıyı önbelleğe alır, böylece her işlemde tekrar bağlanmaz.
@st.cache_resource
def tabloya_baglan():
    # Secrets'tan verileri al
    secrets_dict = st.secrets["gcp_service_account"]
    
    # JSON formatına uygun sözlük oluştur
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
    
    # Tabloyu aç (Tablo adının Google Sheets'teki adla BİREBİR aynı olduğundan emin ol)
    sheet = client.open("ButceVerileri").sheet1 
    return sheet

# Verileri Çek
try:
    sheet = tabloya_baglan()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.stop()

# Eğer tablo boşsa DataFrame yapısını biz kuralım
if df.empty:
    df = pd.DataFrame(columns=["Tur", "Isim", "Adet", "Fiyat"])

# --- YENİ VERİ EKLEME PANELİ ---
st.sidebar.header("➕ Yeni Varlık Ekle")

with st.sidebar.form("ekle_form"):
    tur = st.selectbox("Tür", ["Hisse", "Fon", "Altın/Döviz"])
    isim = st.text_input("Varlık İsmi (Örn: TTE)")
    adet = st.number_input("Adet", min_value=0.0, step=0.1)
    fiyat = st.number_input("Birim Fiyat (TL)", min_value=0.0, step=0.1)
    
    submit = st.form_submit_button("Kaydet")

    if submit:
        if isim and adet > 0:
            # Google Sheets'e yeni satır ekle
            yeni_veri = [tur, isim, adet, fiyat]
            sheet.append_row(yeni_veri)
            st.success("Kaydedildi! Tablo yenileniyor...")
            st.rerun() # Sayfayı yenile ki yeni veriyi görelim
        else:
            st.warning("Lütfen isim ve adet giriniz.")

# --- RAKAMLARI HESAPLA ---
if not df.empty:
    # Sayıları sayı formatına çevir (Bazen metin olarak gelebilir)
    df["Adet"] = pd.to_numeric(df["Adet"])
    df["Fiyat"] = pd.to_numeric(df["Fiyat"])
    df["Toplam"] = df["Adet"] * df["Fiyat"]
    
    toplam_varlik = df["Toplam"].sum()
    
    # Kategori bazlı grupla
    ozet = df.groupby("Tur")["Toplam"].sum()
else:
    toplam_varlik = 0
    ozet = pd.Series()

# --- GÖSTERGE PANELİ ---
col1, col2 = st.columns(2)
col1.metric("TOPLAM VARLIK", f"{toplam_varlik:,.2f} TL")
col2.write("Son güncellenen veriler Google Sheets'ten çekildi.")

st.markdown("---")

# --- DETAYLI TABLO ---
st.subheader("📋 Varlık Listesi")
st.dataframe(df, use_container_width=True)

# --- SİLME İŞLEMİ (Opsiyonel) ---
st.markdown("---")
st.subheader("🗑️ Veri Temizle")
if st.button("Tüm Verileri Sil (Dikkat!)"):
    sheet.clear()
    # Başlıkları tekrar ekle
    sheet.append_row(["Tur", "Isim", "Adet", "Fiyat"])
    st.rerun()
