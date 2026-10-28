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
st.caption("Foto → Detecta → Análisis completo ML")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def ocr_from_image(pil_image):
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format='JPEG')
        buf.seek(0)
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", buf, "image/jpeg")},
            data={"apikey": "helloworld", "language": "spa"},
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
        r = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=HEADERS, timeout=8).json()
        return r
    except:
        return {}

def limpiar_texto(q):
    q = q.upper()
    q = q.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
    q = re.sub(r'[^A-Z0-9 ]', ' ', q)
    return q

with st.sidebar:
    st.header("Tu compra")
    costo = st.number_input("¿Cuánto pagaste?", value=0.0, step=5.0)
    moneda = st.selectbox("Moneda", ["MXN","USD"])
    costo_envio = st.number_input("Envío ML", value=85.0)
    comision_pct = st.slider("Comisión %", 10, 20, 15)
    costo_mxn = costo*18.5 if moneda=="USD" else costo
    if costo>0:
        st.metric("Costo MXN", f"${costo_mxn:.0f}")

foto = st.camera_input("📸 Foto del frente")
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
            limpio = limpiar_texto(texto)
            # Quita basura común
            basura = {"CONT","NET","ML","L","KG","GR","NO","SE","DEJE","ALCANCE","LOS","NINOS","NINOS","700","750","500"}
            palabras = [p for p in limpio.split() if p not in basura and len(p)>1]
            query_auto = " ".join(palabras[:4])
            if not query_auto:
                query_auto = limpio[:30]
            st.success(f"Detectado: **{query_auto}**")
            with st.expander("Ver texto leído"):
                st.write(texto)
        else:
            st.warning("No leí texto, intenta más cerca con luz")

query_final = st.text_input("Producto a analizar (editable)", value=query_auto, placeholder="Ej: H24 Casa Jardin")

if st.button("🔍 ANALIZAR MERCADO COMPLETO", type="primary", use_container_width=True):
    if not query_final:
        st.warning("Toma foto primero")
    else:
        limpio_final = limpiar_texto(query_final)
        palabras = limpio_final.split()
        
        # Crea intentos: completo, quitando última palabra cada vez
        queries = []
        for i in range(len(palabras), 0, -1):
            q = " ".join(palabras[:i])
            if len(q) >= 3:
                queries.append(q)
        # Agrega solo marca por si falla
        if len(palabras) > 0:
            queries.append(palabras[0])
        
        queries = list(dict.fromkeys(queries))  # sin duplicados
        
        results = []
        query_usada = ""
        
        with st.spinner("Buscando en MercadoLibre..."):
            for q in queries:
                url = f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(q)}&limit=25"
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=12)
                    if resp.status_code == 200:
                        data = resp.json()
                        tmp = data.get('results', [])
                        if tmp:
                            results = tmp
                            query_usada = q
                            break
                except Exception as e:
                    continue
        
        if not results:
            st.error(f"No encontré nada con {queries}. MercadoLibre no respondió.")
            st.link_button("Buscar manual en ML", f"https://listado.mercadolibre.com.mx/{quote_plus(query_final)}", use_container_width=True)
            st.stop()
        
        precios = [r['price'] for r in results]
        total_vendedores = len(results)
        precio_min = min(precios)
        precio_max = max(precios)
        precio_prom = sum(precios)/len(precios)
        precio_mediana = statistics.median(precios)
        total_vendidos = sum([r.get('sold_quantity',0) for r in results])
        
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
        
        ventas_mes_prom = sum(ventas_mes_estimadas)/len(ventas_mes_estimadas) if ventas_mes_estimadas else 4

        st.divider()
        st.subheader(f"📊 Análisis: {query_usada}")
        st.caption(f"{total_vendedores} vendedores encontrados")
        
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Vendedores", total_vendedores)
        c2.metric("Promedio", f"${precio_prom:.0f}")
        c3.metric("Min-Max", f"${precio_min:.0f}-${precio_max:.0f}")
        c4.metric("Mediana", f"${precio_mediana:.0f}")
        
        c1,c2,c3 = st.columns(3)
        c1.metric("Vendidos totales", total_vendidos)
        c2.metric("Ventas/mes por vendedor", f"{ventas_mes_prom:.1f}")
        c3.metric("Mercado total/mes", f"{ventas_mes_prom * total_vendedores:.0f}")
        
        st.divider()
        st.subheader("💰 Lo que cobra MercadoLibre")
        precio_ref = precio_mediana
        comision = precio_ref * (comision_pct/100)
        iva_comision = comision * 0.16
        isr = precio_ref * 0.01
        iva_ret = precio_ref * 0.08 if precio_ref > 1500 else 0
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
                    st.success(f"GANANCIA ${ganancia:.0f} ROI {ganancia/costo_mxn*100:.0f}%")
                    st.write(f"Para 10% vende en mínimo ${ (costo_mxn + total_ml)*1.15:.0f}")
                else:
                    st.error(f"PÉRDIDA ${ganancia:.0f}")
        
        st.divider()
        st.subheader("🏪 Competencia")
        for r in results[:10]:
            with st.container(border=True):
                st.write(f"**{r['title'][:110]}**")
                c1,c2,c3 = st.columns([1,1,1])
                c1.write(f"${r['price']}")
                c2.write(f"Vend: {r.get('sold_quantity',0)}")
                c3.link_button("Ver", r['permalink'], use_container_width=True)
