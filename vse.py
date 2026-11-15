# Modelo «ventaja semanal esperada» (VSE). Cada viernes, con 10 años de velas diarias:
# 7 señales por acción, pasadas a rangos (−0,5…+0,5); cada semana pasada, regresión de la rentabilidad lunes→viernes
# (respecto a la media) sobre esos rangos (Fama–MacBeth); pesos = media de las últimas 156 semanas × 0,5 (prudencia);
# previsión = media semanal de esas semanas + rangos · pesos. Se elige la acción con mayor previsión (opera todas las semanas).
import datetime, statistics as st
import numpy as np
FEAT = ['m12', 'm6', 'm1', 'w1', 'vol', 'd52', 's52']
NOMBRE = {'m12': 'Subida 12 meses (sin el último)', 'm6': 'Subida 6 meses (sin el último)', 'm1': 'Subida del último mes', 'w1': 'Subida de la última semana',
          'vol': 'Volatilidad 3 meses', 'd52': 'Distancia al máximo de 52 semanas', 's52': '% de semanas lunes→viernes en positivo (52)'}
WIN, SHRINK = 156, 0.5
_wk = lambda d: '%d-W%02d' % datetime.date.fromisoformat(d).isocalendar()[:2]
def _feats(D, g, k, ks_sorted):
    """D = {'d','o','c'}; g = {semana: (i0, i1)}; señales al cierre de la semana anterior a k; r = rentabilidad de la semana k (o None si aún no ha pasado)."""
    if k in g: i0 = g[k][0]; e = i0 - 1
    else: e = len(D['c']) - 1; i0 = None
    c = D['c']
    if e < 260 or not all(c[j] for j in (e, e - 5, e - 21, e - 126, e - 252)): return None
    rets = [c[j] / c[j - 1] - 1 for j in range(e - 62, e + 1) if c[j] and c[j - 1]]
    hi = max(x for x in c[e - 251:e + 1] if x)
    prev = [x for x in ks_sorted if x < k][-52:]
    wr = [c[g[x][1]] / D['o'][g[x][0]] - 1 for x in prev if D['o'][g[x][0]] and c[g[x][1]]]
    if len(rets) < 40 or len(wr) < 40: return None
    r = (c[g[k][1]] / D['o'][i0] - 1) if i0 is not None and D['o'][i0] and c[g[k][1]] else None
    return [c[e - 21] / c[e - 252] - 1, c[e - 21] / c[e - 126] - 1, c[e] / c[e - 21] - 1, c[e] / c[e - 5] - 1, st.pstdev(rets), c[e] / hi - 1, sum(x > 0 for x in wr) / len(wr)], r
def _ranks(F):
    F = np.array(F); return F.argsort(0).argsort(0) / (len(F) - 1) - 0.5
def elegir(DL, semana_sig):
    """DL = {ticker: {'d','o','c'}} (10 años). semana_sig = semana ISO que se va a operar. Devuelve elección, previsión y pesos."""
    G = {}
    for t, D in DL.items():
        g = {}
        for i, d in enumerate(D['d']): g.setdefault(_wk(d), []).append(i)
        G[t] = ({k: (I[0], I[-1]) for k, I in g.items()}, sorted(g))
    weeks = sorted({k for g, ks in G.values() for k in ks})
    hist = [k for k in weeks if k < semana_sig][-(WIN + 1):]
    # semanas completas (la última solo si acaba en viernes)
    B, MU = [], []
    for k in hist:
        rows = []
        for t, (g, ks) in G.items():
            if k not in g or (k == weeks[-1] and datetime.date.fromisoformat(DL[t]['d'][g[k][1]]).weekday() != 4): continue
            x = _feats(DL[t], g, k, ks)
            if x and x[1] is not None: rows.append(x)
        if len(rows) < 100: continue
        R = _ranks([f for f, r in rows]); y = np.array([r for f, r in rows])
        b = np.linalg.lstsq(np.c_[np.ones(len(rows)), R], y - y.mean(), rcond=None)[0][1:]; B.append(b); MU.append(y.mean())
    B, MU = B[-WIN:], MU[-WIN:]
    w = np.mean(B, 0) * SHRINK; mu = float(np.mean(MU))
    rows = []
    for t, (g, ks) in G.items():
        if DL[t]['d'][-1] != max(D['d'][-1] for D in DL.values()): continue
        x = _feats(DL[t], g, semana_sig, ks)
        if x: rows.append((t, x[0]))
    R = _ranks([f for t, f in rows]); pred = mu + R @ w; o = np.argsort(-pred)
    top = [{'t': rows[i][0], 'prev': round(float(pred[i]), 5), 'senales': {n: round(v, 4) for n, v in zip(FEAT, rows[i][1])}} for i in o[:5]]
    return {'semana': semana_sig, 'semanas_aprendidas': len(B), 'media_semanal': round(mu, 5), 'pesos': {n: round(float(v), 5) for n, v in zip(FEAT, w)},
            'nombres': NOMBRE, 'top': top, 'coste_aprox': 0.004}
