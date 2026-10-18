#!/usr/bin/env python3
"""Prueba del servicio público Transitous (MOTIS 2): ¿responde?, ¿permite llamadas desde un navegador (CORS)?, ¿qué devuelve hoy y para setiembre de 2027?
Pocas consultas, una por segundo, con identificación en User-Agent. Guarda un resumen."""
import urllib.request, urllib.parse, json, time, os
UA = "MoppiProbe/1.0 (personal trip app; https://github.com/vir3001/Moppi)"
BASE = "https://api.transitous.org/api"
CASES = [
 ("Roma: Termini -> Colosseo", "41.9009,12.5016", "41.8902,12.4922"),
 ("Roma: Trastevere -> Termini", "41.8886,12.4698", "41.9009,12.5016"),
 ("Rapallo: estación -> Portofino", "44.3491,9.2321", "44.3036,9.2092"),
 ("Génova: Brignole -> Principe", "44.4073,8.9489", "44.4172,8.9211"),
 ("Turín: Porta Nuova -> Piazza Castello", "45.0620,7.6785", "45.0710,7.6859"),
 ("Venezia: Ferrovia -> San Zaccaria", "45.4410,12.3213", "45.4336,12.3437"),
 ("Milán: Centrale -> Duomo", "45.4861,9.2043", "45.4642,9.1900"),
 ("Sevilla: Santa Justa -> Catedral", "37.3920,-5.9753", "37.3860,-5.9926"),
 ("Granada: estación -> Alhambra", "37.1850,-3.6090", "37.1760,-3.5881"),
 ("Entre ciudades: Milán Centrale -> Tirano", "45.4861,9.2043", "46.2157,10.1713"),
 ("Entre ciudades: Milán Centrale -> Varenna-Esino", "45.4861,9.2043", "46.0105,9.2845"),
 ("Entre ciudades: Sevilla Santa Justa -> Córdoba", "37.3920,-5.9753", "37.8918,-4.7897"),
 ("Entre ciudades: Sevilla Santa Justa -> Cádiz", "37.3920,-5.9753", "36.5290,-6.2910"),
 ("Entre ciudades: Roma Termini -> Rapallo", "41.9009,12.5016", "44.3491,9.2321"),
 ("Entre ciudades: Génova Principe -> Turín Porta Nuova", "44.4172,8.9211", "45.0620,7.6785"),
]
DATES = [("2026-10-20T10:00:00+02:00", "hoy (martes 20/10/2026)"), ("2027-09-14T10:00:00+02:00", "setiembre 2027 (martes 14/09/2027)")]
out = {"cors": {}, "version": None, "cases": []}
def get(path, params=None, origin=True):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    h = {"User-Agent": UA, "Accept": "application/json"}
    if origin: h["Origin"] = "https://vir3001.github.io"; h["Referer"] = "https://vir3001.github.io/Moppi/"
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, str(e).encode()
# versión disponible
ver = None
for v in ("v6", "v5", "v4"):
    st, hd, body = get(f"/{v}/plan", {"fromPlace": CASES[0][1], "toPlace": CASES[0][2], "time": DATES[0][0], "numItineraries": 1})
    print("probe version", v, st, flush=True)
    if st == 200: ver = v; out["cors"] = {k: hd.get(k) for k in hd if k.lower().startswith("access-control") or k.lower() in ("server", "content-type", "x-ratelimit-limit")}; break
out["version"] = ver
if ver:
    # preflight
    req = urllib.request.Request(f"{BASE}/{ver}/plan", method="OPTIONS", headers={"User-Agent": UA, "Origin": "https://vir3001.github.io", "Access-Control-Request-Method": "GET"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: out["cors"]["preflight_status"] = r.status; out["cors"]["preflight_headers"] = {k: v for k, v in r.headers.items() if k.lower().startswith("access-control")}
    except urllib.error.HTTPError as e: out["cors"]["preflight_status"] = e.code
    except Exception as e: out["cors"]["preflight_error"] = str(e)
    for name, a, b in CASES:
        for t, tl in DATES:
            time.sleep(1)
            st, hd, body = get(f"/{ver}/plan", {"fromPlace": a, "toPlace": b, "time": t, "numItineraries": 3})
            rec = {"caso": name, "fecha": tl, "http": st}
            try:
                j = json.loads(body)
                its = j.get("itineraries", [])
                rec["itinerarios"] = len(its); rec["directos"] = len(j.get("direct", []))
                def legs(it): return [{"modo": l.get("mode"), "linea": l.get("routeShortName") or l.get("displayName"), "agencia": l.get("agencyName"), "de": (l.get("from") or {}).get("name"), "a": (l.get("to") or {}).get("name"), "sale": l.get("startTime"), "llega": l.get("endTime")} for l in it.get("legs", [])]
                rec["primero"] = {"duracion_s": its[0].get("duration"), "inicio": its[0].get("startTime"), "fin": its[0].get("endTime"), "transbordos": its[0].get("transfers"), "tramos": legs(its[0])} if its else None
                rec["mensajes"] = {k: j[k] for k in j if k in ("debugOutput",)} or None
                if not its and j.get("direct"): rec["directo_primero"] = {"duracion_s": j["direct"][0].get("duration"), "modos": [l.get("mode") for l in j["direct"][0].get("legs", [])]}
            except Exception:
                rec["cuerpo"] = body[:300].decode("utf-8", "replace")
            out["cases"].append(rec)
            print(name, "|", tl, "|", st, "|", rec.get("itinerarios"), flush=True)
os.makedirs("probe/out", exist_ok=True)
json.dump(out, open("probe/out/transitous.json", "w"), ensure_ascii=False, indent=1)
