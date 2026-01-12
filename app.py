import streamlit as st
import pandas as pd
import time
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="AUV PID Simülasyonu", layout="wide")

# --- CSS İLE GÖRSEL DÜZENLEME ---
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- BAŞLIK ---
st.title("🌊 Otonom Sualtı Aracı: PID Kontrol & Fizik Animasyonu")
st.markdown("Bu simülasyon, **şırınga balast sisteminin** su alıp vermesiyle aracın **yüzerliliğini (buoyancy)** değiştirerek nasıl hareket ettiğini gösterir.")

# --- KENAR ÇUBUĞU (KONTROLLER) ---
st.sidebar.header("🎛️ Kontrol Paneli")

# 1. Hedef Ayarı
target_depth = st.sidebar.slider("🎯 Hedef Derinlik (metre)", 0.0, 5.0, 2.5, step=0.1)

# 2. PID Ayarları
st.sidebar.subheader("PID Katsayıları")
kp = st.sidebar.number_input("Kp (Oransal)", value=50.0, step=1.0)
ki = st.sidebar.number_input("Ki (İntegral)", value=2.0, step=0.1)
kd = st.sidebar.number_input("Kd (Türevsel)", value=40.0, step=1.0)

# 3. Simülasyon Kontrolü
if 'running' not in st.session_state:
    st.session_state.running = False

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("▶️ Başlat"):
    st.session_state.running = True
if col_btn2.button("⏹️ Durdur"):
    st.session_state.running = False
    
if st.sidebar.button("🔄 Sıfırla"):
    st.session_state.running = False
    st.session_state.current_depth = 0.0
    st.session_state.velocity = 0.0
    st.session_state.piston_pos = 30.0 # %50 (Nötr)
    st.session_state.integral_error = 0.0
    st.session_state.last_error = 0.0
    st.session_state.history = pd.DataFrame(columns=['Zaman', 'Mevcut', 'Hedef', 'Piston'])
    st.session_state.start_time = time.time()

# --- STATE BAŞLATMA ---
if 'current_depth' not in st.session_state:
    st.session_state.current_depth = 0.0 # Başlangıç derinliği
    st.session_state.velocity = 0.0
    st.session_state.piston_pos = 30.0 # ml (0-60 arası, 30 nötr)
    st.session_state.integral_error = 0.0
    st.session_state.last_error = 0.0
    st.session_state.history = pd.DataFrame(columns=['Zaman', 'Mevcut', 'Hedef', 'Piston'])
    st.session_state.start_time = time.time()

# --- FONKSİYON: SVG ANİMASYONU ---
def render_animation(depth, piston_ml):
    """
    Derinlik ve piston durumuna göre SVG üretir.
    depth: 0-5 metre arası
    piston_ml: 0-60 ml arası
    """
    # Ölçeklendirme
    max_depth_pixel = 400 # Havuz yüksekliği (px)
    pixel_y = (depth / 5.0) * (max_depth_pixel - 60) # Aracı konumlandır
    pixel_y = max(0, min(pixel_y, max_depth_pixel - 60)) # Sınırlar
    
    # Şırınga Görseli
    piston_fill_pct = (piston_ml / 60.0) * 100
    piston_height = (piston_ml / 60.0) * 40 # Şırınga içindeki su yüksekliği
    
    svg_code = f"""
    <svg width="100%" height="450" style="border: 2px solid #004488; background: linear-gradient(to bottom, #87CEEB, #001f3f); border-radius: 10px;">
        <line x1="0" y1="50" x2="100%" y2="50" stroke="white" stroke-opacity="0.2" />
        <line x1="0" y1="150" x2="100%" y2="150" stroke="white" stroke-opacity="0.2" />
        <line x1="0" y1="250" x2="100%" y2="250" stroke="white" stroke-opacity="0.2" />
        <line x1="0" y1="350" x2="100%" y2="350" stroke="white" stroke-opacity="0.2" />
        
        <text x="10" y="20" fill="white" font-family="monospace">0m (Yüzey)</text>
        <text x="10" y="440" fill="white" font-family="monospace">5m (Dip)</text>
        
        <g transform="translate(150, {pixel_y})">
            <rect x="0" y="0" width="120" height="50" rx="15" ry="15" fill="#f1c40f" stroke="#333" stroke-width="2"/>
            <rect x="-10" y="15" width="10" height="20" fill="#333" />
            <path d="M 120 10 Q 135 25 120 40" stroke="#333" fill="#f1c40f" stroke-width="2"/>
            
            <rect x="30" y="15" width="60" height="20" fill="white" stroke="black" stroke-width="1"/>
            <rect x="30" y="15" width="{piston_fill_pct * 0.6}" height="20" fill="#3498db" />
            <line x1="{30 + (piston_fill_pct * 0.6)}" y1="25" x2="100" y2="25" stroke="#555" stroke-width="3" />
            
            <text x="35" y="45" font-size="8" fill="black">Şırınga: {int(piston_ml)}ml</text>
        </g>
        
        <line x1="210" y1="{pixel_y + 25}" x2="280" y2="{pixel_y + 25}" stroke="white" stroke-dasharray="4" />
        <text x="290" y="{pixel_y + 30}" fill="white" font-weight="bold">{depth:.2f} m</text>
    </svg>
    """
    return svg_code

# --- ANA DÜZEN ---
col_anim, col_data = st.columns([1, 2])

# Yer tutucular (Animasyon ve Veriler için)
with col_anim:
    st.subheader("🚢 Canlı Animasyon")
    anim_placeholder = st.empty()

with col_data:
    st.subheader("📊 PID Analiz Grafiği")
    chart_placeholder = st.empty()
    st.subheader("🧮 Anlık PID Değerleri")
    table_placeholder = st.empty()

# --- SİMÜLASYON DÖNGÜSÜ ---
if st.session_state.running:
    # Simülasyon parametreleri
    dt = 0.1 # Zaman adımı (sn)
    mass_base = 2.4 # kg (Araç kütlesi)
    
    # Döngü
    while st.session_state.running:
        # 1. PID HESAPLAMA
        error = target_depth - st.session_state.current_depth
        st.session_state.integral_error += error * dt
        derivative = (error - st.session_state.last_error) / dt
        
        # PID Çıkışı -> İstenen Şırınga Hareketi
        pid_output = (kp * error) + (ki * st.session_state.integral_error) + (kd * derivative)
        
        # Çıkışı Fiziksel Şırınga Sınırlarına Ölçekle (ml/sn değişim hızı)
        piston_change_rate = np.clip(pid_output, -10, 10) # Motor hızı sınırı
        st.session_state.piston_pos += piston_change_rate * dt
        
        # Şırınga Fiziksel Sınırları (0ml - 60ml)
        st.session_state.piston_pos = np.clip(st.session_state.piston_pos, 0, 60)
        
        # 2. FİZİK MOTORU (Arşimet)
        # Nötr Yüzerlilik: 30ml (Varsayım: 30ml su aldığında araç suyla aynı yoğunlukta)
        # 30ml'den fazla su -> Ağırlaşır (Batar)
        # 30ml'den az su -> Hafifler (Çıkar)
        
        buoyancy_factor = (st.session_state.piston_pos - 30.0) * 0.05 # Kuvvet katsayısı
        
        # F = m*a -> a = F/m (Basit model)
        # Sürtünme (Drag) ekleyelim: Hızın tersine kuvvet
        drag = -0.8 * st.session_state.velocity
        acceleration = buoyancy_factor + drag
        
        # Kinematik
        st.session_state.velocity += acceleration * dt
        st.session_state.current_depth += st.session_state.velocity * dt
        
        # Sınır Kontrolü (Yüzey ve Dip)
        if st.session_state.current_depth < 0:
            st.session_state.current_depth = 0
            st.session_state.velocity = 0
        elif st.session_state.current_depth > 5.0:
            st.session_state.current_depth = 5.0
            st.session_state.velocity = 0
            
        st.session_state.last_error = error
        
        # 3. VERİ GÜNCELLEME
        current_time = time.time() - st.session_state.start_time
        new_row = pd.DataFrame({
            'Zaman': [current_time],
            'Mevcut': [st.session_state.current_depth],
            'Hedef': [target_depth],
            'Piston': [st.session_state.piston_pos]
        })
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
        # Grafikte son 100 veriyi tut (Performans için)
        if len(st.session_state.history) > 100:
            chart_data = st.session_state.history.iloc[-100:]
        else:
            chart_data = st.session_state.history

        # 4. GÖRSELLEŞTİRME (RENDER)
        
        # A) SVG Animasyonu
        anim_placeholder.markdown(
            render_animation(st.session_state.current_depth, st.session_state.piston_pos), 
            unsafe_allow_html=True
        )
        
        # B) Grafik
        with chart_placeholder.container():
            st.line_chart(
                chart_data.set_index('Zaman')[['Mevcut', 'Hedef']],
                color=["#FF0000", "#0000FF"], # Mavi Hedef, Kırmızı Mevcut
                height=250
            )
            
        # C) Canlı PID Tablosu
        # Pandas DataFrame ile şık bir tablo oluşturalım
        pid_data = {
            "Parametre": ["Hata (e)", "P-Etkisi (Kp*e)", "I-Etkisi (Ki*∫)", "D-Etkisi (Kd*d)", "Şırınga Suyu (ml)", "Araç Hızı (m/s)"],
            "Değer": [
                f"{error:.3f} m",
                f"{kp * error:.2f}",
                f"{ki * st.session_state.integral_error:.2f}",
                f"{kd * derivative:.2f}",
                f"{st.session_state.piston_pos:.1f} ml",
                f"{st.session_state.velocity:.3f}"
            ],
            "Açıklama": [
                "Hedef ile anlık fark",
                "Mevcut hataya anlık tepki",
                "Geçmiş hataların toplamı",
                "Hatanın değişim hızına tepki",
                "Aracın ağırlığını belirler",
                "Pozitif: Batıyor, Negatif: Çıkıyor"
            ]
        }
        table_placeholder.table(pd.DataFrame(pid_data))
        
        # Gecikme (Animasyon hızı)
        time.sleep(0.05)
else:
    # Durmuş haldeyken son durumu göster
    anim_placeholder.markdown(
        render_animation(st.session_state.current_depth, st.session_state.piston_pos), 
        unsafe_allow_html=True
    )
    if not st.session_state.history.empty:
        chart_placeholder.line_chart(st.session_state.history.set_index('Zaman')[['Mevcut', 'Hedef']])
    else:
        chart_placeholder.info("Simülasyonu başlatmak için 'Başlat' butonuna basın.")
