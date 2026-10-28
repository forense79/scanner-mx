import streamlit as st
import requests
from urllib.parse import quote_plus

st.set_page_config(page_title="Scanner MX Pro", page_icon="📦", layout="wide")
st.title("📦 Scanner MX Pro")
st.caption("Cualquier producto • Calcula ganancia real")

with st.sidebar:
    st.header("Tu compra")
    costo = st.number_input("¿Cuánto pagaste?", value=0.0, step=10.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_envio = st.number_input("Envío ML promedio", value=80.0)
    comision = st.slider("Comisión ML %", 12, 20, 16)
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    if costo>0:
        st.metric("Costo en MXN", f"${costo_mxn:.0f}")
    
    st.divider()
    st.write("Links rápidos")
    st.link_button("Amazon MX", "https://www.amazon.com.mx/", use_container_width=True)
    st.link_button("Walmart MX", "https://www.walmart.com.mx/", use_container_width=True)

query = st.text_input("¿Qué producto escaneaste?", placeholder="Ej: Ariel 5kg, Clorox 3L, Suavitel 2.8L")
foto = st.camera_input("Foto (opcional)")

if st.button("🔍 ANALIZAR AHORA", type="primary", use_container_width=True):
    if not query:
        st.warning("Escribe el producto")
    else:
        st.divider()
        st.subheader(f"Resultados para: {query}")
        
        col1, col2 = st.columns([2,1])
        
        with col1:
            # MercadoLibre
            try:
                url = f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(query)}&limit=6"
                r = requests.get(url, timeout=10).json()
                results = r.get('results', [])
                if not results:
                    st.info("No hay resultados en ML, prueba otro nombre")
                for item in results:
                    precio_ml = item['price']
                    vendidos = item.get('sold_quantity', 0)
                    comision_pesos = precio_ml * (comision/100)
                    ganancia = precio_ml - comision_pesos - costo_envio - costo_mxn if costo_mxn>0 else 0
                    roi = (ganancia/costo_mxn*100) if costo_mxn>0 else 0
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([3,1])
                        c1.write(f"**{item['title'][:90]}**")
                        c1.write(f"Vendidos: {vendidos} | ${precio_ml}")
                        if costo_mxn>0:
                            color = "green" if ganancia>0 else "red"
                            c2.metric(f"Ganancia", f"${ganancia:.0f}", f"{roi:.0f}% ROI")
                            if ganancia>0:
                                st.success(f"✅ SI DEJA - Ganas ${ganancia:.0f}")
                            else:
                                st.error(f"❌ NO DEJA - Pierdes ${abs(ganancia):.0f}")
                        c1.link_button("Ver en ML", item['permalink'], use_container_width=True)
            except Exception as e:
                st.error(f"Error ML: {e}")
        
        with col2:
            st.write("**Compara en otras tiendas**")
            st.link_button(f"Amazon MX: {query}", f"https://www.amazon.com.mx/s?k={quote_plus(query)}", use_container_width=True)
            st.link_button(f"Walmart MX: {query}", f"https://www.walmart.com.mx/search?q={quote_plus(query)}", use_container_width=True)
            st.link_button(f"Google Shopping: {query}", f"https://www.google.com/search?q={quote_plus(query)}+precio&tbm=shop", use_container_width=True)
            
            if costo_mxn>0:
                st.divider()
                st.write("**Para que deje 30%**")
                precio_objetivo = (costo_mxn + costo_envio) / (1 - comision/100) * 1.3
                st.metric("Véndelo mínimo en", f"${precio_objetivo:.0f}")

st.divider()
st.caption("Hecho para forense79/scanner - v2 Pro")
