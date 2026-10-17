import streamlit as st
import requests
import google.generativeai as genai
from PIL import Image
from urllib.parse import quote_plus
import json

st.set_page_config(page_title="Scanner Total MX", page_icon="🔍", layout="centered")
st.title("🔍 Scanner Total MX")
st.caption("Foto -> Identifica -> ML + Amazon + Walmart")

# --- CONFIG KEYS ---
with st.sidebar:
    st.header("🔑 Configuración")
    gemini_key = st.text_input("Gemini API Key", type="password")
    serp_key = st.text_input("SerpApi Key", type="password")
    st.divider()
    costo = st.number_input("Cuánto pagaste?", value=0.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo

if not gemini_key or not serp_key:
    st.warning("👈 Pon tus 2 keys en la barra lateral para empezar")
    st.stop()

genai.configure(api_key=gemini_key)

# --- 1. TOMAR FOTO ---
foto = st.camera_input("1️⃣ Toma foto del producto")
upload = st.file_uploader("O sube foto de galería", type=['jpg','png','jpeg'])

imagen = foto if foto else upload

if imagen:
    img = Image.open(imagen)
    st.image(img, caption="Foto tomada", use_container_width=True)

    if st.button("🚀 IDENTIFICAR Y ANALIZAR", type="primary", use_container_width=True):
        
        # --- 2. IDENTIFICAR CON GEMINI (Google Vision) ---
        with st.status("2️⃣ Identificando producto con Google AI...", expanded=True):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Identifica este producto de supermercado/limpieza. Dame solo: MARCA + NOMBRE + TAMAÑO. Ej: 'Clorox 1L' o 'Ariel 5kg'. Si no sabes, adivina lo más cercano. Responde en 5 palabras máximo."
                response = model.generate_content([prompt, img])
                producto = response.text.strip().replace('"','').replace("'","")
                st.success(f"Producto identificado: **{producto}**")
            except Exception as e:
                st.error(f"Error Gemini: {e}")
                st.stop()

        q = quote_plus(producto)

        # --- 3. MERCADO LIBRE ---
        st.divider()
        st.subheader(f"3️⃣ Mercado Libre: {producto}")
        try:
            ml = requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={q}&limit=10", timeout=15).json()
            results = ml.get('results', [])
            st.metric("Vendedores encontrados", len(results))
            
            if results:
                # Agrupar por precio
                precios = [r['price'] for r in results]
                for r in results[:3]:
                    with st.container(border=True):
                        st.write(f"**{r['title'][:80]}**")
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Precio", f"${r['price']}")
                        c2.metric("Vendidos", r.get('sold_quantity',0))
                        c3.metric("Disponibles", r.get('available_quantity',0))
                        if costo_mxn>0:
                            gan = r['price']*0.84 - costo_mxn
                            st.write(f"Tu ganancia: ${gan:.0f}")
                        st.link_button("Ver en ML", r['permalink'], use_container_width=True)
                
                st.info(f"Precio promedio ML: ${sum(precios)/len(precios):.0f} | Más barato: ${min(precios)} | Más caro: ${max(precios)}")
            else:
                st.warning("No encontrado en ML")
        except Exception as e:
            st.error(f"Error ML: {e}")

        # --- 4. AMAZON MX (vía SerpApi) ---
        st.divider()
        st.subheader(f"4️⃣ Amazon.com.mx: {producto}")
        try:
            params = {"engine":"amazon","k":producto,"amazon_domain":"amazon.com.mx","api_key":serp_key}
            amz = requests.get("https://serpapi.com/search", params=params, timeout=20).json()
            amz_results = amz.get('organic_results', [])[:3]
            
            if amz_results:
                for a in amz_results:
                    with st.container(border=True):
                        st.write(f"**{a.get('title','')}**")
                        price = a.get('price',{}).get('extracted_price','N/A')
                        st.metric("Precio Amazon", f"${price}")
                        # BSR no siempre viene, estimado
                        st.write(f"Rating: {a.get('rating','N/A')} | Reviews: {a.get('reviews','N/A')}")
                        st.link_button("Ver en Amazon", a.get('link',''), use_container_width=True)
                        # BSR
                        if 'extensions' in a:
                            st.caption(f"Info: {a['extensions']}")
            else:
                st.warning("No encontrado en Amazon, buscando...")
                st.link_button("Buscar manual", f"https://www.amazon.com.mx/s?k={q}")
        except Exception as e:
            st.error(f"Error Amazon: {e}")
            st.link_button("Buscar en Amazon", f"https://www.amazon.com.mx/s?k={q}")

        # --- 5. WALMART ---
        st.divider()
        st.subheader(f"5️⃣ Walmart.com.mx: {producto}")
        try:
            params_w = {"engine":"walmart","query":producto,"api_key":serp_key}
            wm = requests.get("https://serpapi.com/search", params=params_w, timeout=20).json()
            wm_results = wm.get('organic_results', [])[:3]
            if wm_results:
                for w in wm_results:
                    with st.container(border=True):
                        st.write(f"**{w.get('title','')}**")
                        st.metric("Precio Walmart", w.get('primary_offer',{}).get('offer_price','N/A'))
                        st.link_button("Ver en Walmart", w.get('product_page_url',''), use_container_width=True)
            else:
                st.link_button("Buscar en Walmart", f"https://www.walmart.com.mx/search?q={q}")
        except Exception as e:
            st.link_button("Buscar en Walmart", f"https://www.walmart.com.mx/search?q={q}")

        # --- 6. RESUMEN ---
        st.divider()
        st.subheader("6️⃣ RESUMEN FINAL")
        st.json({
            "Producto": producto,
            "Tu costo MXN": costo_mxn,
            "Foto": "Si" if imagen else "No"
        })
        st.success("Análisis completo. ¿Conviene comprar para revender?") 
