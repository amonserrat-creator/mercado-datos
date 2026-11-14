# Ranking «lunes a la apertura → viernes al cierre» con 52 semanas, 5 años y 10 años, y la media de las tres,
# más una prueba histórica sin mirar al futuro (cada semana se elige con los datos anteriores a esa semana).
import datetime, bisect, statistics as st
COST = 0.004                      # Trade Republic con 1.000 €: 1 € + 1 € y ≈0,1 % de horquilla en cada operación
WIN = {'s52': (52, 40), 'a5': (260, 200), 'a10': (520, 400)}     # ventana en semanas y mínimo de semanas para entrar
WIN_BT = {'s52': (52, 40), 'a5': (260, 156), 'a10': (520, 156)}  # en la prueba histórica (en 2019 aún no hay 5-10 años)
def _wk(d): y, w, _ = datetime.date.fromisoformat(d).isocalendar(); return '%d-W%02d' % (y, w)
def semanas(D):
    """D = {'d':[fechas],'o':[...],'c':[...]} -> {semana: apertura del primer día / cierre del último - 1}.
    Igual que la lista semanal (semana.py): cuentan todas las semanas, también las cortas por festivo;
    solo se descarta la última si aún no ha terminado (no acaba en viernes)."""
    g = {}
    for i, d in enumerate(D['d']): g.setdefault(_wk(d), []).append(i)
    r = {}; ult = max(g) if g else None
    for k, I in g.items():
        if k == ult and datetime.date.fromisoformat(D['d'][I[-1]]).weekday() != 4: continue
        o, c = D['o'][I[0]], D['c'][I[-1]]
        if o and c: r[k] = c / o - 1
    return r
class _T:
    def __init__(s, r):
        s.k = sorted(r); s.v = [r[k] for k in s.k]; s.cu = [0]; s.cs = [0.0]
        for x in s.v: s.cu.append(s.cu[-1] + (x > 0)); s.cs.append(s.cs[-1] + x)
    def stat(s, p, w, mn):  # semanas [p-w, p)
        a = max(0, p - w); n = p - a
        return None if n < mn else ((s.cu[p] - s.cu[a]) / n, (s.cs[p] - s.cs[a]) / n, n)
def score(T, p, wins):
    o = {h: T.stat(p, w, mn) for h, (w, mn) in wins.items()}
    if all(o.values()): o['med'] = (st.mean(o[h][0] for h in wins), st.mean(o[h][1] for h in wins), None)
    else: o['med'] = None
    return o
def ranking(W):
    """W = {ticker: {semana: rendimiento}} -> {ticker: {s52:[up,avg,n], a5:..., a10:..., med:[up,avg]}} con las últimas semanas."""
    out = {}
    for t, r in W.items():
        if not r: continue
        T = _T(r); o = score(T, len(T.k), WIN)
        out[t] = {h: ([round(v[0], 4), round(v[1], 5)] + ([v[2]] if v[2] is not None else [])) if v else None for h, v in o.items()}
        # año en curso frente a los años anteriores (dentro de los últimos 10 años)
        y = T.k[-1][:4]; ks = T.k[-520:]; vs = T.v[-520:]
        pre = [v for k, v in zip(ks, vs) if k[:4] < y]; ytd = [v for k, v in zip(ks, vs) if k[:4] == y]
        f = lambda L, mn: [round(sum(x > 0 for x in L) / len(L), 4), round(st.mean(L), 5), len(L)] if len(L) >= mn else None
        out[t]['pre'] = f(pre, 200); out[t]['ytd'] = f(ytd, 20); out[t]['y'] = y
    return out
def prueba(W, desde='2019-W46'):
    """Cada semana desde `desde`: la 1.ª de cada ranking. Devuelve el resultado con costes."""
    TT = {t: _T(r) for t, r in W.items() if r}
    allk = sorted({k for r in W.values() for k in r if k >= desde})
    res = {h: [] for h in list(WIN_BT) + ['med']}; base = []; det = {h: [] for h in res}
    for k in allk:
        best = {h: None for h in res}
        for t, T in TT.items():
            p = bisect.bisect_left(T.k, k)
            if p >= len(T.k) or T.k[p] != k: continue  # esa semana no cotizó completa
            o = score(T, p, WIN_BT)
            for h in res:
                v = o.get(h)
                if v and (best[h] is None or (v[0], v[1]) > best[h][0]): best[h] = ((v[0], v[1]), T.v[p], t)
        for h in res:
            if best[h]: res[h].append(best[h][1] - COST); det[h].append((k, best[h][2], round(best[h][1], 4)))
        base.append(st.mean([r[k] for r in W.values() if k in r]))
    def summ(L):
        cap = 1000.0
        for x in L: cap *= 1 + x
        return {'n': len(L), 'final': round(cap), 'up': round(sum(x > 0 for x in L) / len(L), 3), 'avg': round(st.mean(L), 5), 'worst': round(min(L), 4)}
    o = {h: dict(summ(L), peores=sorted(det[h], key=lambda x: x[2])[:3]) for h, L in res.items() if L}; o['todas'] = summ(base); o['todas_c'] = summ([x - COST for x in base]); o['desde'] = allk[0]; o['hasta'] = allk[-1]
    return o

def mantener(BH, desde_dia):
    """BH = {ticker: (apertura del primer día >= desde_dia, último cierre)}: 1.000 € repartidos a partes iguales y sin tocar."""
    r = [c / o for o, c in BH.values() if o and c]
    return {'n': len(r), 'final': round(1000 * sum(r) / len(r)), 'desde': desde_dia} if r else None
