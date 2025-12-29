import streamlit as st
import pandas as pd

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Kişisel Bütçe Takip", page_icon="💰", layout="wide")

# Başlık
st.title("💸 Kişisel Finans ve Birikim Paneli")
st.markdown("---")

# --- SOL MENÜ (GENEL GİRDİLER) ---
st.sidebar.header("⚙️ Genel Ayarlar")

maas = st.sidebar.number_input("Aylık Net Gelir (Maaş+Burs)", min_value=0.0, value=14700.0, step=500.0)
gider = st.sidebar.number_input("Aylık Tahmini Gider", min_value=0.0, value=3800.0, step=100.0)
sure = st.sidebar.number_input("Kaç Aydır Birikim Yapıyorsun?", min_value=1, value=1)

# --- ANA EKRAN: VARLIK GİRİŞLERİ ---
col1, col2, col3 = st.columns(3)

def tablo_olustur(baslik, key_name):
    """Kullanıcının satır ekleyip çıkarabileceği dinamik tablo"""
    st.subheader(baslik)
    # Varsayılan boş bir şablon
    df_sablon = pd.DataFrame(columns=["Varlık İsmi", "Adet", "Birim Fiyat"])
    
    # Tabloyu ekranda göster ve düzenlenebilir yap
    config = {
        "Varlık İsmi": st.column_config.TextColumn("İsim", help="Örn: TTE, Gram Altın, THYAO"),
        "Adet": st.column_config.NumberColumn("Adet", min_value=0, format="%.2f"),
        "Birim Fiyat": st.column_config.NumberColumn("Fiyat (TL)", min_value=0, format="%.2f ₺"),
    }
    
    # Kullanıcıdan gelen veriyi al
    duzenlenmis_df = st.data_editor(
        df_sablon,
        key=key_name,
        column_config=config,
        num_rows="dynamic", # Satır ekle/sil özelliği
        use_container_width=True
    )
    
    # Toplam değeri hesapla
    if not duzenlenmis_df.empty:
        duzenlenmis_df["Toplam Değer"] = duzenlenmis_df["Adet"] * duzenlenmis_df["Birim Fiyat"]
        toplam = duzenlenmis_df["Toplam Değer"].sum()
    else:
        toplam = 0.0
        
    st.info(f"Bu Kategori Toplamı: {toplam:,.2f} ₺")
    return toplam

with col1:
    st.markdown("### 📈 Hisseler")
    st.caption("Borsa İstanbul / ABD Hisseleri")
    toplam_hisse = tablo_olustur("", "hisse_tablosu")

with col2:
    st.markdown("### 📊 Fonlar")
    st.caption("TEFAS Yatırım Fonları")
    toplam_fon = tablo_olustur("", "fon_tablosu")

with col3:
    st.markdown("### 🥇 Kıymetli Madenler")
    st.caption("Altın, Gümüş vb.")
    toplam_maden = tablo_olustur("", "maden_tablosu")

st.markdown("---")

# --- HESAPLAMALAR ---
toplam_birikim_varlik = toplam_hisse + toplam_fon + toplam_maden
toplam_gelir_surec = maas * sure
toplam_gider_surec = gider * sure
net_nakit_akisi = toplam_gelir_surec - toplam_gider_surec # Sadece maaştan artanlar

# Gerçek Net Varlık (Birikmiş Varlıklar + (Gelir-Gider'den kalan nakit))
# Not: Burada basitlik adına "Birikimlerim" kısmını ana varlık kabul ediyoruz.
genel_toplam_varlik = toplam_birikim_varlik

# --- SONUÇ PANOSU (DASHBOARD) ---
st.header("📊 Finansal Özet")

k1, k2, k3, k4 = st.columns(4)

k1.metric(label="Toplam Gelir (Süre Bazlı)", value=f"{toplam_gelir_surec:,.2f} ₺", delta=f"{sure} Ay")
k2.metric(label="Toplam Gider (Süre Bazlı)", value=f"{toplam_gider_surec:,.2f} ₺", delta="-Gider", delta_color="inverse")
k3.metric(label="Maaştan Kalan Teorik Nakit", value=f"{net_nakit_akisi:,.2f} ₺", help="Gelir - Gider")
k4.metric(label="TOPLAM BİRİKİM DEĞERİ", value=f"{genel_toplam_varlik:,.2f} ₺", delta="Net Varlık")

# Görsel Grafik (Pasta Grafiği)
if genel_toplam_varlik > 0:
    st.markdown("### Varlık Dağılımı")
    data = {
        "Kategori": ["Hisseler", "Fonlar", "Kıymetli Madenler"],
        "Değer": [toplam_hisse, toplam_fon, toplam_maden]
    }
    df_chart = pd.DataFrame(data)
    st.bar_chart(df_chart, x="Kategori", y="Değer")
