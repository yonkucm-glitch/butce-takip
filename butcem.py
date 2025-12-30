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
    
    scope = ["
