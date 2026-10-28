import streamlit as st
import requests
from urllib.parse import quote_plus
from PIL import Image
import io
import re

st.set_page_config(page_title="Scanner MX Auto", page_icon="📦", layout="wide")
st.title("📦 Scanner MX - Auto Detect")
st.caption("Solo foto, sin escribir")

def ocr_from_image(pil_image):
    """OCR gratis via OCR.Space - funciona en Streamlit Cloud"""
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format='JPEG')
        buf.seek(0)
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", buf, "image/jpeg")},
            data={"apikey": "helloworld", "language": "spa", "isOverlayRequired": False},
            timeout=20
        )
        j = r.json()
        if j.get("IsErroredOnProcessing") == False:
            text = j["ParsedResults"][0]["ParsedText"]
            return text
        return ""
    except Exception as e:
        return f"Error OCR: {e}"

with st.sidebar:
    st.header("Tu compra")
    costo = st.number_input("¿Cuánto pagaste?", value=0.0, step=10.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_envio = st.number_input("Envío ML", value=80.0)
    comision = st.slider("Comisión ML %", 12, 20, 16)
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    if costo>0:
        st.metric("Costo MXN", f"${costo_mxn:.0f}")

foto = st.camera_input("📸 Toma foto del frente del producto")
uploaded = st.file_uploader("O sube de galería", type=["jpg","png","jpeg"])

imagen = None
if foto:
    imagen = Image.open(foto)
elif uploaded:
    imagen = Image.open(uploaded)

query_auto = ""
if imagen:
    st.image(imagen, width=350)
    with st.spinner("Identificando producto por foto..."):
        texto = ocr_from_image(imagen)
        st.write(f"Texto leído: {texto[:200]}")
        if texto:
            # Limpia y saca marca
            texto_upper = re.sub(r'[^A-Z0-9ÁÉÍÓÚÑ ]', ' ', texto.upper())
            palabras = [p for p in texto_upper.split() if len(p) > 2]
            # Quita palabras comunes que no sirven
            basura = {"CONT","NET","PESO","LITROS","ML","KG","GR","HECHO","MEXICO","ENVASE"}
            palabras = [p for p in palabras if p not in basura]
            query_auto = " ".join(palabras[:5])
            if query_auto:
                st.success(f"Detectado: **{query_auto}**")
        else:
            st.warning("No leí texto, intenta más cerca y con luz")

query_final = st.text_input("Corrige si hace falta", value=query_auto, placeholder="Ej: Ariel 5kg")

if st.button("🔍 BUSCAR GANANCIA", type="primary", use_container_width=True):
    if not query_final:
        st.warning("Toma foto primero")
    else:
        st.divider()
        st.subheader(f"Resultados para: {query_final}")
        try:
            url = f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(query_final)}&limit=6"
            r = requests.get(url, timeout=12).json()
            for item in r.get('results', []):
                precio = item['price']
                vendidos = item.get('sold_quantity',0)
                gan = precio*(1-comision/100) - costo_envio - costo_mxn if costo_mxn>0 else 0
                with st.container(border=True):
                    st.write(f"**{item['title']}**")
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Precio ML", f"${precio}")
                    c2.metric("Vendidos", vendidos)
                    if costo_mxn>0:
                        c3.metric("Ganancia", f"${gan:.0f}", delta="SI" if gan>0 else "NO")
                    st.link_button("Ver en ML", item['permalink'], use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
        st.divider()
        st.link_button(f"Amazon: {query_final}", f"https://www.amazon.com.mx/s?k={quote_plus(query_final)}", use_container_width=True)
        st.link_button(f"Walmart: {query_final}", f"https://www.walmart.com.mx/search?q={quote_plus(query_final)}", use_container_width=True)
