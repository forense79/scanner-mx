import streamlit as st
import requests
import base64
from urllib.parse import quote_plus
from PIL import Image
import io
import time

st.set_page_config(page_title="Scanner Total MX", page_icon="🔍")
st.title("🔍 Scanner Total MX")

with st.sidebar:
    st.header("🔑 Keys")
    gemini_key = st.text_input("Gemini API Key", type="password")
    costo = st.number_input("Cuánto pagaste?", value=0.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo

if not gemini_key:
    st.warning("Pon tu Gemini Key. >> arriba a la izq")
    st.stop()

foto = st.camera_input("1️⃣ Toma foto")
upload = st.file_uploader("O sube foto", type=['jpg','png','jpeg'])
imagen_file = foto if foto else upload

if imagen_file:
    img = Image.open(imagen_file).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🚀 IDENTIFICAR Y ANALIZAR", type="primary", use_container_width=True):
        with st.status("Identificando...", expanded=True) as status:
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()

            # LISTA DE MODELOS EN ORDEN, PRUEBA UNO TRAS OTRO
            modelos = [
                "models/gemini-3.8-flash",
                "models/gemini-2.5-flash",
                "models/gemini-2.0-flash",
                "models/gemini-flash-latest",
                "models/gemini-1.5-flash-latest"
            ]
            
            producto = None
            for modelo in modelos:
                try:
                    st.write(f"Probando: {modelo}...")
                    url = f"https://generativelanguage.googleapis.com/v1/{modelo}:generateContent?key={gemini_key}"
                    payload = {
                        "contents": [{"parts": [
                            {"text": "Identifica producto. SOLO MARCA + PRODUCTO + TAMAÑO. Ej: Ariel 5kg. Max 5 palabras."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                        ]}]
                    }
                    r = requests.post(url, json=payload, timeout=30)
                    data = r.json()
                    
                    if 'candidates' in data:
                        producto = data['candidates'][0]['content']['parts'][0]['text'].strip()
                        st.success(f"Jaló con {modelo}")
                        break
                    elif data.get('error',{}).get('code') == 503:
                        st.write(f"⏳ {modelo} saturado, probando siguiente...")
                        time.sleep(1)
                        continue
                    else:
                        st.write(f"Error con {modelo}: {data.get('error',{}).get('message','')[:100]}")
                        continue
                except Exception as e:
                    st.write(f"Fallo {modelo}: {e}")
                    continue
            
            if not producto:
                st.error("Todos los modelos saturados. Espera 2 min y dale de nuevo a Identificar. Es normal cuando Google tiene picos.")
                st.stop()
            
            st.success(f"Producto: **{producto}**")
            status.update(label="Producto identificado", state="complete")

        q = quote_plus(producto)
        st.divider()
        st.subheader(f"Mercado Libre: {producto}")
        ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=5", timeout=15).json()
        st.metric("Vendedores", len(ml.get('results',[])))
        for item in ml.get('results', [])[:3]:
            with st.container(border=True):
                st.write(f"**{item['title'][:90]}**")
                c1,c2 = st.columns(2)
                c1.metric("Precio", f"${item['price']}")
                c2.metric("Vendidos", item.get('sold_quantity',0))
                if costo_mxn>0:
                    st.write(f"Tu ganancia: ${item['price']*0.84 - costo_mxn:.0f}")
                st.link_button("Ver en ML", item['permalink'])

        st.divider()
        st.link_button(f"Amazon: {producto}", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
        st.link_button(f"Walmart: {producto}", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)
        st.success(f"Resumen: {producto} | Costo ${costo_mxn:.0f}")
