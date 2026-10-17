import streamlit as st
import requests
from urllib.parse import quote_plus

st.set_page_config(page_title="Scanner MX", page_icon="📦", layout="centered")
st.title("📦 Scanner Genérico MX")
st.caption("Cualquier producto - Foto + análisis real")

# SIDEBAR COSTO
st.sidebar.header("Tu costo")
costo = st.sidebar.number_input("Cuánto pagaste?", value=0.0, step=1.0)
moneda = st.sidebar.selectbox("Moneda", ["MXN","USD"])
costo_mxn = costo * 18.5 if moneda == "USD" else costo
if costo > 0:
    st.sidebar.metric("Costo en MXN", f"${costo_mxn:.0f}")

# ENTRADA
query = st.text_input("Nombre del producto", placeholder="Ej: Suavitel 3L, Clorox, Ariel, etc")
foto = st.camera_input("📷 Toma foto del producto (para tu registro)")

if st.button("🔍 ANALIZAR CUALQUIER PRODUCTO", type="primary", use_container_width=True):
    if not query:
        st.error("Escribe el nombre del producto primero")
    else:
        q = quote_plus(query)
        
        # 1. MERCADO LIBRE REAL
        st.divider()
        st.subheader(f"1️⃣ Mercado Libre: {query}")
        try:
            url = f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=5"
            data = requests.get(url, timeout=10).json()
            results = data.get('results', [])
            
            if not results:
                st.warning("No se encontró en ML")
            else:
                for r in results[:3]:
                    precio = r['price']
                    vendidos = r.get('sold_quantity', 0)
                    disponible = r.get('available_quantity', 0)
                    
                    st.container(border=True)
                    with st.container(border=True):
                        st.write(f"**{r['title']}**")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Precio ML", f"${precio}")
                        col2.metric("Vendidos", vendidos)
                        col3.metric("Stock", disponible)
                        
                        if costo_mxn > 0:
                            ganancia = precio * 0.84 - costo_mxn
                            margen = (ganancia / costo_mxn * 100) if costo_mxn>0 else 0
                            st.metric("Tu ganancia estimada", f"${ganancia:.0f} ({margen:.0f}%)")
                            if ganancia > 100:
                                st.success("✅ COMPRA - Buen margen")
                            elif ganancia > 0:
                                st.warning("⚠️ Margen bajo")
                            else:
                                st.error("❌ No conviene")
                        
                        st.link_button("Ver en Mercado Libre", r['permalink'], use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")

        # 2 y 3 - LINKS
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("2️⃣ Amazon MX")
            st.link_button("Buscar en Amazon", f"https://www.amazon.com.mx/s?k={q}", use_container_width=True)
        with c2:
            st.subheader("3️⃣ Walmart")
            st.link_button("Buscar en Walmart", f"https://www.walmart.com.mx/search?q={q}", use_container_width=True)

        st.divider()
        st.caption(f"Análisis para: {query} | Foto guardada: {'Si' if foto else 'No'}")
