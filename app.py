import streamlit as st
import pandas as pd
import time
import numpy as np

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="AUV PID Simülasyonu", layout="wide")

# --- BAŞLIK ---
st.title("🌊 Otonom Sualtı Aracı: PID Kontrol")
st.markdown("Bu simülasyon, **şırınga balast sisteminin** su alıp vermesiyle aracın **yüzerliliğini (buoyancy)** değiştirerek nasıl hareket ettiğini gösterir.")

# --- KENAR ÇUBUĞU (KONTROLLER) ---
st.sidebar.header("🎛️ Kontrol Paneli")

# 1. Hedef Ayarı
target_depth = st.sidebar.slider("🎯 Hedef Derinlik (metre)", 0.0, 5.0, 2.5, step=0.1)

# 2. PID Ayarları (Tooltips Eklendi)
st.sidebar.subheader("PID Katsayıları")

kp = st.sidebar.number_input(
    "Kp (Oransal)", 
    value=20.0, 
    step=1.0,
    help="Hata büyüklüğüne anlık tepki verir. Değer arttıkça araç hedefe daha agresif hareket eder."
)

ki = st.sidebar.number_input(
    "Ki (İntegral)", 
    value=0.5, 
    step=0.1, 
    help="Derinlik direncini yenmek ve kalıcı hatayı (steady-state error) sıfırlamak için kullanılır."
)

kd = st.sidebar.number_input(
    "Kd (Türevsel)", 
    value=35.0, 
    step=1.0,
    help="Ani hareketleri frenler, salınımı (overshoot) engeller ve sistemi kararlı (stabil) kılar."
)

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
    st.session_state.current_depth = 0.0 
    st.session_state.velocity = 0.0
    st.session_state.piston_pos = 30.0 
    st.session_state.integral_error = 0.0
    st.session_state.last_error = 0.0
    st.session_state.history = pd.DataFrame(columns=['Zaman', 'Mevcut', 'Hedef', 'Piston'])
    st.session_state.start_time = time.time()

# --- FONKSİYON: SVG ANİMASYONU ---
def render_animation(depth, piston_ml):
    # Ölçeklendirme
    max_depth_pixel = 400 
    pixel_y = (depth / 5.0) * (max_depth_pixel - 60) 
    pixel_y = max(0, min(pixel_y, max_depth_pixel - 60)) 
    
    piston_fill_pct = (piston_ml / 60.0) * 100
    
    # SVG KODU (ViewBox eklendi ve koordinatlar ortalandı)
    # viewBox="0 0 600 450" -> 600 birim genişlik tanımlar.
    # Aracın merkezi x=300 noktasına taşındı.
    svg_code = f"""
<svg viewBox="0 0 600 450" preserveAspectRatio="xMidYMid meet" style="width: 100%; height: 450px; background: linear-gradient(to bottom, #4facfe, #00f2fe); border-radius: 10px; border: 2px solid #333;">
<defs>
<linearGradient id="oceanGradient" x1="0%" y1="0%" x2="0%" y2="100%">
<stop offset="0%" style="stop-color:#4facfe;stop-opacity:1" />
<stop offset="100%" style="stop-color:#00f2fe;stop-opacity:1" />
</linearGradient>
</defs>

<line x1="0" y1="50" x2="600" y2="50" stroke="white" stroke-opacity="0.5" stroke-dasharray="5,5"/>
<line x1="0" y1="150" x2="600" y2="150" stroke="white" stroke-opacity="0.5" stroke-dasharray="5,5"/>
<line x1="0" y1="250" x2="600" y2="250" stroke="white" stroke-opacity="0.5" stroke-dasharray="5,5"/>
<line x1="0" y1="350" x2="600" y2="350" stroke="white" stroke-opacity="0.5" stroke-dasharray="5,5"/>

<text x="10" y="20" fill="white" font-weight="bold" font-family="sans-serif" style="text-shadow: 1px 1px 2px black;">0m (Yüzey)</text>
<text x="10" y="440" fill="white" font-weight="bold" font-family="sans-serif" style="text-shadow: 1px 1px 2px black;">5m (Dip)</text>

<g transform="translate(230, {pixel_y})">
    <rect x="-15" y="15" width="15" height="20" fill="#333">
    <animateTransform attributeName="transform" type="rotate" from="0 -7.5 25" to="360 -7.5 25" dur="0.2s" repeatCount="indefinite" />
    </rect>
    
    <rect x="0" y="0" width="140" height="50" rx="20" ry="20" fill="#FFD700" stroke="#333" stroke-width="2"/>
    <path d="M 140 10 Q 155 25 140 40" stroke="#333" fill="#87CEFA" stroke-width="2" fill-opacity="0.8"/>
    
    <rect x="35" y="15" width="70" height="20" fill="white" stroke="black" stroke-width="1"/>
    <rect x="35" y="15" width="{piston_fill_pct * 0.7}" height="20" fill="#0000FF" fill-opacity="0.6" />
    <line x1="{35 + (piston_fill_pct * 0.7)}" y1="25" x2="115" y2="25" stroke="#333" stroke-width="3" />
    
    <text x="40" y="45" font-size="10" fill="black" font-weight="bold">{int(piston_ml)}ml</text>
</g>

<line x1="300" y1="{pixel_y + 25}" x2="400" y2="{pixel_y + 25}" stroke="white" stroke-width="2" />
<circle cx="300" cy="{pixel_y + 25}" r="3" fill="white" />
<text x="410" y="{pixel_y + 30}" fill="white" font-size="18" font-weight="bold" style="text-shadow: 1px 1px 2px black;">{depth:.2f} m</text>
</svg>
"""
    return svg_code

# --- ANA DÜZEN ---
col_anim, col_data = st.columns([1, 2])

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
    dt = 0.1 
    
    while st.session_state.running:
        # 1. PID HESAPLAMA
        error = target_depth - st.session_state.current_depth
        st.session_state.integral_error += error * dt
        derivative = (error - st.session_state.last_error) / dt
        
        pid_output = (kp * error) + (ki * st.session_state.integral_error) + (kd * derivative)
        
        piston_change_rate = np.clip(pid_output, -5, 5) 
        st.session_state.piston_pos += piston_change_rate * dt
        st.session_state.piston_pos = np.clip(st.session_state.piston_pos, 0, 60)
        
        # 2. FİZİK MOTORU (Derinlik Direnci Dahil)
        dynamic_neutral_point = 30.0 + (st.session_state.current_depth * 3.0)
        
        buoyancy_factor = (st.session_state.piston_pos - dynamic_neutral_point) * 0.05 
        
        drag = -2.0 * st.session_state.velocity 
        acceleration = buoyancy_factor + drag
        
        st.session_state.velocity += acceleration * dt
        st.session_state.current_depth += st.session_state.velocity * dt
        
        # Sınır Kontrolü
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
            'Hedef': [target_depth]
        })
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
        
        if len(st.session_state.history) > 100:
            chart_data = st.session_state.history.iloc[-100:]
        else:
            chart_data = st.session_state.history

        # GÖRSELLEŞTİRME
        anim_placeholder.markdown(
            render_animation(st.session_state.current_depth, st.session_state.piston_pos), 
            unsafe_allow_html=True
        )
        
        with chart_placeholder.container():
            st.line_chart(
                chart_data.set_index('Zaman')[['Mevcut', 'Hedef']],
                color=["#FF4B4B", "#1C83E1"], 
                height=250
            )
            
        pid_data = {
            "Parametre": ["Hata (e)", "P-Etkisi", "I-Etkisi", "D-Etkisi", "Şırınga (ml)"],
            "Değer": [
                f"{error:.3f} m",
                f"{kp * error:.2f}",
                f"{ki * st.session_state.integral_error:.2f}",
                f"{kd * derivative:.2f}",
                f"{st.session_state.piston_pos:.1f} ml"
            ]
        }
        table_placeholder.table(pd.DataFrame(pid_data))
        
        time.sleep(0.05)
else:
    # Durmuş Halde Gösterim
    anim_placeholder.markdown(
        render_animation(st.session_state.current_depth, st.session_state.piston_pos), 
        unsafe_allow_html=True
    )
    if not st.session_state.history.empty:
        chart_placeholder.line_chart(st.session_state.history.set_index('Zaman')[['Mevcut', 'Hedef']])
    else:
        st.info("Simülasyonu başlatmak için sol menüdeki 'Başlat' butonuna basın.")
