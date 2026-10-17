import streamlit as st
import requests
import base64
from urllib.parse import quote_plus
from PIL import Image
import io

st.set_page_config(page_title="Scanner Total MX", page_icon="🔍")
st.title("🔍 Scanner Total MX")
st.caption("Foto -> Identifica -> ML + Amazon + Walmart")

with st.sidebar:
    st.header("🔑 Keys")
    gemini_key = st.text_input("Gemini API Key (gratis)", type="password", help="aistudio.google.com/app/apikey")
    serp_key = st.text_input("SerpApi Key (opcional)", type="password")
    st.divider()
    costo = st.number_input("Cuánto pagaste?", value=0.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo

if not gemini_key:
    st.warning("👈 Pon tu Gemini Key en la barra lateral. Es gratis en aistudio.google.com/app/apikey")
    st.info("Arriba a la izquierda dale a >> para abrir el menú")
    st.stop()

# 1. FOTO
foto = st.camera_input("1️⃣ Toma foto del producto")
upload = st.file_uploader("O sube foto", type=['jpg','png','jpeg'])
imagen_file = foto if foto else upload

if imagen_file:
    img = Image.open(imagen_file)
    st.image(img, use_container_width=True)
    
    if st.button("🚀 IDENTIFICAR Y ANALIZAR", type="primary", use_container_width=True):
        # 2. IDENTIFICAR CON GEMINI 2.0
        with st.spinner("2️⃣ Identificando con Google AI 2.0..."):
            try:
                buffered = io.BytesIO()
                img = img.convert("RGB")
                img.save(buffered, format="JPEG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode()
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Identifica este producto. Responde SOLO con MARCA + PRODUCTO + TAMAÑO. Ej: Ariel 5kg o Clorox 1L. Max 5 palabras, sin comillas."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                        ]
                    }]
                }
                r = requests.post(url, json=payload, timeout=25)
                data = r.json()
                
                if 'candidates' not in data:
                    st.error("Error de Google")
                    st.json(data)
                    st.stop()
                    
                producto = data['candidates'][0]['content']['parts'][0]['text'].strip()
                st.success(f"Producto identificado: **{producto}**")
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        q = quote_plus(producto)
        
        # 3. MERCADO LIBRE
        st.divider()
        st.subheader(f"3️⃣ Mercado Libre: {producto}")
        try:
            ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=6", timeout=15).json()
            results = ml.get('results', [])
            st.metric("Vendedores encontrados", len(results))
            for item in results[:3]:
                with st.container(border=True):
                    st.write(f"**{item['title'][:95]}**")
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Precio", f"${item['price']}")
                    c2.metric("Vendidos", item.get('sold_quantity',0))
                    if costo_mxn>0:
                        gan = item['price']*0.84 - costo_mxn
                        c3.metric("Tu Ganancia", f"${gan:.0f}", delta="SI" if gan>0 else "NO")
                    st.link_button("Ver en ML", item['permalink'], use_container_width=True)
        except Exception as e:
            st.error(f"Error ML: {e}")

        # 4. AMAZON
        st.divider()
        st.subheader(f"4️⃣ Amazon.com.mx: {producto}")
        st.link_button(f"Buscar '{producto}' en Amazon", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
        
        # 5. WALMART
        st.divider()
        st.subheader(f"5️⃣ Walmart.com.mx: {producto}")
        st.link_button(f"Buscar '{producto}' en Walmart", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)

        # 6. RESUMEN
        st.divider()
        st.subheader("6️⃣ RESUMEN FINAL")
        st.write(f"**Producto:** {producto}")
        st.write(f"**Tu costo:** ${costo_mxn:.0f} MXN")
        st.success("Análisis listo ✅")
