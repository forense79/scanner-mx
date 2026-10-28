import streamlit as st, requests, io, re, statistics
from urllib.parse import quote_plus
from PIL import Image
from datetime import datetime, timezone

st.set_page_config(page_title="Scanner MX", layout="wide")
st.title("📦 Scanner MX")

H={"User-Agent":"Mozilla/5.0"}

def ocr(img):
 try:
  b=io.BytesIO(); img.save(b,format='JPEG'); b.seek(0)
  r=requests.post("https://api.ocr.space/parse/image",files={"file":("a.jpg",b,"image/jpeg")},data={"apikey":"helloworld","language":"spa"},timeout=20)
  return r.json()["ParsedResults"][0]["ParsedText"]
 except: return ""

def busquedas(t):
 t=t.upper()
 if "H24" in t or "PROFARDEN" in t: return ["casa y jardin 700ml","H24 casa jardin","casa y jardin"]
 if "RAID" in t: return ["raid casa y jardin"]
 w=re.sub(r'[^A-Z0-9 ]',' ',t).split()
 q=[]
 for i in range(len(w),0,-1):
  s=" ".join(w[:i])
  if len(s)>2: q.append(s)
 q.append("casa y jardin")
 return list(dict.fromkeys(q))

with st.sidebar:
 c=st.number_input("Pagaste",value=0.0)
 env=st.number_input("Envio",value=85.0)
 pct=st.slider("Comision %",10,20,15)

f=st.camera_input("Foto")
up=st.file_uploader("Galeria",type=["jpg","png","jpeg"])
im=None
if f: im=Image.open(f)
elif up: im=Image.open(up)

qa=""
if im:
 st.image(im,width=300)
 with st.spinner("Leyendo..."):
  txt=ocr(im)
  if txt:
   qa=" ".join(re.sub(r'[^A-Z0-9 ]',' ',txt.upper()).split()[:4])
   st.success(qa)
   with st.expander("Texto"): st.write(txt)

qf=st.text_input("Producto",value=qa)

if st.button("🔍 ANALIZAR",type="primary",use_container_width=True):
 qs=busquedas(qf)
 res=[]; qu=""
 for q in qs:
  try:
   r=requests.get(f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(q)}&limit=20",headers=H,timeout=10).json().get('results',[])
   if r: res=r; qu=q; break
  except: pass
 if not res:
  st.error("No dejo API, abre manual")
  st.link_button("Ver ML",f"https://listado.mercadolibre.com.mx/{quote_plus('casa y jardin')}")
  st.stop()
 prec=[x['price'] for x in res]
 med=statistics.median(prec)
 st.subheader(f"{qu} - {len(res)} vend")
 c1,c2,c3=st.columns(3)
 c1.metric("Vend",len(res)); c2.metric("Prom",f"${sum(prec)/len(prec):.0f}"); c3.metric("Med",f"${med:.0f}")
 tot=med*(pct/100)*1.16+med*0.01+env
 neto=med-tot
 st.metric("Neto",f"${neto:.0f}")
 if c>0:
  g=neto-c
  if g>0: st.success(f"Ganancia ${g:.0f}")
  else: st.error(f"Perdida ${g:.0f}")
 for r in res[:8]:
  with st.container(border=True):
   st.write(f"{r['title'][:100]} - ${r['price']}")
   st.link_button("Ver",r['permalink'])
