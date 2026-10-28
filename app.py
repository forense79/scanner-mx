import streamlit as st
import requests
from urllib.parse import quote_plus
from PIL import Image
import io
import re
from datetime import datetime, timezone
import statistics

st.set_page_config(page_title="Scanner MX Pro", page_icon="📦", layout="wide")
st.title("📦 Scanner MX Pro")
st.caption("Foto → Identifica → Análisis Mercado Libre completo")

def ocr_from_image(pil_image):
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format='JPEG')
        buf.seek(0)
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", buf, "image/jpeg")},
            data={"apikey": "helloworld", "language": "spa", "isOverlayRequired": False},
            timeout=25
        )
        j = r.json()
        if j.get("IsErroredOnProcessing") == False:
            return j["ParsedResults"][0]["ParsedText"]
        return ""
    except Exception as e:
        return ""

def get_item_detail(item_id):
    try:
        r = requests.get(f"https://api.mercadolibre.com/items/{item_id}", timeout=8).json()
        return r
    except:
        return {}

def limpiar_query_inteligente(q):
    q = q.upper()
    q = q.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
    q = re.sub(r'[^A-Z0-9 ]', ' ', q)
    # Palabras que hacen fallar la búsqueda en ML
    basura = {"PARA","DE","CON","Y","FREE","UNAS","UÑAS","PARA","LA","EL","EN"}
    palabras = [p for p in q.split() if p not in basura and len(p)>1]
    return palabras

with st.sidebar:
    st.header("Tu compra")
    costo = st.number_input("¿Cuánto pagaste?", value=0.0, step=5.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_envio = st.number_input("Envío que pagas", value=85.0)
    comision_pct = st.slider("Comisión ML %", 10, 20, 14)
    st.caption("Belleza/Cosméticos = 14% - Abarrotes = 15%")
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    if costo>0:
        st.metric("Costo MXN", f"${costo_mxn:.0f}")

foto = st.camera_input("📸 Toma foto del producto")
uploaded = st.file_uploader("O sube de galería", type=["jpg","png","jpeg"])

imagen = None
if foto:
    imagen = Image.open(foto)
elif uploaded:
    imagen = Image.open(uploaded)

query_auto = ""
if imagen:
    st.image(imagen, width=350)
    with st.spinner("Identificando producto..."):
        texto = ocr_from_image(imagen)
        if texto:
            palabras = limpiar_query_inteligente(texto)
            query_auto = " ".join(palabras[:4])
            if len(query_auto) < 2:
                query_auto = texto[:30]
            st.success(f"Detectado: **{query_auto}**")
            with st.expander("Ver texto leído"):
                st.write(texto)
        else:
            st.warning("No leí texto, intenta más cerca")

query_final = st.text_input("Producto a analizar (puedes editar)", value=query_auto, placeholder="Ej: YUYA ESMALTE")

if st.button("🔍 ANALIZAR MERCADO COMPLETO", type="primary", use_container_width=True):
    if not query_final:
        st.warning("Toma foto primero")
    else:
        palabras_limpias = limpiar_query_inteligente(query_final)
        
        # Intentos de búsqueda inteligentes
        queries_intento = []
        if palabras_limpias:
            queries_intento.append(" ".join(palabras_limpias[:3]))
            queries_intento.append(" ".join(palabras_limpias[:2]))
            queries_intento.append(palabras_limpias[0])
        queries_intento.append("YUYA ESMALTE")
        queries_intento.append("YUYA")
        queries_intento.append(query_final[:15])
        
        # Elimina duplicados manteniendo orden
        seen = set()
        queries_intento = [x for x in queries_intento if not (x in seen or seen.add(x))]

        results = []
        query_usada = ""
        
        with st.spinner("Buscando en MercadoLibre..."):
            for q in queries_intento:
                if not q or len(q) < 2:
                    continue
                url = f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(q)}&limit=25"
                try:
                    data = requests.get(url, timeout=12).json()
                    tmp = data.get('results', [])
                    if tmp:
                        results = tmp
                        query_usada = q
                        break
                except:
                    continue
        
        if not results:
            st.error("No encontré nada ni con YUYA. Prueba con solo 'esmalte' o 'YUYA'")
            st.stop()
        
        # --- ANALISIS ---
        precios = [r['price'] for r in results]
        vendidos_list = [r.get('sold_quantity',0) for r in results]
        
        total_vendedores = len(results)
        precio_min = min(precios)
        precio_max = max(precios)
        precio_prom = sum(precios)/len(precios)
        precio_mediana = statistics.median(precios)
        total_vendidos = sum(vendidos_list)
        
        # Ventas por mes estimado
        ventas_mes_estimadas = []
        for r in results[:6]:
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
        
        ventas_mes_prom = sum(ventas_mes_estimadas)/len(ventas_mes_estimadas) if ventas_mes_estimadas else (total_vendidos/total_vendedores/12 if total_vendedores>0 else 0)

        st.divider()
        st.subheader(f"📊 Análisis: {query_final}")
        st.caption(f"Búsqueda real usada: {query_usada} - {total_vendedores} resultados")
        
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Vendedores", total_vendedores)
        c2.metric("Precio prom", f"${precio_prom:.0f}")
        c3.metric("Min - Max", f"${precio_min:.0f} / ${precio_max:.0f}")
        c4.metric("Mediana", f"${precio_mediana:.0f}")
        
        c1,c2,c3 = st.columns(3)
        c1.metric("Total vendidos", f"{total_vendidos}")
        c2.metric("Ventas/mes x vendedor", f"{ventas_mes_prom:.1f}")
        c3.metric("Mercado total/mes", f"{ventas_mes_prom * total_vendedores:.0f} pzas")
        
        # --- COSTOS ML ---
        st.divider()
        st.subheader("💰 Lo que cobra MercadoLibre")
        precio_ref = precio_mediana
        
        comision = precio_ref * (comision_pct/100)
        iva_comision = comision * 0.16
        isr = precio_ref * 0.01
        iva_ret = precio_ref * 0.08 if precio_ref > 1000 else 0
        total_ml = comision + iva_comision + isr + iva_ret + costo_envio
        
        neto = precio_ref - total_ml
        ganancia = neto - costo_mxn if costo_mxn>0 else 0
        
        col1,col2 = st.columns(2)
        with col1:
            st.write(f"**Si vendes en ${precio_ref:.0f}:**")
            st.write(f"- Comisión {comision_pct}%: ${comision:.0f}")
            st.write(f"- IVA comisión 16%: ${iva_comision:.0f}")
            st.write(f"- ISR 1%: ${isr:.0f}")
            st.write(f"- IVA ret 8%: ${iva_ret:.0f}")
            st.write(f"- Envío: ${costo_envio:.0f}")
            st.write(f"**Total ML: ${total_ml:.0f}**")
        with col2:
            st.metric("Recibes neto", f"${neto:.0f}")
            if costo_mxn>0:
                if ganancia>0:
                    st.success(f"GANANCIA ${ganancia:.0f} - ROI {ganancia/costo_mxn*100:.0f}%")
                    st.write(f"Véndelo mínimo en ${ (costo_mxn + total_ml)*1.1:.0f} para 10% ganancia")
                else:
                    st.error(f"PÉRDIDA ${ganancia:.0f}")
        
        st.divider()
        st.subheader("🏪 Top competencia")
        for r in results[:8]:
            with st.container(border=True):
                st.write(f"**{r['title'][:110]}**")
                cc1,cc2,cc3 = st.columns([1,1,1])
                cc1.write(f"${r['price']}")
                cc2.write(f"Vend: {r.get('sold_quantity',0)}")
                cc3.link_button("Ver", r['permalink'], use_container_width=True)
        
        st.divider()
        st.link_button(f"Comparar en Amazon", f"https://www.amazon.com.mx/s?k={quote_plus(query_usada)}", use_container_width=True)
