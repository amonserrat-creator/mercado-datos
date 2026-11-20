# Series mensuales (máx. 50 años) por producto para la sección «¿De golpe, cada mes o en el momento perfecto?»; escribe data/hist_series.json
# Construye las series mensuales (máx. 50 años) de cada producto: Yahoo (cierre ajustado) + extensiones con índices
import json, csv, re, ast, io, urllib.request
H = json.load(open('data/hist_mensual.json'))['px']
SHILLER = urllib.request.urlopen('https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv', timeout=60).read().decode()
M = lambda k: dict(H[k]['m'])
START = '1976-11'
def splice(old, new):  # old y new: dict ym->precio; se encadena por rentabilidades: antes del primer mes de new se usa old reescalado
    ks = sorted(new); f = ks[0]
    if f not in old: return dict(new)
    k = new[f] / old[f]; out = {y: v * k for y, v in old.items() if y < f}; out.update(new); return out
# S&P 500 con dividendos: Shiller (media mensual + dividendo/12) hasta 1987-12, después ^SP500TR (cierre de mes)
sh = {}; tr = None; prev = None
for r in csv.DictReader(io.StringIO(SHILLER)):
    ym = r['Date'][:7]; p = float(r['SP500']); d = float(r['Dividend'] or 0)
    if ym < '1976-01' or ym > '1988-01': prev = p if ym < '1976-01' else prev; continue
    tr = 1.0 if tr is None else tr * (p + d / 12) / prev; sh[ym] = tr; prev = p
SP = splice(sh, M('SP500TR'))
EXT = {'SPY': (SP, 'S&P 500 con dividendos: Shiller (medias mensuales) hasta 1987 y S&P 500 Total Return después'),
       'URTH': (splice(M('MSCIW'), M('URTH')), 'MSCI World sin dividendos hasta 2011 (índice de precios) y el ETF URTH después'),
       'QQQ': (splice(M('NDX'), M('QQQ')), 'Nasdaq-100 sin dividendos hasta 1999 y el ETF QQQ después'),
       'GLD': (splice(M('ORO'), M('GLD')), 'oro (futuro) hasta 2004 y el ETF GLD después'),
       'SLV': (splice(M('PLATA'), M('SLV')), 'plata (futuro) hasta 2006 y el ETF SLV después'),
       'CPER': (splice(M('COBRE'), M('CPER')), 'cobre (futuro) hasta 2011 y el ETF CPER después')}
P = set(ast.literal_eval(re.search(r'PORT = (\{.*?\})\n', open('intradia.py').read(), re.S).group(1))) - {'SPY'} | {'SPY'}
OUT = {}
for s in sorted(P):
    if s in EXT: m, nota = EXT[s]
    else: m, nota = M(s), None
    ks = [k for k in sorted(m) if k >= START]
    y, mo = int(ks[0][:4]), int(ks[0][5:]); seq = []; last = None; fill = []
    while '%04d-%02d' % (y, mo) <= ks[-1]:
        k = '%04d-%02d' % (y, mo)
        if k in m: last = m[k]
        else: fill.append(k)
        seq.append(last); mo += 1
        if mo > 12: y += 1; mo = 1
    b = seq[0]
    OUT[s] = {'d0': ks[0], 'p': [float('%.5g' % (v / b * 100)) for v in seq], 'nota': nota}
    if fill: print('rellenados', s, fill)
json.dump({'at': json.load(open('data/hist_mensual.json'))['at'], 'hasta': max(v['m'][-1][0] for v in H.values()), 's': OUT}, open('data/hist_series.json', 'w'), separators=(',', ':'))
import os; print(os.path.getsize('data/hist_series.json')); print({k: (v['d0'], len(v['p'])) for k, v in OUT.items()})
