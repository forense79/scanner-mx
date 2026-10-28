import streamlit as st, requests, io, re, statistics, random
from urllib.parse import quote_plus
from PIL import Image

st.set_page_config(page_title="Scanner Universal", layout="wide")
st.title("📦 Scanner Universal - Súper a ML")

H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

def ocr(img):
 try:
  b=io.BytesIO(); img.save(b,format='JPEG'); b.seek(0)
  r=requests.post("https://api.ocr.space/parse/image",files={"file":("a.jpg",b,"image/jpeg")},data={"apikey":"helloworld","language":"spa","OCREngine":"2"},timeout=25)
  j=r.json()
  return j["ParsedResults"][0]["ParsedText"] if not j.get("IsErroredOnProcessing") else ""
 except: return ""

def limpiar_texto(t):
 t=t.upper()
 # corrige errores comunes del OCR
 t=t.replace("AHTP","5HTP").replace("5 HTP","5HTP").replace("5HTP+B6","5HTP B6")
 t=t.replace("PLEMENTO","SUPLEMENTO").replace("AUPLEMENTO","SUPLEMENTO")
 t=re.sub(r'[^A-Z0-9+ ]',' ',t)
 t=" ".join(t.split())
 return t

def generar_busquedas(texto_ocr):
 texto=limpiar_texto(texto_ocr)
 if not texto: return []
 palabras=texto.split()
 # quita basura
 basura={"CONT","NET","CONTENIDO","CAPS","TABLETAS","PIEZAS","ML","G","MG","ORIGINAL","SUPLEMENTO","ALIMENTICIO"}
 palabras=[p for p in palabras if p not in basura and len(p)>1]
 busquedas=[]
 # crea combinaciones de la foto, de mas especifico a general
 for i in range(min(5,len(palabras)),0,-1):
  busquedas.append(" ".join(palabras[:i]))
 # si tiene numeros como 5HTP, conservalos
 if len(palabras)>=2:
  busquedas.append(" ".join(palabras[:2]))
 busquedas.append(palabras[0] if palabras else texto[:15])
 return list(dict.fromkeys([b for b in busquedas if len(b)>=3]))[:6]

def buscar_ml(q):
 try:
  url=f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(q)}&limit=30"
  resp=requests.get(url,headers=H,timeout=10)
  data=resp.json()
  results=data.get('results',[])
  # filtra precios locos
  results=[r for r in results if 15 < r['price'] < 10000]
  return results
 except:
  return []

with st.sidebar:
 st.header("Tu costo")
 costo=st.number_input("Cuánto pagaste en súper $",value=0.0)
 envio=st.number_input("Envío ML $",value=85.0)
 comision=st.slider("Comisión %",8,20,14)

f=st.camera_input("📸 Toma foto al producto")
up=st.file_uploader("O súbela",type=["jpg","png","jpeg"])
im=None
if f: im=Image.open(f)
elif up: im=Image.open(up)

texto_ocr=""
query_auto=""
if im:
 st.image(im,width=320)
 with st.spinner("Leyendo etiqueta..."):
  texto_ocr=ocr(im)
  if texto_ocr:
   query_auto=limpiar_texto(texto_ocr)
   st.success(f"Leído: {query_auto[:80]}")
   with st.expander("Ver texto completo"): st.write(texto_ocr)
  else:
   st.warning("No pude leer bien, escribe abajo")

query_final=st.text_input("Producto a buscar (puedes corregir)",value=query_auto)

if st.button("🔍 ANALIZAR SI SE VENDE",type="primary",use_container_width=True):
 if not query_final:
  st.warning("Toma una foto o escribe el nombre")
  st.stop()
 
 queries=generar_busquedas(query_final)
 st.write(f"Voy a probar: {queries}")
 
 resultados=[]; q_usada=""
 for q in queries:
  with st.spinner(f"Buscando {q}..."):
   r=buscar_ml(q)
   if len(r)>=2:
    # quita duplicados por precio para que no salga mismo precio
    unicos={}
    for item in r:
     unicos[item['price']]=item
    lista=list(unicos.values())
    if len(lista)>=3:
     resultados=lista; q_usada=q; break
   elif len(r)>0 and not resultados:
    resultados=r; q_usada=q # guarda aunque sea pocos

 if not resultados:
  st.error(f"No se encontró '{query_final}' en ML. Puede ser que no se venda o esté bloqueado.")
  st.link_button("Ver manual en ML",f"https://listado.mercadolibre.com.mx/{quote_plus(query_final)}",use_container_width=True)
  st.stop()
 
 precios=sorted([x['price'] for x in resultados])
 precios_unicos=sorted(set(precios))
 mediana=statistics.median(precios)
 promedio=sum(precios)/len(precios)
 
 st.divider()
 st.success(f"✅ SI SE VENDE con: '{q_usada}' - {len(resultados)} vendedores")
 col1,col2,col3,col4=st.columns(4)
 col1.metric("Min",f"${min(precios)}")
 col2.metric("Max",f"${max(precios)}")
 col3.metric("Promedio",f"${promedio:.0f}")
 col4.metric("Mediana",f"${mediana:.0f}")
 
 st.caption(f"Precios distintos encontrados: {precios_unicos[:12]}")
 
 st.divider()
 st.subheader("💰 ¿Te conviene?")
 neto=mediana - (mediana*(comision/100)*1.16 + mediana*0.01 + envio)
 st.metric(f"Si vendes a ${mediana:.0f}, recibes",f"${neto:.0f}")
 if costo>0:
  ganancia=neto-costo
  roi=(ganancia/costo*100) if costo>0 else 0
  if ganancia>0:
   st.success(f"GANANCIA ${ganancia:.0f} | ROI {roi:.0f}% - SI CONVIENE")
  else:
   st.error(f"PÉRDIDA ${ganancia:.0f} - NO CONVIENE")
  st.write(f"Precio mínimo para ganar 20%: ${((costo+envio)*1.35):.0f}")

 st.divider()
 for item in resultados[:12]:
  with st.container(border=True):
   st.write(f"**{item['title'][:110]}**")
   st.write(f"${item['price']} | Vendidos: {item.get('sold_quantity',0)}")
   st.link_button("Ver en ML",item['permalink'],use_container_width=True)
