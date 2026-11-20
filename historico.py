# Histórico mensual (máximo disponible) de los productos de «Nuestras finanzas» y de índices de referencia, para comparar formas de invertir.
# Escribe data/hist_mensual.json = {at, px: {clave: {sym, cur, first, m: [[AAAA-MM, cierre ajustado], ...]}}, faltan}
import json, time, datetime, urllib.request, urllib.parse
import re, ast
PORT = ast.literal_eval(re.search(r'PORT = (\{.*?\})\n', open('intradia.py').read(), re.S).group(1))  # misma lista que la cartera
EXTRA = {'GSPC': '^GSPC', 'SP500TR': '^SP500TR', 'MSCIW': '^990100-USD-STRD', 'NDX': '^NDX', 'ORO': 'GC=F', 'PLATA': 'SI=F', 'COBRE': 'HG=F', 'EURUSD': 'EURUSD=X'}
SYM = dict(PORT); SYM.update(EXTRA)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept': 'application/json'}
def one(sym):
    for i in range(3):
        try:
            u = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=0&period2=%d&interval=1mo&events=div%%2Csplit&includeAdjustedClose=true' % (urllib.parse.quote(sym), int(time.time()))
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r: R = json.loads(r.read())['chart']['result'][0]
            ts = R['timestamp']; q = R['indicators']; ac = (q.get('adjclose') or [{}])[0].get('adjclose') or q['quote'][0]['close']
            m = {}
            for t, v in zip(ts, ac):
                if v: m[datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m')] = round(v, 6)
            return {'sym': sym, 'cur': R['meta'].get('currency'), 'm': sorted(m.items())}
        except Exception as e: err = str(e); time.sleep(2 * (i + 1))
    return {'sym': sym, 'error': err}
PX, FAL = {}, []
for k, s in SYM.items():
    x = one(s)
    if x.get('m'): x['first'] = x['m'][0][0]; PX[k] = x
    else: FAL.append([k, s, x.get('error')])
    time.sleep(0.4)
json.dump({'at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'px': PX, 'faltan': FAL}, open('data/hist_mensual.json', 'w'), separators=(',', ':'))
print(len(PX), 'series;', 'faltan', FAL); print({k: (v['first'], len(v['m'])) for k, v in PX.items()})
