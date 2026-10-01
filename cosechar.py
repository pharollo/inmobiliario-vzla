#!/usr/bin/env python3
"""Recosecha ZonaVen y bienesonline, mezcla con lo congelado y reconstruye index.html.

Congelado = lo que no se puede recosechar sin intervención humana:
  - Facebook Marketplace: exige sesión iniciada en un navegador
  - mercadopiso: su protección antibots responde 403 desde datacenter
"""
import re,json,html,gzip,time,sys,os,threading,queue,urllib.request,statistics as st
from collections import Counter

UA={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                 '(KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept':'text/html,application/xhtml+xml','Accept-Encoding':'gzip',
    'Accept-Language':'es-VE,es;q=0.9'}
OP=urllib.request.build_opener(urllib.request.HTTPRedirectHandler)   # sigue 301/308

def get(u,t=30):
    with OP.open(urllib.request.Request(u,headers=UA),timeout=t) as r:
        b=r.read()
        if r.headers.get('Content-Encoding')=='gzip': b=gzip.decompress(b)
        return b.decode('utf-8','ignore')

def paralelo(items,fn,hilos=4,pausa=0.9,reintentos=2):
    out=[];lock=threading.Lock();q=queue.Queue()
    for x in items: q.put(x)
    def w():
        while True:
            try: x=q.get_nowait()
            except queue.Empty: return
            for intento in range(reintentos):
                try:
                    r=fn(x)
                    if r:
                        with lock: out.extend(r if isinstance(r,list) else [r])
                    break
                except urllib.error.HTTPError as e:
                    if e.code in (404,410): break          # el aviso ya no existe
                    time.sleep(2.5*(intento+1))            # 429/500: espera y reintenta
                except Exception:
                    time.sleep(2.0*(intento+1))
            q.task_done(); time.sleep(pausa)
    ts=[threading.Thread(target=w,daemon=True) for _ in range(hilos)]
    [t.start() for t in ts]
    while any(t.is_alive() for t in ts):
        time.sleep(30); print(f"    {len(out)} …",flush=True)
    [t.join() for t in ts]
    return out

# ─────────────────────────── ZonaVen ───────────────────────────
COM=re.compile(r'local|galp[oó]n|galpon|oficina|comercial|dep[oó]sito|deposito|fondo de comercio',re.I)
LD=re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',re.S)

def zonaven():
    urls=set()
    for n in (1,2):
        try:
            x=get(f'https://zonaven.com/sitemap-listings-{n}.xml',60)
            for u in re.findall(r'<loc>([^<]+)</loc>',x):
                if re.search(r'/(venta|alquiler)/',u) and COM.search(u): urls.add(u)
        except Exception as e: print(f"  sitemap {n} falló: {e}",flush=True)
    urls=sorted(urls)
    print(f"  ZonaVen: {len(urls)} URLs comerciales en el sitemap",flush=True)
    def una(u):
        h=get(u)
        for blob in LD.findall(h):
            try: d=json.loads(blob)
            except Exception: continue
            t=d.get('@type'); t=t if isinstance(t,list) else [t]
            if 'RealEstateListing' not in t: continue
            of=d.get('offers') or {}; fs=d.get('floorSize') or {}
            ad=d.get('address') or {}; g=d.get('geo') or {}
            nm=d.get('name') or ''
            if not of.get('price') or not fs.get('value'): return None
            tipo='galpon' if re.search(r'galp',nm+u,re.I) else 'oficina' if re.search(r'oficina',nm+u,re.I) else 'local'
            m=re.search(r'\ben ([^,]+),\s*([^-]+?)(?:\s*-\s*(.+))?$',nm)
            return dict(fuente='zonaven',op=('alquiler' if '/alquiler/' in u else 'venta'),tipo=tipo,
                price=of['price'],m2=fs['value'],zona=(m.group(1).strip() if m else None),
                city=(ad.get('addressLocality') or '').strip(),region=(ad.get('addressRegion') or '').strip(),
                lat=g.get('latitude'),lon=g.get('longitude'),name=nm,url=u)
        return None
    return paralelo(urls,una)

# ─────────────────────────── bienesonline ───────────────────────────
EST=['aragua','distrito-capital','miranda','carabobo','lara','zulia','anzoategui','bolivar',
     'nueva-esparta','falcon','monagas','tachira','merida','portuguesa','sucre','yaracuy',
     'trujillo','barinas','guarico','la-guaira','cojedes','apure']
NOM={'aragua':'Aragua','distrito-capital':'Distrito Capital','miranda':'Miranda','carabobo':'Carabobo',
 'lara':'Lara','zulia':'Zulia','anzoategui':'Anzoátegui','bolivar':'Bolívar','nueva-esparta':'Nueva Esparta',
 'falcon':'Falcón','monagas':'Monagas','tachira':'Táchira','merida':'Mérida','portuguesa':'Portuguesa',
 'sucre':'Sucre','yaracuy':'Yaracuy','trujillo':'Trujillo','barinas':'Barinas','guarico':'Guárico',
 'la-guaira':'La Guaira','cojedes':'Cojedes','apure':'Apure'}

def bienesonline():
    combos=[(o,t,e) for o in ('venta','alquiler') for t in ('local','galpon','oficina','deposito') for e in EST]
    print(f"  bienesonline: {len(combos)} páginas de categoría",flush=True)
    def una(c):
        o,t,e=c
        h=get(f"https://bienesonline.ai/es/venezuela/{o}/{t}/{e}")
        res=[]
        for p in re.split(r'(?=<a href="https://bienesonline\.ai/es/[^"]*/propiedad/)',h)[1:]:
            u=re.search(r'href="(https://bienesonline\.ai/es/[^"]*?/propiedad/[^"]+)"',p)
            pr=re.search(r'USD\s*([\d.,]+)',p); m2=re.search(r'([\d.,]+)\s*m²',p)
            ti=re.search(r'title="([^"]*)"',p)
            if not(u and pr and m2): continue
            try:
                precio=float(pr.group(1).replace('.','').replace(',','.'))
                sup=float(m2.group(1).replace('.','').replace(',','.'))
            except Exception: continue
            ciudad=u.group(1).split('/es/venezuela/')[1].split('/')[0].replace('-',' ').title()
            res.append(dict(fuente='bienesonline',op=o,tipo=('galpon' if t=='galpon' else 'oficina' if t=='oficina' else 'local'),
                price=precio,m2=sup,zona=None,city=ciudad,region=NOM.get(e,e),lat=None,lon=None,
                name=html.unescape(ti.group(1)) if ti else '',url=u.group(1)))
        return res
    return paralelo(combos,una,hilos=4,pausa=0.6)

# ─────────────────────────── métrica ───────────────────────────
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
med=lambda v: st.median(v) if v else None

def construir(nuevos,congelado):
    frescos=[r for r in nuevos if limpio(r)]
    for r in frescos: r['banda']=banda(r['m2'])
    # deduplicar (32% del crudo eran repetidos en la primera cosecha)
    vis=set(); ded=[]
    for r in frescos:
        k=(r['fuente'],r['op'],round(r['price']),round(r['m2']),r.get('city') or '')
        if k in vis: continue
        vis.add(k); ded.append(r)
    print(f"  limpios {len(frescos)} → {len(ded)} sin duplicados",flush=True)
    # el PATRÓN sale solo de las dos fuentes compatibles (mercadopiso sesga: ver LEEME)
    def patron(op,b,reg=None):
        if reg:
            v=[r['price']/r['m2'] for r in ded if r['op']==op and r['banda']==b and r['region']==reg]
            if len(v)>=5: return med(v)
        v=[r['price']/r['m2'] for r in ded if r['op']==op and r['banda']==b]
        return med(v) if len(v)>=5 else None
    filas=[]
    for r in ded:
        ppm=r['price']/r['m2']; pt=patron(r['op'],r['banda'],r['region'])
        e=dict(f=('zona' if r['fuente']=='zonaven' else 'bien'),op=r['op'][0],
               t=r['tipo'][0],b=r['banda'],m=round(r['m2']),p=round(r['price']),pm=round(ppm,1),
               e=r['region'],c=r.get('city') or '',z=(r.get('zona') or '')[:28],
               dv=(round(100*ppm/pt-100) if pt else None),n=(r.get('name') or '')[:88],u=r['url'],q='')
        if r['op']=='venta':
            a=patron('alquiler',r['banda'],r['region'])
            if a: e['y']=round(r['price']/(a*r['m2']*12),1)
        if r.get('lat'): e['la'],e['lo']=round(r['lat'],4),round(r['lon'],4)
        filas.append(e)
    TEL=re.compile(r'(?:\+?58[\s\-\.]?)?0?4(?:12|14|16|24|26)[\s\-\.]?\d{3}[\s\-\.]?\d{4}'
                   r'|(?:\+?58[\s\-\.]?)?0?2\d{2}[\s\-\.]?\d{3}[\s\-\.]?\d{4}')
    todo=filas+congelado
    for r in todo: r['n']=TEL.sub('····',r.get('n') or '')
    return todo

def main():
    print("cosechando…",flush=True)
    nuevos=zonaven()+bienesonline()
    print(f"  total crudo: {len(nuevos)}",flush=True)
    if len(nuevos)<300:
        print("DEMASIADO POCO — no toco nada para no romper la página publicada",flush=True)
        sys.exit(1)
    cong=json.load(open("datos/congelado.json",encoding="utf-8"))
    todo=construir(nuevos,cong)
    print("  por fuente:",dict(Counter(r['f'] for r in todo)),flush=True)
    h=open("plantilla.html",encoding="utf-8").read()
    hoy=time.strftime("%d/%m/%Y")
    h=h.replace('__DATOS__',json.dumps(todo,ensure_ascii=False,separators=(',',':')))
    h=re.sub(r'Septiembre 2026\.?',f'Portales actualizados el {hoy}; Facebook Marketplace y mercadopiso son la cosecha de septiembre de 2026 y no se refrescan solos.',h,count=1)
    open("index.html","w",encoding="utf-8").write(h)
    json.dump(todo,open("datos/actual.json","w"),ensure_ascii=False,separators=(',',':'))
    print(f"index.html reconstruido: {len(todo)} avisos, {len(h)} bytes",flush=True)

if __name__=="__main__": main()
