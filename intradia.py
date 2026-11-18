# Precios de la última hora (durante la sesión de EE. UU.) para «Nuestras finanzas»: cartera, simulacros y cambio.
# Escribe data/intra.json = {at (UTC), fx: EUR/USD, px: {ticker: [precio, cierre anterior, hora UTC del precio]}}
import json, time, datetime, urllib.request, concurrent.futures as cf
PORT = {'NVDA': 'NVDA', 'INTC': 'INTC', 'KLAC': 'KLAC', 'AMD': 'AMD', 'AVGO': 'AVGO', 'MSFT': 'MSFT', 'AMZN': 'AMZN', 'MRVL': 'MRVL', 'PANW': 'PANW',
        'CRM': 'CRM', 'TSM': 'TSM', 'LRCX': 'LRCX', 'IBM': 'IBM', 'TSLA': 'TSLA', 'KD': 'KD', 'LLY': 'LLY', 'IBRX': 'IBRX', 'CELH': 'CELH', 'CGC': 'CGC',
        'PLUG': 'PLUG', 'IONQ': 'IONQ', 'RGTI': 'RGTI', 'QBTS': 'QBTS', 'RCAT': 'RCAT', 'ACHR': 'ACHR', 'QSI': 'QSI', 'URTH': 'URTH', 'IEMG': 'IEMG',
        'QQQ': 'QQQ', 'GRID': 'GRID', 'DTCR': 'DTCR', 'REMX': 'REMX', 'URA': 'URA', 'IXJ': 'IXJ', 'KXI': 'KXI', 'GLD': 'GLD', 'SLV': 'SLV', 'CPER': 'CPER',
        'SPY': 'SPY', 'BTC': 'BTC-USD', 'UCORE': 'UURAF'}
T = json.load(open('tickers.json'))
SYM = dict(PORT); SYM.update({t: (t if t.endswith('.MC') else t.replace('.', '-')) for t in T}); SYM['EURUSD'] = 'EURUSD=X'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept': 'application/json'}
def one(k):
    for i in range(3):
        try:
            u = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1d&interval=5m' % SYM[k]
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as r: m = json.loads(r.read())['chart']['result'][0]['meta']
            p = m.get('regularMarketPrice'); pc = m.get('chartPreviousClose') or m.get('previousClose'); ts = m.get('regularMarketTime')
            if p: return k, [round(p, 6), round(pc, 6) if pc else None, datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ') if ts else None]
        except Exception: time.sleep(1.5 * (i + 1))
    return k, None
PX = {}
with cf.ThreadPoolExecutor(8) as ex:
    for k, v in ex.map(one, list(SYM)):
        if v: PX[k] = v
FXV = PX.pop('EURUSD', [None, None, None]); fx = FXV[0]
out = {'at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'fx': fx, 'fxprev': FXV[1], 'fxt': FXV[2], 'n': len(PX), 'faltan': sorted(set(SYM) - set(PX) - {'EURUSD'})[:20], 'px': PX}
json.dump(out, open('data/intra.json', 'w'), separators=(',', ':'))
print(out['at'], 'precios', len(PX), 'de', len(SYM) - 1, 'cambio', fx, 'faltan', out['faltan'][:10])
