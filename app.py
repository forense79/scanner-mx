import streamlit as st
import requests
from urllib.parse import quote_plus
from PIL import Image
import easyocr
import re

st.set_page_config(page_title="Scanner MX Auto", page_icon="📦", layout="wide")
st.title("📦 Scanner MX - Auto Detect")
st.caption("Solo toma foto, no escribas nada")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['es','en'], gpu=False)

reader = load_ocr()

with st.sidebar:
    st.header("Tu compra")
    costo = st.number_input("¿Cuánto pagaste?", value=0.0, step=10.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_envio = st.number_input("Envío ML", value=80.0)
    comision = st.slider("Comisión ML %", 12, 20, 16)
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    if costo>0:
        st.metric("Costo MXN", f"${costo_mxn:.0f}")

# --- AUTO DETECT ---
foto = st.camera_input("📸 Toma foto del producto - frente donde se vea la marca")
uploaded = st.file_uploader("O sube foto de galería", type=["jpg","png","jpeg"])

imagen = None
if foto:
    imagen = Image.open(foto)
elif uploaded:
    imagen = Image.open(uploaded)

query_auto = ""
if imagen:
    st.image(imagen, width=300)
    with st.spinner("Leyendo etiqueta..."):
        # OCR
        try:
            result = reader.readtext(
                image = imagen,
                detail = 0,
                paragraph = True
            )
            texto_detectado = " ".join(result)
            st.write(f"Texto detectado: {texto_detectado}")

            # Limpia y saca palabras clave
            # Busca marcas comunes
            texto = texto_detectado.upper()
            # Quita basura
            texto = re.sub(r'[^A-Z0-9 ]', ' ', texto)
            palabras = texto.split()
            # Toma las 4 palabras más largas que parezcan marca/producto
            palabras_filtradas = [p for p in palabras if len(p) > 2][:6]
            query_auto = " ".join(palabras_filtradas)
            
            if len(query_auto) < 3:
                query_auto = texto_detectado[:40]
                
            st.success(f"Producto identificado: **{query_auto}**")
        except Exception as e:
            st.error(f"No pude leer: {e}")
            query_auto = ""

# Si no detectó, permite escribir manual como respaldo
query_manual = st.text_input("Si no lo detectó bien, corrígelo aquí", value=query_auto, placeholder="Ej: Ariel 5kg")

query_final = query_manual if query_manual else query_auto

if st.button("🔍 BUSCAR GANANCIA", type="primary", use_container_width=True):
    if not query_final:
        st.warning("Toma una foto primero")
    else:
        st.divider()
        st.subheader(f"Resultados para: {query_final}")
        
        try:
            url = f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(query_final)}&limit=6"
            r = requests.get(url, timeout=12).json()
            for item in r.get('results', []):
                precio = item['price']
                vendidos = item.get('sold_quantity',0)
                ganancia = precio*(1-comision/100) - costo_envio - costo_mxn if costo_mxn>0 else 0
                with st.container(border=True):
                    st.write(f"**{item['title']}**")
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Precio ML", f"${precio}")
                    c2.metric("Vendidos", vendidos)
                    if costo_mxn>0:
                        c3.metric("Ganancia", f"${ganancia:.0f}", delta="SI" if ganancia>0 else "NO")
                    st.link_button("Ver", item['permalink'], use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
        
        st.divider()
        c1,c2 = st.columns(2)
        c1.link_button(f"Amazon: {query_final}", f"https://www.amazon.com.mx/s?k={quote_plus(query_final)}", use_container_width=True)
        c2.link_button(f"Walmart: {query_final}", f"https://www.walmart.com.mx/search?q={quote_plus(query_final)}", use_container_width=True)
