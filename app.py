import streamlit as st, requests, io, re, statistics, json
from urllib.parse import quote_plus
from PIL import Image

st.set_page_config(page_title="Scanner MX", layout="wide")
st.title("📦 Scanner MX Pro v7")

H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0","Accept-Language":"es-MX"}

def ocr(img):
 try:
  b=io.BytesIO(); img.save(b,format='JPEG'); b.seek(0)
  r=requests.post("https://api.ocr.space/parse/image",files={"file":("a.jpg",b,"image/jpeg")},data={"apikey":"helloworld","language":"spa"},timeout=20)
  return r.json()["ParsedResults"][0]["ParsedText"]
 except: return ""

def buscar_real(q):
 res=[]
 # Intento 1 - API oficial
 try:
  u=f"https://api.mercadolibre.com/sites/MLM/search?q={quote_plus(q)}&limit=30"
  j=requests.get(u,headers=H,timeout=10).json()
  if j.get('results'): return j['results']
 except: pass
 
 # Intento 2 - Scraping JSON interno de ML (este no lo bloquean)
 try:
  u=f"https://listado.mercadolibre.com.mx/{quote_plus(q)}"
  html=requests.get(u,headers=H,timeout=12).text
  # ML mete los productos en un JSON gigante
  m=re.search(r'"results":\s*\[(.*?)\]\s*,\s*"pagination"',html,re.DOTALL)
  if not m:
   m=re.search(r'"items":\s*\[(.*?)\]',html,re.DOTALL)
  if m:
   # saca todos los precios y titulos con regex del JSON
   items=re.findall(r'"title":"([^"]+)".*?"fraction":(\d+).*?"sold_quantity":(\d+)?',html)
   # otra forma
   if not items:
    titles=re.findall(r'"title":"([^"]{10,120})"',html)
    fracs=re.findall(r'"fraction":(\d+)',html)
    for i in range(min(len(titles),len(fracs),15)):
     try:
      p=int(fracs[i])
      if 10 < p < 5000: # filtra precios absurdos
       res.append({"title":titles[i],"price":p,"sold_quantity":5,"permalink":u})
     except: pass
   else:
    for t,f,s in items[:15]:
     try:
      p=int(f)
      if 10 < p < 5000:
       res.append({"title":t,"price":p,"sold_quantity":int(s) if s else 5,"permalink":u})
     except: pass
  return res
 except Exception as e:
  return []

def queries_inteligentes(t):
 t=t.upper()
 if "H24" in t or "PROFARDEN" in t or "ARDEN" in t:
  return ["Raid casa jardin","Baygon casa jardin","aerosol mata bichos","insecticida hogar"]
 if "YUYA" in t or "YARGE" in t:
  return ["Yuya esmalte","esmalte Yuya","esmalte uñas"]
 w=re.sub(r'[^A-Z0-9 ]',' ',t).split()
 base=" ".join(w[:4])
 return [base," ".join(w[:3])," ".join(w[:2]),w[0]]

with st.sidebar:
 c=st.number_input("Pagaste $",value=50.0)
 env=st.number_input("Envio ML",value=85.0)
 pct=st.slider("Comision %",10,20,15)

f=st.camera_input("Foto")
up=st.file_uploader("Galeria",type=["jpg","png","jpeg"])
im=None
if f: im=Image.open(f)
elif up: im=Image.open(up)

qa=""
if im:
 st.image(im,width=300)
 txt=ocr(im)
 if txt:
  qa=" ".join(re.sub(r'[^A-Z0-9 ]',' ',txt.upper()).split()[:4])
  st.success(f"Detectado: {qa}")
  with st.expander("Ver texto"): st.write(txt)

qf=st.text_input("Producto",value=qa)

if st.button("🔍 ANALIZAR",type="primary",use_container_width=True):
 qs=queries_inteligentes(qf)
 res=[]; usado=""
 for q in qs:
  st.write(f"Probando: {q}...")
  r=buscar_real(q)
  if r:
   # quita duplicados por precio igual
   vistos=set()
   filtrado=[]
   for x in r:
    if x['price'] not in vistos and 15 < x['price'] < 2000:
     vistos.add(x['price'])
     filtrado.append(x)
   if len(filtrado)>=3:
    res=filtrado; usado=q; break
 
 if not res:
  st.error("No encontre, prueba manual")
  st.link_button("Ver ML",f"https://listado.mercadolibre.com.mx/{quote_plus(qf)}")
  st.stop()

 prec=[x['price'] for x in res]
 prec=sorted(prec)
 med=statistics.median(prec)
 prom=sum(prec)/len(prec)
 st.divider()
 st.success(f"Con: {usado} - {len(res)} ofertas distintas")
 c1,c2,c3,c4=st.columns(4)
 c1.metric("Min",f"${min(prec)}"); c2.metric("Max",f"${max(prec)}")
 c3.metric("Prom",f"${prom:.0f}"); c4.metric("Mediana",f"${med:.0f}")
 
 st.write(f"Rango real: ${prec[0]} - ${prec[-1]} - Precios encontrados: {prec[:10]}")

 tot=med*(pct/100)*1.16+med*0.01+env
 neto=med-tot
 st.divider()
 st.metric(f"Vendes en ${med:.0f} recibes",f"${neto:.0f}")
 if c>0:
  g=neto-c
  if g>0: st.success(f"GANANCIA ${g:.0f} ROI {g/c*100:.0f}%")
  else: st.error(f"PERDIDA ${g:.0f}")
  st.caption(f"Para 10% ganancia vende en: ${(c+tot)*1.15:.0f}")

 for r in res[:12]:
  with st.container(border=True):
   st.write(f"**{r['title'][:110]}**")
   st.write(f"${r['price']} - Vend: {r.get('sold_quantity',0)}")
   st.link_button("Ver",r['permalink'],use_container_width=True)
