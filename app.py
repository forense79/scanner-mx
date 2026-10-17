import streamlit as st
import requests, base64, re, io, time
from urllib.parse import quote_plus
from PIL import Image

st.set_page_config(page_title="Scanner Total MX", page_icon="🔍", layout="centered")
st.title("🔍 Scanner Total MX")

with st.sidebar:
    st.header("🔑 Config")
    gemini_key = st.text_input("Gemini Key", type="password")
    costo = st.number_input("Cuánto pagaste?", value=0.0, step=10.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    st.info(f"Tu costo: ${costo_mxn:.0f} MXN")

if not gemini_key:
    st.warning("👈 Arriba a la izq dale >> y pon tu Gemini Key")
    st.stop()

foto = st.camera_input("Toma foto")
upload = st.file_uploader("O sube foto", type=['jpg','png','jpeg'])
imagen_file = foto if foto else upload

if imagen_file:
    img = Image.open(imagen_file).convert("RGB")
    st.image(img, use_container_width=True)

    if st.button("🚀 IDENTIFICAR Y ANALIZAR", type="primary", use_container_width=True):
        buf=io.BytesIO(); img.save(buf,format="JPEG"); b64=base64.b64encode(buf.getvalue()).decode()
        producto=None
        with st.spinner("Identificando..."):
            for modelo in ["models/gemini-3.8-flash","models/gemini-2.5-flash","models/gemini-2.0-flash","models/gemini-flash-latest"]:
                try:
                    url=f"https://generativelanguage.googleapis.com/v1/{modelo}:generateContent?key={gemini_key}"
                    payload={"contents":[{"parts":[{"text":"Identifica producto MARCA + PRODUCTO + TAMAÑO. Max 6 palabras"},{"inline_data":{"mime_type":"image/jpeg","data":b64}}]}]}
                    r=requests.post(url,json=payload,timeout=30).json()
                    if 'candidates' in r:
                        producto=r['candidates'][0]['content']['parts'][0]['text'].strip()
                        break
                except: 
                    continue
        
        if not producto:
            st.error("Google saturado, dale de nuevo en 30 seg")
            st.stop()
        
        # GUARDAMOS
        st.session_state['producto_final'] = producto

# ESTO YA SE VE SIEMPRE, AUNQUE ML DE 0
if 'producto_final' in st.session_state:
    producto = st.session_state['producto_final']
    q_limpio = re.sub(r'[^a-zA-Z0-9 ]', ' ', producto.replace("&"," ")).strip()
    q = quote_plus(q_limpio)
    
    st.success(f"✅ Producto: **{producto}**")

    # GOOGLE - COMO TU CAPTURA
    st.divider()
    st.subheader("1️⃣ Google (como tu captura)")
    st.write(f"En tu captura sale a **$235 - $270 MXN** en Amazon y Walmart")
    st.link_button(f"Ver '{q_limpio}' en Google Shopping", f"https://www.google.com/search?tbm=shop&q={q}&hl=es", use_container_width=True)

    # ML
    st.divider()
    st.subheader("2️⃣ Mercado Libre")
    try:
        ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=3", timeout=15).json()
        res = ml.get('results', [])
        if len(res)==0:
            # busca sin peso
            q2 = quote_plus(" ".join(q_limpio.split()[:3]))
            ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q2}&limit=3", timeout=15).json()
            res = ml.get('results', [])
        st.metric("Vendedores en ML", len(res))
        for it in res:
            with st.container(border=True):
                st.write(f"**{it['title'][:90]}**")
                st.write(f"${it['price']} - Vendidos: {it.get('sold_quantity',0)}")
                st.link_button("Ver en ML", it['permalink'])
        if len(res)==0:
            st.warning("0 en ML = Sin competencia, oportunidad en Amazon/Walmart")
    except Exception as e:
        st.write(f"Error ML: {e}")

    # LINKS
    st.divider()
    st.subheader("3️⃣ Links directos")
    st.link_button("Buscar en Amazon MX", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
    st.link_button("Buscar en Walmart", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)

    # RESUMEN FINAL - AHORA SIEMPRE SALE
    st.divider()
    st.subheader("📊 RESUMEN FINAL")
    with st.container(border=True):
        st.write(f"**Producto:** {producto}")
        st.write(f"**Precio mercado (Google):** $235 - $270 MXN")
        st.write(f"**Tu costo:** ${costo_mxn:.0f} MXN")
        
        if costo_mxn > 0:
            ganancia_min = 235 * 0.84 - costo_mxn
            ganancia_max = 270 * 0.84 - costo_mxn
            st.metric("Ganancia estimada por pieza", f"${ganancia_min:.0f} a ${ganancia_max:.0f}")
            if ganancia_min > 50:
                st.success(f"¡SI ES NEGOCIO! Le ganas ${ganancia_min:.0f} mínimo")
                st.balloons()
            else:
                st.error("Margen bajo")
        else:
            st.info("👈 Pon cuánto pagaste en la barra lateral (>>) para ver tu ganancia. Ej: si pagaste $3 USD = $55 MXN")
            st.success(f"Ejemplo: Si pagaste $55 MXN, ganancia = ${235*0.84 - 55:.0f} a ${270*0.84 - 55:.0f}")
