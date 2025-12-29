import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Net Hesap", page_icon="🧮", layout="wide")

# --- KESİN ÇÖZÜM FONKSİYONU ---
def metni_sayiya_zorla(deger):
    """
    Gelen veri ne olursa olsun (virgüllü yazı, noktalı yazı, hatalı giriş)
    bunu mutlaka matematiksel sayıya (float) çevirir.
    Çeviremezse 0.0 döndürür, asla hata vermez.
    """
    try:
        # 1. Veri zaten sayıysa (int/float) elleme, geri gönder
        if isinstance(deger, (int, float)):
            return float(deger)
        
        # 2. Veri metinse string'e çevir
        s = str(deger).strip()
        
        # 3. Virgülleri noktaya çevir (Türkiye standardını dünya standardına çevir)
        # Örn: "4,20" -> "4.20"
        s = s.replace(",", ".")
        
        # 4. İçinde sayı ve nokta harici her şeyi temizle (Örn: "100 TL" -> "100")
        s = ''.join(c for c in s if c.isdigit() or c == '.')
        
        # 5. Boş kaldıysa 0 dön
        if not s:
            return 0.0
            
        return float(s)
    except:
        return 0.0

# --- GOOGLE SHEETS BAĞLANTISI ---
@st.cache_resource
def baglanti_kur():
    # Secrets kontrolü
    if "gcp_service_account" not in st.secrets:
        st.error("Lütfen Streamlit Secrets ayarlarını yapınız.")
        st.stop()
        
    secrets_dict = st.secrets["gcp_service_account"]
    
    # Kimlik bilgileri sözlüğü oluştur
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
    except:
        st.error("Google Sheets dosyası bulunamadı. Adın 'ButceVerileri' olduğundan emin ol.")
        st.stop()

# --- VERİ ÇEKME ---
try:
    sheet = baglanti_kur()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Tablo boşsa veya başlıklar yoksa düzelt
    beklenen = ["Tur", "Isim", "Adet", "Fiyat"]
    if df.empty or not all(col in df.columns for col in beklenen):
        if len(data) == 0:
            sheet.clear()
            sheet.append_row(beklenen)
            st.rerun()
            
except Exception as e:
    df = pd.DataFrame(columns=["Tur", "Isim", "Adet", "Fiyat"])

# --- ARAYÜZ ---
st.title("💰 Kurşun Geçirmez Bütçe Takibi")
st.markdown("---")

# YAN MENÜ
with st.sidebar:
    st.header("➕ Ekleme Paneli")
    with st.form("ekle_form", clear_on_submit=True):
        tur = st.selectbox("Tür", ["Hisse", "Fon", "Altın/Döviz", "Nakit"])
        isim = st.text_input("Varlık Adı", placeholder="Örn: TTE")
        
        # Burası önemli: String olarak alıyoruz, aşağıda zorla sayıya çevireceğiz
        adet_txt = st.text_input("Adet", placeholder="Örn: 1000")
        fiyat_txt = st.text_input("Birim Fiyat", placeholder="Örn: 4,20")
        
        btn = st.form_submit_button("Kaydet")
        
        if btn:
            # Önce temizle ve sayıya çevir
            temiz_adet = metni_sayiya_zorla(adet_txt)
            temiz_fiyat = metni_sayiya_zorla(fiyat_txt)
            
            if isim and temiz_adet > 0:
                # Google Sheets'e düzgün formatta (noktalı) kaydet
                sheet.append_row([tur, isim, temiz_adet, temiz_fiyat])
                st.success("Kaydedildi!")
                st.rerun()
            else:
                st.warning("Lütfen geçerli değerler giriniz.")

# --- TABLO VE HESAPLAMA ---
if not df.empty:
    st.subheader("📋 Varlıklarınız")
    
    # 1. ADIM: Tablodaki her şeyi sayıya zorla (Metin kalmasın!)
    df["Adet"] = df["Adet"].apply(metni_sayiya_zorla)
    df["Fiyat"] = df["Fiyat"].apply(metni_sayiya_zorla)
    
    # 2. ADIM: Matematik (Artık hata veremez, çünkü hepsi sayı)
    df["Toplam"] = df["Adet"] * df["Fiyat"]
    
    genel_toplam = df["Toplam"].sum()
    
    # Göstergeler
    col1, col2 = st.columns(2)
    col1.metric("TOPLAM VARLIK", f"{genel_toplam:,.2f} ₺")
    
    # Silme İşlemi
    varliklar = df["Isim"].unique().tolist()
    silinecek = st.selectbox("Silinecek Kayıt:", ["Seçiniz..."] + varliklar)
    
    if silinecek != "Seçiniz...":
        if st.button("🗑️ Sil"):
            cell = sheet.find(silinecek)
            sheet.delete_rows(cell.row)
            st.success("Silindi!")
            st.rerun()

    st.dataframe(df, use_container_width=True)

else:
    st.info("Tablo şu an boş.")
    if st.button("Tabloyu Sıfırla (Başlıkları Onar)"):
        sheet.clear()
        sheet.append_row(["Tur", "Isim", "Adet", "Fiyat"])
        st.rerun()
