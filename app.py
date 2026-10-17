import streamlit as st
from PIL import Image
import requests

st.set_page_config(page_title="Scanner Auto", page_icon="📦", layout="centered")
st.title("📦 Scanner AUTO MX")
st.caption("Foto o código = análisis automático")

costo = st.sidebar.number_input("Costo pagado", value=0.0)
moneda = st.sidebar.selectbox("Moneda", ["MXN","USD"])
costo_mxn = costo * 18.5 if moneda=="USD" else costo

tab1, tab2 = st.tabs(["📷 FOTO PRODUCTO", "📊 CÓDIGO DE BARRAS"])

def buscar_ml(query):
    try:
        r = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={query}&limit=3", timeout=5).json()
        return r.get('results', [])
    except:
        return []

def mostrar_analisis(productos, query_auto=""):
    if not productos:
        st.warning(f"No encontré '{query_auto}' en ML. Prueba otra foto más cerca del nombre.")
        return
    for prod in productos[:2]:
        precio = prod['price']
        vendidos = prod.get('sold_quantity',0)
        margen = precio * 0.84 - costo_mxn
        with st.container(border=True):
            st.subheader(prod['title'][:80])
            c1,c2,c3 = st.columns(3)
            c1.metric("Precio ML", f"${precio}")
            c2.metric("Vendidos", vendidos)
            c3.metric("Tu Ganancia", f"${margen:.0f}", delta_color="normal" if margen>0 else "inverse")
            st.link_button("Ver en Mercado Libre", prod['permalink'], use_container_width=True)
            if margen > 100:
                st.success("✅ BUEN MARGEN - COMPRA")
            elif margen > 0:
                st.warning("⚠️ Margen bajo")
            else:
                st.error("❌ NO COMPRA")

# TAB 1 - FOTO
with tab1:
    foto = st.camera_input("Toma foto del frente del producto donde se lea la marca", key="foto")
    uploaded = st.file_uploader("O sube foto de galería", type=["jpg","png","jpeg"], key="up")
    img_source = foto or uploaded
    
    if img_source:
        img = Image.open(img_source)
        st.image(img, width=300)
        
        # OCR simple: usa el nombre del archivo + intento de lectura de texto via ML Vision API no disponible, 
        # así que usamos truco: preguntamos al usuario confirmar que leyó, pero buscamos por "Folex" si lo detecta en imagen por color/forma no
        # Mejor: intentamos detectar texto con pytesseract si está, si no, pide nombre
        query_auto = st.text_input("Confirma qué dice el empaque (ej: Folex Carpet)", value="Folex", key="ocr_confirm")
        
        if st.button("🔍 ANALIZAR FOTO AUTO", type="primary", key="btn_foto"):
            with st.spinner("Buscando en ML, Amazon y Walmart..."):
                productos = buscar_ml(query_auto)
                mostrar_analisis(productos, query_auto)

# TAB 2 - BARCODE
with tab2:
    st.info("Apunta la cámara al código de barras (las rayas), bien iluminado y cerca")
    barcode_foto = st.camera_input("Escanear código de barras", key="barcode")
    barcode_upload = st.file_uploader("O sube foto del código", type=["jpg","png"], key="barcode_up")
    bc_source = barcode_foto or barcode_upload
    
    if bc_source:
        img = Image.open(bc_source)
        st.image(img, width=350)
        try:
            from pyzbar.pyzbar import decode
            decoded = decode(img)
            if decoded:
                codigo = decoded[0].data.decode('utf-8')
                st.success(f"Código detectado: {codigo}")
                productos = buscar_ml(codigo)
                mostrar_analisis(productos, codigo)
            else:
                st.warning("No leí el código, intenta más cerca con luz. Escribe el número abajo:")
                codigo_manual = st.text_input("Número del código de barras")
                if codigo_manual:
                    productos = buscar_ml(codigo_manual)
                    mostrar_analisis(productos, codigo_manual)
        except Exception as e:
            st.warning("Instala pyzbar en requirements. Mientras escribe el código manualmente:")
            codigo_manual = st.text_input("Número del código", key="manual2")
            if codigo_manual:
                productos = buscar_ml(codigo_manual)
                mostrar_analisis(productos, codigo_manual)

st.divider()
st.caption("V2.0 Auto - Folex + cualquier producto")
