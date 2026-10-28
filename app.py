import streamlit as st
import requests
from urllib.parse import quote_plus
from PIL import Image
import io
import re
from datetime import datetime, timezone
import statistics

st.set_page_config(page_title="Scanner MX Pro", page_icon="📦", layout="wide")
st.title("📦 Scanner MX Pro - Análisis ML")
st.caption("Foto → Identifica → Analiza mercado")

def ocr_from_image(pil_image):
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format='JPEG')
        buf.seek(0)
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", buf, "image/jpeg")},
            data={"apikey": "helloworld", "language": "spa"},
            timeout=20
        )
        j = r.json()
        if j.get("IsErroredOnProcessing") == False:
            return j["ParsedResults"][0]["ParsedText"]
        return ""
    except:
        return ""

def get_item_detail(item_id):
    try:
        r = requests.get(f"https://api.mercadolibre.com/items/{item_id}", timeout=8).json()
        return r
    except:
        return {}

with st.sidebar:
    st.header("Tu compra")
    costo = st.number_input("¿Cuánto pagaste?", value=0.0, step=10.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    st.metric("Costo MXN", f"${costo_mxn:.0f}")
    st.divider()
    st.write("Costos ML")
    comision_pct = st.slider("Comisión categoría %", 10, 20, 15)
    costo_envio_prom = st.number_input("Envío que pagas tú", value=85.0)
    st.caption("Se calcula IVA 16% sobre comisión + retenciones ISR 1% e IVA 8%")

foto = st.camera_input("📸 Foto del producto")
uploaded = st.file_uploader("O sube de galería", type=["jpg","png","jpeg"])
imagen = None
if foto:
    imagen = Image.open(foto)
elif uploaded:
    imagen = Image.open(uploaded)

query_auto = ""
if imagen:
    st.image(imagen, width=350)
    with st.spinner("Identificando..."):
        texto = ocr_from_image(imagen)
        if texto:
            texto_upper = re.sub(r'[^A-Z0-9ÁÉÍÓÚÑ ]', ' ', texto.upper())
            palabras = [p for p in texto_upper.split() if len(p) > 2]
            basura = {"CONT","NET","PESO","LITROS","ML","KG","GR","HECHO","MEXICO"}
            palabras = [p for p in palabras if p not in basura]
            query_auto = " ".join(palabras[:5])
            st.success(f"Detectado: **{query_auto}**")

query_final = st.text_input("Producto a analizar", value=query_auto)

if st.button("🔍 ANALIZAR MERCADO COMPLETO", type="primary", use_container_width=True):
    if not query_final:
        st.warning("Toma foto primero")
    else:
        with st.spinner("Buscando en MercadoLibre..."):
            url = f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(query_final)}&limit=20"
            data = requests.get(url, timeout=12).json()
            results = data.get('results', [])
            
            if not results:
                st.error("No encontré nada, prueba con menos palabras")
                st.stop()
            
            # --- ANALISIS GENERAL ---
            precios = [r['price'] for r in results]
            vendidos_list = [r.get('sold_quantity',0) for r in results]
            
            total_vendedores = len(results)
            precio_min = min(precios)
            precio_max = max(precios)
            precio_prom = sum(precios)/len(precios)
            precio_mediana = statistics.median(precios)
            total_vendidos = sum(vendidos_list)
            
            # Ventas por mes - sacamos fecha de 3 items para estimar
            ventas_mes_estimadas = []
            for r in results[:5]:
                detail = get_item_detail(r['id'])
                try:
                    date_str = detail.get('date_created')
                    if date_str:
                        date_created = datetime.fromisoformat(date_str.replace('Z','+00:00'))
                        dias = (datetime.now(timezone.utc) - date_created).days
                        meses = max(dias/30, 1)
                        vpm = r.get('sold_quantity',0) / meses
                        ventas_mes_estimadas.append(vpm)
                except:
                    pass
            
            ventas_mes_prom = sum(ventas_mes_estimadas)/len(ventas_mes_estimadas) if ventas_mes_estimadas else 0
            
            st.divider()
            st.subheader(f"📊 Análisis de mercado: {query_final}")
            
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Vendedores activos", total_vendedores)
            c2.metric("Precio promedio", f"${precio_prom:.0f}")
            c3.metric("Rango", f"${precio_min:.0f} - ${precio_max:.0f}")
            c4.metric("Total vendidos (todos)", f"{total_vendidos}")
            
            c1,c2,c3 = st.columns(3)
            c1.metric("Mediana precio", f"${precio_mediana:.0f}")
            c2.metric("Ventas/mes estimado por vendedor", f"{ventas_mes_prom:.1f}")
            c3.metric("Ventas/mes totales mercado", f"{ventas_mes_prom * total_vendedores:.0f}")
            
            # --- CALCULADORA DE COMISIONES ---
            st.divider()
            st.subheader("💰 Desglose de costos MercadoLibre")
            
            # Usamos precio mediana como referencia de venta
            precio_venta_ref = precio_mediana
            
            comision = precio_venta_ref * (comision_pct/100)
            iva_comision = comision * 0.16
            isr_ret = precio_venta_ref * 0.01
            iva_ret = precio_venta_ref * 0.08 if precio_venta_ref > 1500 else 0  # solo si pasa de cierto monto
            total_retenciones = comision + iva_comision + isr_ret + iva_ret + costo_envio_prom
            
            neto = precio_venta_ref - total_retenciones
            ganancia = neto - costo_mxn if costo_mxn>0 else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Si vendes en ${precio_venta_ref:.0f}**")
                st.write(f"- Comisión ML ({comision_pct}%): ${comision:.0f}")
                st.write(f"- IVA sobre comisión (16%): ${iva_comision:.0f}")
                st.write(f"- ISR retención (1%): ${isr_ret:.0f}")
                st.write(f"- IVA retención (8%): ${iva_ret:.0f}")
                st.write(f"- Envío: ${costo_envio_prom:.0f}")
                st.write(f"**Total que te quita ML: ${total_retenciones:.0f}**")
            with col2:
                st.metric("Recibes neto", f"${neto:.0f}")
                if costo_mxn>0:
                    if ganancia>0:
                        st.success(f"GANANCIA: ${ganancia:.0f} ({ganancia/costo_mxn*100:.0f}% ROI)")
                    else:
                        st.error(f"PÉRDIDA: ${ganancia:.0f}")
            
            # --- TABLA VENDEDRES ---
            st.divider()
            st.subheader("🏪 Competencia")
            for r in results[:10]:
                with st.container(border=True):
                    c1,c2 = st.columns([3,1])
                    c1.write(f"**{r['title'][:100]}**")
                    c1.write(f"${r['price']} | Vendidos: {r.get('sold_quantity',0)} | {'Envío Full' if r.get('shipping',{}).get('logistic_type')=='fulfillment' else 'Envío normal'}")
                    c2.link_button("Ver", r['permalink'], use_container_width=True)
            
            st.divider()
            st.link_button(f"Ver todo en Amazon MX", f"https://www.amazon.com.mx/s?k={quote_plus(query_final)}", use_container_width=True)
