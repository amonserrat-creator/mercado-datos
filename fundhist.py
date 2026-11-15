# Resultados y balance históricos de Yahoo (anual y trimestral) para el ciclo de vida y la rentabilidad del negocio.
# Escribe data/fundhist.json: {t: {tipo: [[fecha_cierre, valor], ...]}}
import json, time, datetime, urllib.request, concurrent.futures as cf
T = json.load(open('tickers.json'))
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept': 'application/json'}
TY = ['TotalRevenue', 'GrossProfit', 'OperatingIncome', 'EBIT', 'PretaxIncome', 'TaxProvision', 'NetIncome', 'TotalAssets', 'InvestedCapital',
      'StockholdersEquity', 'TotalDebt', 'CashAndCashEquivalents', 'OperatingCashFlow', 'FreeCashFlow', 'CashDividendsPaid', 'RepurchaseOfCapitalStock']
types = ','.join(['annual' + x for x in TY] + ['quarterly' + x for x in TY])
ysym = lambda t: t if t.endswith('.MC') else t.replace('.', '-')
p1 = int(time.mktime(datetime.date(2015, 1, 1).timetuple())); p2 = int(time.time()) + 86400
def get(url):
    err = None
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r: return json.loads(r.read())
        except Exception as e: err = e; time.sleep(2 * (k + 1))
    raise err
def one(t):
    f = get('https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/%s?symbol=%s&type=%s&period1=%d&period2=%d' % (ysym(t), ysym(t), types, p1, p2))
    o = {}
    for r in f['timeseries']['result']:
        k = r['meta']['type'][0]; a = [x for x in (r.get(k) or []) if x]
        if a: o[k] = [[x['asOfDate'], (x.get('reportedValue') or {}).get('raw')] for x in a]
    return o
if __name__ == '__main__':
    OUT = {}; E = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for fut, t in [(ex.submit(one, t), t) for t in T]:
            try: OUT[t] = fut.result()
            except Exception as e: E[t] = repr(e)[:100]
    json.dump(OUT, open('data/fundhist.json', 'w'), separators=(',', ':'))
    n_a = [len(o.get('annualTotalRevenue', [])) for o in OUT.values()]
    print('acciones', len(OUT), 'errores', len(E), 'años de ventas (min/mediana/max):', min(n_a), sorted(n_a)[len(n_a) // 2], max(n_a), list(E.items())[:3])
