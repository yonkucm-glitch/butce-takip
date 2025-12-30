import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI (Web Sekmesinde Yazan İsim) ---
st.set_page_config(page_title="Bütçe Takibi.com", page_icon="💰", layout="wide")

# --- ZORLAYICI ÇEVİRİCİ MOTORU ---
def tr_formatini_duzelt(deger):
    """
    Bu fonksiyon veriye acımaz. Ne gelirse gelsin sayıya çevirir.
    Girdi: "1.500,50" -> Çıktı: 1500.50
    Girdi: "10,5"     -> Çıktı: 10.5
    Girdi: 100        -> Çıktı: 100.0
    """
    if deger == "" or pd.isna(deger):
        return 0.0
    
    # Zaten sayıysa (int/float) direkt döndür
    if isinstance(deger, (int, float)):
        return float(deger)
    
    # Önce metne çevirip kenar boşluklarını al
    s = str(deger).strip()
    
    # 1. Adım: Binlik ayracı olan NOKTAYI sil (1.000 -> 1000)
    s = s.replace(".", "")
    
    # 2. Adım: Ondalık ayracı olan VİRGÜLÜ noktaya çevir (10,5 -> 10.5)
    s = s.replace(",", ".")
    
    # 3. Adım: Çevirmeyi dene
    try:
        return float(s)
    except:
        return 0.0

# --- BAĞLANTI AYARLARI ---
@st.cache_resource
def baglan():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets ayarları yok!")
        st.stop()
    secrets = st.secrets["gcp_service_account"]
    
    # JSON yapısını oluştur
    creds_dict = {k: v for k, v in secrets.items()}
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("ButceVerileri").sheet1

# --- VERİ İŞLEME ---
try:
    sheet = baglan()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Başlık kontrolü
    if df.empty or "Fiyat" not in df.columns:
        if len(data) == 0:
            sheet.clear()
            sheet.append_row(["Tur", "Isim", "Adet", "Fiyat"])
            st.rerun()

except:
    df = pd.DataFrame(columns=["Tur", "Isim", "Adet", "Fiyat"])

# --- ARAYÜZ ---
st.title("💰 Bütçe Takibi.com")
st.info("Virgül (,) kuruş için, Nokta (.) binlik ayracı için kullanılır veya yoksayılır.")

with st.sidebar:
    st.header("➕ Ekle")
    with st.form("ekle", clear_on_submit=True):
        tur = st.selectbox("Tür", ["Hisse", "Fon", "Altın/Döviz", "Nakit"])
        isim = st.text_input("İsim (Örn: TTE)")
        # String olarak alıyoruz ki Python karışmasın
        adet_gir = st.text_input("Adet", value="0") 
        fiyat_gir = st.text_input("Fiyat", value="0")
        
        if st.form_submit_button("Kaydet"):
            # Kaydederken hiçbir şeye dokunmadan ham haliyle gönderiyoruz
            sheet.append_row([tur, isim, adet_gir, fiyat_gir])
            st.success("Eklendi!")
            st.rerun()

# --- HESAPLAMA MOTORU ---
if not df.empty:
    # Pandas'a diyoruz ki: "Bu sütunlardaki her bir hücreyi tek tek al ve fonksiyonumdan geçir"
    # Bu işlem, çarpma işleminden ÖNCE yapılır.
    df["Adet_Sayi"] = df["Adet"].apply(tr_formatini_duzelt)
    df["Fiyat_Sayi"] = df["Fiyat"].apply(tr_formatini_duzelt)
    
    # Artık garanti sayı olan yeni sütunları çarpıyoruz
    df["Toplam"] = df["Adet_Sayi"] * df["Fiyat_Sayi"]
    
    genel_toplam = df["Toplam"].sum()
    
    col1, col2 = st.columns(2)
    col1.metric("NET VARLIK", f"{genel_toplam:,.2f} ₺")
    
    # Tabloyu göster (Okunaklı olsun diye)
    gosterim_df = df[["Tur", "Isim", "Adet", "Fiyat", "Toplam"]].copy()
    gosterim_df["Toplam"] = gosterim_df["Toplam"].map('{:,.2f}'.format)
    st.dataframe(gosterim_df, use_container_width=True)
    
    # Silme
    secilen = st.selectbox("Silinecek:", ["Seçim Yap..."] + df["Isim"].unique().tolist())
    if secilen != "Seçim Yap..." and st.button("Kaydı Sil"):
        cell = sheet.find(secilen)
        sheet.delete_rows(cell.row)
        st.rerun()
else:
    st.warning("Listeniz boş.")
