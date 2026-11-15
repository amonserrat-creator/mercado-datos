# Descarga diaria de cotizaciones (S&P 500 + IBEX 35) para «Nuestras finanzas».
# Se ejecuta en los servidores de GitHub (Actions). Escribe data/upd.json con el mismo
# formato que nube.py espera (mkt_upd_yh.json): {"H":{t:[{d,o,h,l,c,v}]},"F":{t:{...}},"E":{t:error}}
# y data/estado.json con el resumen. Solo datos públicos de mercado.
import json, os, sys, time, datetime, urllib.request, concurrent.futures as cf
import ranking, ciclo, fundhist
FRI = '--viernes' in sys.argv or datetime.datetime.utcnow().weekday() == 4
T = json.load(open('tickers.json'))
EXTRA = ['EURUSD=X']  # cambio euro/dólar para el simulacro (no entra en el ranking)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept': 'application/json,text/plain,*/*'}
def get(url, h=UA):
    err = None
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25) as r: return json.loads(r.read())
        except Exception as ex:
            err = ex; time.sleep(2 * (k + 1))
    raise err
ysym = lambda t: t if t.endswith('.MC') else t.replace('.', '-')
p2 = int(time.time()) + 86400; p1 = p2 - 86400 * 25
P10 = int(time.mktime((datetime.date.today() - datetime.timedelta(days=3700)).timetuple()))  # ~10 años y pico, para el ranking de los viernes
RANK = FRI or '--ranking' in sys.argv
DESDE_BH = '2019-11-11'  # lunes de la semana 2019-W46, la primera de la prueba
TY = ['TotalRevenue', 'CostOfRevenue', 'GrossProfit', 'ResearchAndDevelopment', 'SellingGeneralAndAdministration', 'OperatingIncome', 'PretaxIncome', 'TaxProvision', 'NetIncome', 'InterestExpense', 'EBIT']
MAP = {'rev': 'TotalRevenue', 'cogs': 'CostOfRevenue', 'gp': 'GrossProfit', 'rd': 'ResearchAndDevelopment', 'sga': 'SellingGeneralAndAdministration', 'op': 'OperatingIncome', 'ebit': 'EBIT', 'int': 'InterestExpense', 'pt': 'PretaxIncome', 'tax': 'TaxProvision', 'ni': 'NetIncome'}
def conv(o, pre):
    per = sorted({x[0] for k, v in o.items() if k.startswith(pre) for x in v})[-4:]
    if not per: return None
    r = {'per': ['%d/%d/%s' % (int(p[5:7]), int(p[8:10]), p[:4]) for p in per]}
    for a, b in MAP.items():
        m = {x[0]: x[1] for x in o.get(pre + b, [])}; r[a] = [m[p] / 1000 if m.get(p) is not None else None for p in per]
    return r
def nasdaq(t):  # respaldo solo para EE. UU. si Yahoo falla
    d2 = datetime.date.today(); d1 = d2 - datetime.timedelta(days=25)
    j = get('https://api.nasdaq.com/api/quote/%s/historical?assetclass=stocks&fromdate=%s&todate=%s&limit=40' % (t.replace('.', '%25sl%25'), d1, d2),
            {**UA, 'Origin': 'https://www.nasdaq.com', 'Referer': 'https://www.nasdaq.com/'})
    f = lambda s: float(str(s).replace('$', '').replace(',', '')) if s not in (None, '', 'N/A') else None
    out = []
    for r in reversed(j['data']['tradesTable']['rows']):
        m, dd, y = r['date'].split('/')
        out.append({'d': '%s-%s-%s' % (y, m, dd), 'o': f(r['open']), 'h': f(r['high']), 'l': f(r['low']), 'c': f(r['close']), 'v': int(f(r['volume']) or 0)})
    return out
def one(t):
    out = {'t': t, 'src': 'yahoo'}
    try:
        j = get('https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=%d&period2=%d&interval=1d' % (ysym(t), P10 if RANK else p1, p2))
        res = j['chart']['result'][0]; q = res['indicators']['quote'][0]; off = res['meta'].get('gmtoffset', 0)
        L = [{'d': datetime.datetime.utcfromtimestamp(ts + off).strftime('%Y-%m-%d'), 'o': q['open'][i], 'h': q['high'][i], 'l': q['low'][i], 'c': q['close'][i], 'v': q['volume'][i]} for i, ts in enumerate(res.get('timestamp') or []) if q['close'][i] is not None]
        if RANK:
            i0 = next((i for i, x in enumerate(L) if x['d'] >= DESDE_BH), None)
            if i0 is not None and L[0]['d'] < DESDE_BH: out['BH'] = (L[i0]['o'], L[-1]['c'])
        if RANK: out['TR'] = ranking.tendencias({'d': [x['d'] for x in L], 'c': [x['c'] for x in L]})
        if RANK and t not in EXTRA: out['DL'] = {'d': [x['d'] for x in L], 'o': [x['o'] for x in L], 'c': [x['c'] for x in L]}
        if RANK: out['W'] = ranking.semanas({'d': [x['d'] for x in L], 'o': [x['o'] for x in L], 'c': [x['c'] for x in L]})
        lim = datetime.datetime.utcfromtimestamp(p1).strftime('%Y-%m-%d'); out['H'] = [x for x in L if x['d'] >= lim]
    except Exception as e:
        if t.endswith('.MC'): raise
        out['H'] = nasdaq(t); out['src'] = 'nasdaq'
    if FRI and t not in EXTRA:
        try:
            ty = ','.join(['quarterly' + x for x in TY] + ['annual' + x for x in TY] + ['trailingMarketCap', 'trailingPeRatio'])
            f = get('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/%s?symbol=%s&type=%s&period1=%d&period2=%d' % (ysym(t), ysym(t), ty, int(time.mktime(datetime.date(2021, 1, 1).timetuple())), p2))
            o = {}
            for r in f['timeseries']['result']:
                k = r['meta']['type'][0]; a = [x for x in (r.get(k) or []) if x]
                if a: o[k] = [[x['asOfDate'], (x.get('reportedValue') or {}).get('raw')] for x in a]
            lastv = lambda k: o[k][-1][1] if o.get(k) else None
            out['F'] = {'q': conv(o, 'quarterly'), 'y': conv(o, 'annual'), 'mc': lastv('trailingMarketCap'), 'pe': lastv('trailingPeRatio'), 'src': 'Yahoo Finance', 'unit': 'miles de EUR' if t.endswith('.MC') else 'miles de USD'}
            try:
                fh = fundhist.one(t); out['FH'] = fh; cv = ciclo.metricas(fh)
                if cv: out['F']['cv'] = cv
            except Exception: pass
        except Exception: pass
    return out
UP = {'H': {}, 'F': {}, 'E': {}}; SRC = {}; WK = {}; BHD = {}; TRD = {}; FHD = {}; DLD = {}
with cf.ThreadPoolExecutor(6) as ex:
    for fut, t in [(ex.submit(one, t), t) for t in T + EXTRA]:
        try:
            o = fut.result()
            if o.get('H'): UP['H'][t] = o['H']; SRC[o['src']] = SRC.get(o['src'], 0) + 1
            else: UP['E'][t] = 'sin velas'
            if o.get('F') and (o['F'].get('q') or o['F'].get('y')): UP['F'][t] = o['F']
            if o.get('W') and t not in EXTRA: WK[t] = o['W']
            if o.get('TR'): TRD[t] = o['TR']
            if o.get('BH') and t not in EXTRA: BHD[t] = o['BH']
            if o.get('FH'): FHD[t] = o['FH']
            if o.get('DL'): DLD[t] = o['DL']
        except Exception as e: UP['E'][t] = repr(e)[:120]
ult = {}
for t, L in UP['H'].items(): ult[L[-1]['d']] = ult.get(L[-1]['d'], 0) + 1
os.makedirs('data', exist_ok=True)
json.dump(UP, open('data/upd.json', 'w'), separators=(',', ':'))
if RANK and len(WK) >= 0.9 * len(T):
    json.dump({'generado': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'hasta': max(max(r) for r in WK.values() if r), 'n': len(WK),
               'rk': ranking.ranking(WK), 'bt': dict(ranking.prueba(WK), mantener=ranking.mantener(BHD, DESDE_BH), **ranking.prueba_criterio(WK, TRD))}, open('data/rank.json', 'w'), separators=(',', ':'))
    json.dump(WK, open('data/semanas.json', 'w'), separators=(',', ':'))  # rendimientos lunes→viernes de cada semana, para revisar
if len(FHD) >= 0.9 * len(T): json.dump(FHD, open('data/fundhist.json', 'w'), separators=(',', ':'))
if RANK and len(DLD) >= 0.9 * len(T):
    try:
        uvse = max(D['d'][-1] for D in DLD.values()); dd = datetime.date.fromisoformat(uvse)
        sig = '%d-W%02d' % (dd + datetime.timedelta(days=7 - dd.weekday())).isocalendar()[:2]
        import vse; V = vse.elegir(DLD, sig); V['generado'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'); V['datos'] = uvse
        json.dump(V, open('data/vse.json', 'w'), ensure_ascii=False, indent=1); print('VSE', sig, [x['t'] for x in V['top']])
    except Exception as e: print('VSE error', repr(e)[:200])
est = {'ranking': len(WK) if RANK else None, 'generado': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'acciones': len(T), 'con_velas': len(UP['H']), 'con_resultados': len(UP['F']), 'errores': len(UP['E']), 'fuentes': SRC,
       'ultima_sesion': sorted(ult.items())[-3:], 'ejemplos_error': list(UP['E'].items())[:5], 'viernes': FRI}
json.dump(est, open('data/estado.json', 'w'), indent=1)
print(json.dumps(est, indent=1))
if len(UP['H']) < 0.9 * len(T): sys.exit(1)
