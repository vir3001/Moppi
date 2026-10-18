#!/usr/bin/env python3
"""Sonda de feeds GTFS oficiales: descarga cada archivo, mide vigencia y tamaño y guarda un resumen. No guarda los zip."""
import urllib.request, hashlib, zipfile, io, json, csv, os, sys, time
FEEDS = [
 ("roma_romamobilita", "https://romamobilita.it/sites/default/files/rome_static_gtfs.zip"),
 ("torino_gtt", "https://www.gtt.to.it/open_data/gtt_gtfs.zip"),
 ("genova_amt", "https://www.amt.genova.it/amt/GTFS/GTFS_AMT_GENOVA.zip"),
 ("milano_atm", "https://dati.comune.milano.it/gtfs.zip"),
 ("trenord", "https://www.dati.lombardia.it/download/3z4k-mxz9/application%2Fzip"),
 ("actv_navigazione", "http://actv.avmspa.it/sites/default/files/attachments/opendata/navigazione/actv_nav.zip"),
 ("sevilla_tussam_nap1567", "https://nap.transportes.gob.es/api/Fichero/download/1567"),
 ("sevilla_metro_nap1583", "https://nap.transportes.gob.es/api/Fichero/download/1583"),
 ("granada_metro_nap1568", "https://nap.transportes.gob.es/api/Fichero/download/1568"),
 ("cordoba_aucorsa_nap1573", "https://nap.transportes.gob.es/api/Fichero/download/1573"),
 ("andalucia_metropolitano_nap1562", "https://nap.transportes.gob.es/api/Fichero/download/1562"),
 ("renfe_av_ld_md", "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"),
 ("renfe_cercanias", "https://ssl.renfe.com/ftransit/Fichero_CER_FOMENTO/fomento_transit.zip"),
]
UA = "Mozilla/5.0 (compatible; MoppiProbe/1.0; +https://github.com/vir3001/Moppi)"
os.makedirs("probe/out", exist_ok=True)
def rows(z, name):
    if name not in z.namelist(): return None
    with z.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")))
def count(z, name):
    if name not in z.namelist(): return 0
    with z.open(name) as f: return sum(1 for _ in f) - 1
out = {}
for key, url in FEEDS:
    info = {"url": url}
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=120) as r:
            info["status"] = r.status; info["final_url"] = r.geturl(); info["content_type"] = r.headers.get("Content-Type"); info["last_modified"] = r.headers.get("Last-Modified")
            data = r.read(400 * 1024 * 1024)
        info["bytes"] = len(data); info["sha256"] = hashlib.sha256(data).hexdigest()
        try:
            z = zipfile.ZipFile(io.BytesIO(data)); info["files"] = sorted(z.namelist())
            fi = rows(z, "feed_info.txt"); info["feed_info"] = fi[:1] if fi else None
            cal = rows(z, "calendar.txt")
            def col(r, suffix):
                for k, v in r.items():
                    if k and k.strip().lstrip("\ufeff").endswith(suffix) and v: return v.strip()
            if cal:
                info["calendar_keys"] = list(cal[0].keys())
                s = [col(c, "start_date") for c in cal if col(c, "start_date")]; e = [col(c, "end_date") for c in cal if col(c, "end_date")]
                info["calendar"] = {"services": len(cal), "min_start": min(s) if s else None, "max_end": max(e) if e else None}
            cd = rows(z, "calendar_dates.txt")
            if cd:
                d = [col(c, "date") for c in cd if col(c, "date")]; info["calendar_dates"] = {"rows": len(cd), "min": min(d) if d else None, "max": max(d) if d else None}
            ag = rows(z, "agency.txt"); info["agencies"] = [a.get("agency_name") for a in (ag or [])][:15]
            rt = rows(z, "routes.txt")
            if rt:
                from collections import Counter
                info["route_types"] = dict(Counter(r.get("route_type") for r in rt)); info["routes"] = len(rt)
            info["stops"] = count(z, "stops.txt"); info["trips"] = count(z, "trips.txt"); info["stop_times"] = count(z, "stop_times.txt")
        except zipfile.BadZipFile:
            info["error"] = "no es un zip"; info["head"] = data[:300].decode("utf-8", "replace")
    except Exception as ex:
        info["error"] = f"{type(ex).__name__}: {ex}"
    info["seconds"] = round(time.time() - t0, 1)
    out[key] = info
    print(key, info.get("status"), info.get("bytes"), info.get("error", ""), info.get("calendar"), flush=True)
json.dump(out, open("probe/out/summary.json", "w"), ensure_ascii=False, indent=1)
