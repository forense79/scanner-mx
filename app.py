import streamlit as st
import requests
import base64
from urllib.parse import quote_plus
from PIL import Image
import io
import time
import re

st.set_page_config(page_title="Scanner Total MX", page_icon="🔍")
st.title("🔍 Scanner Total MX")
st.caption("Arm & Hammer -> Ahora sí jala")

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

def limpiar_busqueda(texto):
    # Quita & y caracteres raros para ML
    texto = texto.replace("&", " ")
    texto = re.sub(r'[^a-zA-Z0-9 ]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

if imagen_file:
    img = Image.open(imagen_file).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🚀 IDENTIFICAR Y ANALIZAR", type="primary", use_container_width=True):
        with st.status("Identificando...", expanded=True) as status:
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode()

            modelos = ["models/gemini-3.8-flash","models/gemini-2.5-flash","models/gemini-2.0-flash","models/gemini-flash-latest"]
            producto = None
            for modelo in modelos:
                try:
                    st.write(f"Probando {modelo}...")
                    url = f"https://generativelanguage.googleapis.com/v1/{modelo}:generateContent?key={gemini_key}"
                    payload = {"contents": [{"parts": [
                        {"text": "Identifica producto. SOLO MARCA + PRODUCTO + TAMAÑO. Ej: Ariel 5kg. Max 5 palabras."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]}]}
                    r = requests.post(url, json=payload, timeout=30)
                    data = r.json()
                    if 'candidates' in data:
                        producto = data['candidates'][0]['content']['parts'][0]['text'].strip()
                        break
                    time.sleep(0.5)
                except: continue
            
            if not producto:
                st.error("Intenta de nuevo, Google saturado")
                st.stop()
            
            st.success(f"Producto: **{producto}**")
            status.update(label=f"✅ {producto}", state="complete")

        # LIMPIEZA PARA BUSQUEDA
        q_limpio = limpiar_busqueda(producto)
        q = quote_plus(q_limpio)
        q_simple = quote_plus(" ".join(q_limpio.split()[:2])) # Ej: Arm Hammer

        st.divider()
        st.subheader(f"Mercado Libre: {producto}")
        
        # Intento 1 con nombre completo limpio
        ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=5", timeout=15).json()
        results = ml.get('results', [])
        
        # Si 0, intento 2 con nombre simple
        if len(results) == 0 and q_simple != q:
            st.caption(f"No hubo con '{q_limpio}', buscando '{q_simple}'...")
            ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q_simple}&limit=5", timeout=15).json()
            results = ml.get('results', [])

        st.metric("Vendedores", len(results))
        
        if len(results) > 0:
            for item in results[:3]:
                with st.container(border=True):
                    st.write(f"**{item['title'][:100]}**")
                    c1,c2 = st.columns(2)
                    c1.metric("Precio", f"${item['price']}")
                    c2.metric("Vendidos", item.get('sold_quantity',0))
                    if costo_mxn>0:
                        gan = item['price']*0.84 - costo_mxn
                        st.metric("Tu ganancia", f"${gan:.0f}", delta="BUENA" if gan>0 else "MALA")
                    st.link_button("Ver en ML", item['permalink'], use_container_width=True)
        else:
            st.warning("0 en ML. Puede ser muy nicho. Revisa Amazon/Walmart abajo.")

        st.divider()
        st.subheader("Amazon y Walmart")
        st.link_button(f"🔍 Amazon: {producto}", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
        st.link_button(f"🔍 Walmart: {producto}", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)

        st.divider()
        st.subheader("📊 RESUMEN FINAL")
        with st.container(border=True):
            st.write(f"**Producto:** {producto}")
            st.write(f"**Búsqueda:** {q_limpio}")
            st.write(f"**Tu costo:** ${costo_mxn:.0f} MXN")
            if len(results)>0:
                precio_prom = sum([r['price'] for r in results[:3]])/min(3,len(results))
                st.write(f"**Precio promedio ML:** ${precio_prom:.0f}")
                if costo_mxn>0:
                    st.success(f"Ganancia estimada: ${precio_prom*0.84 - costo_mxn:.0f} por pieza")
            else:
                st.info("No hay competencia en ML = Buena oportunidad si hay en Amazon/Walmart")
