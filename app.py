import streamlit as st
import requests
import base64
from urllib.parse import quote_plus
from PIL import Image
import io

st.set_page_config(page_title="Scanner Total MX", page_icon="🔍")
st.title("🔍 Scanner Total MX")

with st.sidebar:
    st.header("🔑 Keys")
    gemini_key = st.text_input("Gemini API Key", type="password")
    costo = st.number_input("Cuánto pagaste?", value=0.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo

if not gemini_key:
    st.warning("Pon tu Gemini Key. Arriba a la izq dale >>")
    st.stop()

foto = st.camera_input("1️⃣ Toma foto")
upload = st.file_uploader("O sube foto", type=['jpg','png','jpeg'])
imagen_file = foto if foto else upload

if imagen_file:
    img = Image.open(imagen_file).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🚀 IDENTIFICAR Y ANALIZAR", type="primary", use_container_width=True):
        with st.spinner("Identificando..."):
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Modelo que no expira
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [
                    {"text": "Identifica producto. SOLO MARCA + PRODUCTO + TAMAÑO. Ej: Ariel 5kg. Max 5 palabras."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                ]}]
            }
            r = requests.post(url, json=payload, timeout=25)
            data = r.json()
            
            if 'candidates' not in data:
                # Si falla el alias, prueba con 1.5
                url2 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                r = requests.post(url2, json=payload, timeout=25)
                data = r.json()
            
            if 'candidates' not in data:
                st.error("Error Google")
                st.json(data)
                st.stop()
                
            producto = data['candidates'][0]['content']['parts'][0]['text'].strip()
            st.success(f"Producto: **{producto}**")

        q = quote_plus(producto)
        st.divider()
        st.subheader(f"Mercado Libre: {producto}")
        ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=5", timeout=15).json()
        for item in ml.get('results', [])[:3]:
            with st.container(border=True):
                st.write(f"**{item['title'][:90]}**")
                c1,c2,c3 = st.columns(3)
                c1.metric("Precio", f"${item['price']}")
                c2.metric("Vendidos", item.get('sold_quantity',0))
                if costo_mxn>0:
                    c3.metric("Ganancia", f"${item['price']*0.84 - costo_mxn:.0f}")
                st.link_button("Ver", item['permalink'])

        st.divider()
        st.link_button(f"Amazon: {producto}", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
        st.link_button(f"Walmart: {producto}", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)
        
        st.divider()
        st.success(f"Resumen: {producto} | Tu costo ${costo_mxn:.0f}")
