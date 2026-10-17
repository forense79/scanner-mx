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
    serp_key = st.text_input("SerpApi Key (gratis)", type="password")
    st.divider()
    costo = st.number_input("Cuánto pagaste?", value=0.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo

if not gemini_key:
    st.warning("👈 Pon tu Gemini Key en la barra lateral para empezar. Es gratis en aistudio.google.com")
    st.stop()

# 1. FOTO
foto = st.camera_input("1️⃣ Toma foto")
upload = st.file_uploader("O sube foto", type=['jpg','png','jpeg'])
imagen_file = foto if foto else upload

if imagen_file:
    img = Image.open(imagen_file)
    st.image(img, use_container_width=True)
    
    if st.button("🚀 IDENTIFICAR", type="primary", use_container_width=True):
        # 2. IDENTIFICAR CON GEMINI VIA API REST (sin libreria)
        with st.spinner("2️⃣ Identificando producto con Google AI..."):
            try:
                # Convertir imagen a base64
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode()
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": "Identifica este producto de tienda. Responde SOLO con MARCA + PRODUCTO + TAMAÑO. Ejemplo: 'Ariel 5kg' o 'Clorox 1L'. Max 5 palabras."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                        ]
                    }]
                }
                r = requests.post(url, json=payload, timeout=20)
                data = r.json()
                producto = data['candidates'][0]['content']['parts'][0]['text'].strip()
                st.success(f"Producto identificado: **{producto}**")
            except Exception as e:
                st.error(f"Error identificando: {e}")
                st.json(r.text if 'r' in locals() else str(e))
                st.stop()

        q = quote_plus(producto)
        
        # 3. MERCADO LIBRE
        st.divider()
        st.subheader(f"3️⃣ Mercado Libre: {producto}")
        try:
            ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=5", timeout=15).json()
            results = ml.get('results', [])
            st.metric("Vendedores", len(results))
            for item in results[:3]:
                with st.container(border=True):
                    st.write(f"**{item['title'][:90]}**")
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Precio", f"${item['price']}")
                    c2.metric("Vendidos", item.get('sold_quantity',0))
                    if costo_mxn>0:
                        gan = item['price']*0.84 - costo_mxn
                        c3.metric("Tu Gan", f"${gan:.0f}")
                    st.link_button("Ver en ML", item['permalink'])
        except Exception as e:
            st.error(f"Error ML: {e}")

        # 4. AMAZON
        st.divider()
        st.subheader("4️⃣ Amazon.com.mx")
        st.link_button(f"Ver '{producto}' en Amazon", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
        if serp_key:
            try:
                params = {"engine":"amazon","k":producto,"amazon_domain":"amazon.com.mx","api_key":serp_key}
                amz = requests.get("https://serpapi.com/search", params=params, timeout=20).json()
                for a in amz.get('organic_results', [])[:2]:
                    with st.container(border=True):
                        st.write(a.get('title',''))
                        st.write(f"Precio: {a.get('price','')}")
            except:
                pass

        # 5. WALMART
        st.divider()
        st.subheader("5️⃣ Walmart.com.mx")
        st.link_button(f"Ver '{producto}' en Walmart", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)

        # 6. RESUMEN
        st.divider()
        st.subheader("6️⃣ Resumen")
        st.write(f"Producto: {producto} | Tu costo: ${costo_mxn:.0f} MXN")
        st.success("Listo. Ya puedes decidir si conviene revender.")
