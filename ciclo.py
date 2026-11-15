# Ciclo de vida y rentabilidad del negocio a partir de los resultados anuales (Yahoo).
# Fases (esquema de Brian Feroldi; las reglas numéricas son propias, una interpretación):
#   1 Arranque: pierde dinero y crece menos de un 20 %.
#   2 Hipercrecimiento: crece un 20 % o más y aún pierde dinero o gana muy poco (margen operativo < 5 %).
#   3 Apalancamiento operativo: gana dinero, crece un 10 % o más y su margen operativo sube al menos 1 punto.
#   4 Devolución de capital (madura): gana dinero sin cumplir lo anterior.
#   5 Declive: las ventas caen más de un 3 % y el margen operativo también baja.
import datetime
LAG = 90  # días que se tarda en publicar las cuentas anuales tras el cierre del ejercicio (supuesto)
FASES = {1: 'Arranque', 2: 'Hipercrecimiento', 3: 'Apalancamiento operativo', 4: 'Devolución de capital', 5: 'Declive'}
def _s(o, k):
    return {d: v for d, v in (o.get('annual' + k) or []) if v is not None}
def metricas(o, hasta=None):
    """o = resultados de una empresa (fundhist); hasta = fecha ISO: solo ejercicios publicados antes (cierre + 90 días)."""
    R = _s(o, 'TotalRevenue'); OP = _s(o, 'OperatingIncome') or _s(o, 'EBIT'); E = _s(o, 'EBIT')
    ys = sorted(d for d in R if d in OP or d in E)
    if hasta: ys = [d for d in ys if (datetime.date.fromisoformat(d) + datetime.timedelta(days=LAG)).isoformat() <= hasta]
    if len(ys) < 2: return None
    d0, d1 = ys[-2], ys[-1]
    op = lambda d: OP.get(d, E.get(d))
    r0, r1, o0, o1 = R[d0], R[d1], op(d0), op(d1)
    if not r0 or not r1 or r0 <= 0 or r1 <= 0 or o0 is None or o1 is None: return None
    g = r1 / r0 - 1; m0, m1 = o0 / r0, o1 / r1
    GP = _s(o, 'GrossProfit'); gm1 = GP[d1] / r1 if d1 in GP else None; gm0 = GP[d0] / r0 if d0 in GP else None
    T, P, IC = _s(o, 'TaxProvision'), _s(o, 'PretaxIncome'), _s(o, 'InvestedCapital')
    tr = T[d1] / P[d1] if d1 in T and P.get(d1) and P[d1] > 0 else 0.21
    tr = min(max(tr, 0.0), 0.35)
    ic = [IC[d] for d in (d0, d1) if IC.get(d) and IC[d] > 0]
    roic = o1 * (1 - tr) / (sum(ic) / len(ic)) if ic else None
    dol = (o1 / o0 - 1) / g if o0 > 0 and o1 > 0 and abs(g) >= 0.02 else None
    DV, RP, NI = _s(o, 'CashDividendsPaid'), _s(o, 'RepurchaseOfCapitalStock'), _s(o, 'NetIncome')
    dev = abs(DV.get(d1) or 0) + abs(RP.get(d1) or 0)
    if g < -0.03 and m1 < m0: f = 5
    elif o1 < 0 and g < 0.20: f = 1
    elif g >= 0.20 and (o1 < 0 or m1 < 0.05): f = 2
    elif o1 > 0 and g >= 0.10 and m1 - m0 >= 0.01: f = 3
    elif o1 > 0: f = 4
    else: f = 1
    rd = lambda x, n=4: None if x is None else round(x, n)
    return {'fase': f, 'ej': d1, 'ej0': d0, 'crec': rd(g), 'mop': rd(m1), 'mop0': rd(m0), 'dmop': rd(m1 - m0), 'mb': rd(gm1), 'mb0': rd(gm0),
            'roic': rd(roic), 'dol': rd(dol, 2), 'imp': rd(tr, 3), 'devol': rd(dev / NI[d1], 3) if NI.get(d1) and NI[d1] > 0 else None,
            'ventas': [[d, R[d]] for d in ys[-4:]], 'mops': [[d, rd(op(d) / R[d])] for d in ys[-4:] if op(d) is not None and R[d]]}
