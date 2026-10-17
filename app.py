import streamlit as st
from PIL import Image
import requests
from urllib.parse import quote_plus

st.set_page_config(page_title="Scanner Auto MX", page_icon="📦", layout="centered")
st.title("📦 Scanner AUTO 3.0")
st.caption("Foto o barcode = ML + Amazon MX + Walmart")

# SIDEBAR
costo = st.sidebar.number_input("Costo pagado", value=0.0)
moneda = st.sidebar.selectbox("Moneda", ["MXN","USD"])
costo_mxn = costo * 18.5 if moneda=="USD" else costo
st.sidebar.divider()
st.sidebar.write("🔗 Fuentes: ML API + Amazon search + Walmart search")

def buscar_ml(query):
    try:
        r = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(query)}&limit=3", timeout=6).json()
        return r.get('results', [])
    except: return []

def link_amazon_mx(query):
    return f"https://www.amazon.com.mx/s?k={quote_plus(query)}"

def link_walmart_mx(query):
    return f"https://www.walmart.com.mx/search?q={quote_plus(query)}"

def mostrar_todo(productos, query):
    if not productos:
        st.error(f"No encontré '{query}' en ML. Pero revisa Amazon/Walmart abajo.")
    else:
        for prod in productos[:2]:
            precio = prod['price']
            vendidos = prod.get('sold_quantity',0)
            margen = precio * 0.84 - costo_mxn
            with st.container(border=True):
                st.markdown(f"**{prod['title'][:90]}**")
                c1,c2,c3 = st.columns(3)
                c1.metric("ML Precio", f"${precio}")
                c2.metric("Vendidos", vendidos)
                c3.metric("Tu Ganancia", f"${margen:.0f}")
                if margen > 150: st.success("✅ COMPRA - BUEN MARGEN")
                elif margen > 0: st.warning("⚠️ Margen bajo")
                else: st.error("❌ NO")
    
    st.divider()
    st.subheader("2️⃣ Amazon MX & 3️⃣ Walmart MX")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🔍 Ver en Amazon MX", link_amazon_mx(query), use_container_width=True)
        st.caption(f"Busca: {query} - Revisa precio y BSR")
    with col2:
        st.link_button("🔍 Ver en Walmart MX", link_walmart_mx(query), use_container_width=True)
        st.caption(f"Busca: {query}")

tab1, tab2 = st.tabs(["📷 FOTO PRODUCTO", "📊 CÓDIGO BARRAS"])

with tab1:
    foto = st.camera_input("Foto del frente (marca legible)", key="f1")
    up = st.file_uploader("O sube foto", type=["jpg","png","jpeg"], key="u1")
    src = foto or up
    if src:
        img = Image.open(src)
        st.image(img, width=300)
        query = st.text_input("Producto detectado (edita si hace falta)", value="Folex Instant Carpet", key="q1")
        if st.button("🔍 ANALIZAR TODO", type="primary", key="b1"):
            prods = buscar_ml(query)
            mostrar_todo(prods, query)

with tab2:
    st.info("Enfoca el código de barras, luz natural")
    bc_foto = st.camera_input("Escanear barras", key="f2")
    bc_up = st.file_uploader("O sube foto código", type=["jpg","png"], key="u2")
    bc_src = bc_foto or bc_up
    if bc_src:
        img = Image.open(bc_src)
        st.image(img, width=350)
        codigo = ""
        try:
            from pyzbar.pyzbar import decode
            d = decode(img)
            if d:
                codigo = d[0].data.decode()
                st.success(f"Código: {codigo}")
        except: pass
        
        codigo = st.text_input("Código / Nombre", value=codigo, key="q2")
        if codigo and st.button("🔍 ANALIZAR TODO", key="b2", type="primary"):
            prods = buscar_ml(codigo)
            mostrar_todo(prods, codigo)

st.caption("V3.0 - Auto ML + Amazon + Walmart | Tu link se actualiza solo")
