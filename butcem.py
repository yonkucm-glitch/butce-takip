import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Canlı Bütçe", page_icon="💰", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def baglanti_kur():
    # Secrets kontrolü
    if "gcp_service_account" not in st.secrets:
        st.error("Streamlit Secrets ayarları yapılmamış! Lütfen Settings -> Secrets kısmına JSON bilgilerini gir.")
        st.stop()
        
    secrets_dict = st.secrets["gcp_service_account"]
    
    # Kimlik doğrulama
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
    
    # Tabloyu aç (İsim hatası olursa uyar)
    try:
        sheet = client.open("ButceVerileri").sheet1
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("HATA: Google Sheets'te 'ButceVerileri' adında bir dosya bulunamadı. Lütfen dosya adını kontrol et.")
        st.stop()

# --- VERİ ÇEKME VE OTOMATİK DÜZELTME ---
try:
    sheet = baglanti_kur()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Eğer tablo boşsa veya başlıklar eksikse OTOMATİK DÜZELT
    beklenen_basliklar = ["Tur", "Isim", "Adet", "Fiyat"]
    mevcut_basliklar = df.columns.tolist()
    
    # Tablo tamamen boşsa veya başlıklar yanlışsa
    if df.empty or not all(col in mevcut_basliklar for col in beklenen_basliklar):
        # Eğer veri yoksa başlıkları biz yazalım
        if len(data) == 0:
            sheet.clear() # Temizle
            sheet.append_row(beklenen_basliklar) # Doğrusunu yaz
            st.toast("Tablo başlıkları otomatik oluşturuldu! Sayfa yenileniyor...")
            st.rerun() # Sayfayı yenile
            
except Exception as e:
    st.warning(f"Bağlantı kurulurken bir pürüz çıktı ama hallediyoruz... ({e})")
    # Kritik hata durumunda boş dataframe oluştur ki site çökmesin
    df = pd.DataFrame(columns=["Tur", "Isim", "Adet", "Fiyat"])

# --- UYGULAMA ARAYÜZÜ ---
st.title("💸 Kişisel Finans Takipçisi")
st.markdown("---")

# Yan Menü: Veri Ekleme
with st.sidebar:
    st.header("➕ Yeni Varlık Ekle")
    with st.form("ekle_form", clear_on_submit=True):
        tur = st.selectbox("Tür Seç", ["Hisse", "Fon", "Altın/Döviz", "Nakit"])
        isim = st.text_input("Varlık Adı (Örn: TTE, Gram Altın)")
        adet = st.number_input("Adet", min_value=0.0, step=0.01)
        fiyat = st.number_input("Güncel Fiyat (TL)", min_value=0.0, step=0.1)
        
        if st.form_submit_button("Listeye Ekle"):
            if isim and adet > 0:
                sheet.append_row([tur, isim, adet, fiyat])
                st.success(f"{isim} eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen isim ve adet giriniz.")

# --- HESAPLAMALAR ---
if not df.empty:
    # Sayısal dönüşümler (Hata önleyici)
    df["Adet"] = pd.to_numeric(df["Adet"], errors='coerce').fillna(0)
    df["Fiyat"] = pd.to_numeric(df["Fiyat"], errors='coerce').fillna(0)
    df["Toplam"] = df["Adet"] * df["Fiyat"]
    
    toplam_varlik = df["Toplam"].sum()
    
    # Kartlar
    col1, col2, col3 = st.columns(3)
    col1.metric("TOPLAM VARLIK", f"{toplam_varlik:,.2f} ₺")
    
    en_degerli = df.loc[df["Toplam"].idxmax()] if len(df) > 0 else None
    if en_degerli is not None:
        col2.metric("En Değerli Varlık", f"{en_degerli['Isim']}")
        col3.metric("Değeri", f"{en_degerli['Toplam']:,.2f} ₺")

    st.markdown("---")
    
    # Tablo ve Silme Butonları
    st.subheader("📋 Varlıklarınız")
    
    # Her satırın yanına silme butonu koymak zor olduğu için seçerek silme yapalım
    varliklar_listesi = df["Isim"].tolist()
    if varliklar_listesi:
        silinecek = st.selectbox("Silmek istediğin varlığı seç:", ["Seçiniz..."] + varliklar_listesi)
        if silinecek != "Seçiniz...":
            if st.button(f"🗑️ '{silinecek}' adlı kaydı sil"):
                # Google Sheets'te bul ve sil (Satır numarası bulmaca)
                cell = sheet.find(silinecek)
                sheet.delete_rows(cell.row)
                st.success("Silindi!")
                st.rerun()

    st.dataframe(df, use_container_width=True)

else:
    st.info("Henüz bir varlık eklemediniz. Sol menüden ekleme yapabilirsiniz.")
