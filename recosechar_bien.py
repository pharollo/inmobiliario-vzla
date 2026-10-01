#!/usr/bin/env python3
"""Recosecha bienesonline DESDE UNA IP DOMÉSTICA y actualiza datos/congelado.json.
No corre en GitHub Actions: bienesonline no responde a IPs de datacenter."""
import json,re,sys,time
exec(open("cosechar.py").read().split("# ─────────────────────────── métrica")[0])

print("Recosechando bienesonline despacio…",flush=True)
t0=time.time()
nuevos=bienesonline()
print(f"  crudo: {len(nuevos)} en {time.time()-t0:.0f}s",flush=True)
if len(nuevos)<200:
    sys.exit(f"Muy poco ({len(nuevos)}) — no toco el congelado")

BAND=[(15,50,'XS'),(50,120,'S'),(120,300,'M'),(300,800,'L'),(800,5000,'XL')]
def banda(m):
    for a,b,n in BAND:
        if m and a<=m<b: return n
    return ''
def limpio(r):
    p,m=r.get('price'),r.get('m2')
    if not p or not m or not(15<=m<=5000): return False
    ppm=p/m
    return (3000<=p<=8e6 and 40<=ppm<=8000) if r['op']=='venta' else (40<=p<=60000 and 0.5<=ppm<=80)
lim=[r for r in nuevos if limpio(r)]
vis=set(); ded=[]
for r in lim:
    k=(r['op'],round(r['price']),round(r['m2']),r.get('city') or '')
    if k in vis: continue
    vis.add(k); ded.append(r)
print(f"  limpios {len(lim)} → {len(ded)} sin duplicados",flush=True)

filas=[dict(f='bien',op=r['op'][0],t=r['tipo'][0],b=banda(r['m2']),m=round(r['m2']),
            p=round(r['price']),pm=round(r['price']/r['m2'],1),e=r['region'],
            c=r.get('city') or '',z='',n=(r.get('name') or '')[:88],u=r['url'],q='')
       for r in ded]
cong=json.load(open("datos/congelado.json",encoding="utf-8"))
antes=sum(1 for r in cong if r['f']=='bien')
cong=[r for r in cong if r['f']!='bien']+filas
json.dump(cong,open("datos/congelado.json","w"),ensure_ascii=False,separators=(',',':'))
print(f"\ncongelado: bienesonline {antes} → {len(filas)}")
from collections import Counter
print("total congelado:",dict(Counter(r['f'] for r in cong)))
print("\nAhora corre:  python3 cosechar.py   (o lanza el workflow) para reconstruir la página")
