#!/usr/bin/env python
"""Build the three bare Leaflet maps for the page.

  interactive/frozen_fleet_map.html   8 frozen transmitters: broadcast X, hourly AIS,
                                      Sentinel-2 re-ids during the freeze (with chips)
  interactive/strikes_map.html        14 drone strikes (o-23 placement) + the hull's
                                      re-identified resting place (o-26)
  interactive/dual_stream_map.html    one MMSI, two transmitters: fixed X vs the moving
                                      hull track, from the raw hourly AIS

Inputs: build/frozen_data.json + build/frozen_chips.json (extracted from the o-23
figure's `const DATA`), o-26 results/o26_resting_places.csv, o-23
results/dual_stream_raw.csv. Basemap: Esri (keyless). No mastheads, no panels — a map,
a legend, and hull pills.
"""
import json, pathlib, math
import pandas as pd

S = pathlib.Path(__file__).resolve().parents[1]
OIL = pathlib.Path("/home/sai/users/ollie/GFW/GhostShip/experiments/oil")
D = json.load(open(S / "build/frozen_data.json"))
CHIPS = json.load(open(S / "build/frozen_chips.json"))

HULL_ORDER = ["AKKORD", "STRATEG", "PIROP", "KHRIZOPRAZ", "DEMANTOID", "MIMOZA", "LABRADOR", "INVICTA"]
COL = {"AKKORD": "#d55e00", "STRATEG": "#0072b2", "PIROP": "#cc3d8a", "KHRIZOPRAZ": "#009e73",
       "DEMANTOID": "#e69f00", "MIMOZA": "#56b4e9", "LABRADOR": "#7b3294", "INVICTA": "#444444"}

CSS = """
html,body{margin:0;height:100%;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#16130f}
#map{position:absolute;inset:0;background:#dfe9ef}
.pills{position:absolute;top:10px;left:10px;z-index:1000;display:flex;flex-wrap:wrap;gap:4px;max-width:calc(100% - 80px)}
.pills button{font:600 11px/1 inherit;font-family:inherit;padding:5px 8px;border-radius:99px;border:1px solid rgba(0,0,0,.18);
  background:rgba(255,255,255,.94);cursor:pointer;color:#333;display:flex;align-items:center;gap:5px;box-shadow:0 1px 2px rgba(0,0,0,.08)}
.pills button i{width:9px;height:9px;border-radius:50%;display:inline-block;border:1px solid rgba(0,0,0,.25)}
.pills button.off{opacity:.42}
.pills button.all{background:#16130f;color:#fff;border-color:#16130f}
.legend{position:absolute;top:80px;right:10px;z-index:1000;background:rgba(255,255,255,.94);border:1px solid rgba(0,0,0,.14);
  border-radius:6px;padding:7px 9px;font-size:11px;line-height:1.45;max-width:250px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.legend b{font-weight:600}
.legend .k{display:inline-block;width:14px;text-align:center;margin-right:3px}
.xmark{font:700 16px/1 sans-serif;text-shadow:0 0 3px #fff,0 0 3px #fff;text-align:center}
.num{font:700 9.5px/16px sans-serif;color:#fff;text-align:center;width:16px;height:16px;border-radius:50%;border:1.5px solid #fff;box-shadow:0 0 2px rgba(0,0,0,.5)}
.tri{width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:11px solid;filter:drop-shadow(0 0 1.5px #fff)}
.star{font:16px/1 sans-serif;text-shadow:0 0 3px #fff,0 0 2px #fff;text-align:center}
.leaflet-popup-content{margin:10px 12px;font-size:12px;line-height:1.45}
.leaflet-popup-content img{display:block;width:120px;height:120px;image-rendering:pixelated;border:1px solid #ccc;margin:6px 0 2px}
.leaflet-popup-content .h{font-weight:600;font-size:12.5px}
.leaflet-container{font-family:inherit}
.leaflet-control-attribution{font-size:9.5px}
"""

LEAFLET = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
           '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>')

BASE_OCEAN = """
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:13, attribution:'Esri, GEBCO, NOAA, Garmin'}).addTo(map);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:13, opacity:.85}).addTo(map);
"""
BASE_IMAGERY = """
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:17, attribution:'Esri, Maxar, Earthstar Geographics'}).addTo(map);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
  {maxZoom:17, opacity:.9}).addTo(map);
"""

PILLS_JS = """
// hull pills: click isolates a hull, click again shows all, "all" resets
const groups = {};                       // name -> L.layerGroup
const pills = document.getElementById('pills');
function setVisible(on){ for(const [n,g] of Object.entries(groups)){ if(on.has(n)) g.addTo(map); else map.removeLayer(g);}
  pills.querySelectorAll('button[data-h]').forEach(b=>b.classList.toggle('off', !on.has(b.dataset.h))); }
let solo=null;
function pill(name, color){ const b=document.createElement('button'); b.dataset.h=name;
  b.innerHTML=`<i style="background:${color}"></i>${name}`;
  b.onclick=()=>{ solo = (solo===name)? null : name; setVisible(new Set(solo? [solo] : Object.keys(groups))); };
  pills.appendChild(b); }
const allBtn=document.createElement('button'); allBtn.className='all'; allBtn.textContent='all';
allBtn.onclick=()=>{solo=null; setVisible(new Set(Object.keys(groups)));}; pills.appendChild(allBtn);
"""

def page(title, legend_html, body_js, base, extra_css=""):
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>{LEAFLET}<style>{CSS}{extra_css}</style></head><body>
<div id="map"></div><div class="pills" id="pills"></div><div class="legend">{legend_html}</div>
<script>
const map = L.map('map', {{zoomControl:false, attributionControl:true, scrollWheelZoom:false}});
L.control.zoom({{position:'topright'}}).addTo(map);
map.on('click', ()=>map.scrollWheelZoom.enable()); map.on('mouseout', ()=>map.scrollWheelZoom.disable());
{base}
{PILLS_JS}
{body_js}
</script></body></html>"""

def chips_for(name, tags):
    out = {}
    for c in CHIPS.get(name, []):
        if c["tag"] in tags:
            out[c["tag"]] = c["img"]
    return out

# ───────────────────────── 1. frozen fleet ─────────────────────────
# The Black Sea sortie of each frozen-transmitter hull: every dark detection between its
# northbound Bosporus entry (last hourly AIS fix south of 41.25 N before the freeze) and its
# southbound exit (KEGM/webcam/AIS, o-23 notes) or the data frontier, inside the Black Sea,
# numbered and linked in date order. Source: code/pull_frozen_fleet_dets.py (prod re-id +
# raw inference + embedding hunt, deduped) — no distinction by source or serving status.
EXIT = {"STRATEG": "2026-08-31", "MIMOZA": "2026-08-28", "DEMANTOID": "2026-09-06",
        "KHRIZOPRAZ": "2026-09-08", "PIROP": "2026-09-08"}          # others: not out by the frontier
FRONTIER = "2026-09-06"
ENTRY = {"MIMOZA": "2026-07-01"}   # already inside the Black Sea when the hourly record starts (at Samsun since July)
BOX = dict(lat0=40.9, lat1=47.5, lon0=27.4, lon1=42.0)
ALL = pd.read_csv(S / "build/frozen_fleet_all_dets.csv")
ALL = ALL[ALL.is_band1 != True].copy()
try:
    O28CH = json.load(open(OIL / "o-28-black-sea-coast-hugging/results/o28_map_chips.json"))
except Exception:
    O28CH = {}
figchip = {}
for h in D["hulls"]:
    ch = {c["tag"]: c["img"] for c in CHIPS.get(h["name"], [])}
    for r in h["dark"] + h["hunt"]:
        if ch.get(str(r["n"])):
            figchip[(h["name"], r["date"])] = ch[str(r["n"])]
import datetime as _dt
def entry_date(h):
    """last hourly fix south of 41.25 N (Bosporus/Marmara) before the freeze start."""
    fs = _dt.datetime.fromisoformat(h["start"]).replace(tzinfo=_dt.timezone.utc)
    last = None
    for ms, lat, lon, sog, cog, fl in h["hourly"]:
        t = _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc)
        if fl == 1 and t < fs and lat < 41.25 and lon < 29.6:
            last = t
    return (last.date().isoformat() if last else h["start"])
hulls_js = []; WIN = {}
for h in D["hulls"]:
    n = h["name"]; a = ENTRY.get(n) or entry_date(h); b = EXIT.get(n, FRONTIER); WIN[n] = (a, b)
    rows = ALL[(ALL.imo.astype(str) == str(h["imo"])) & (ALL.date >= a) & (ALL.date <= b)
               & (ALL.detect_lat >= BOX["lat0"]) & (ALL.detect_lon >= BOX["lon0"]) & (ALL.detect_lon <= BOX["lon1"])].sort_values("detect_ts")
    pts = [dict(date=r.date, lat=round(float(r.detect_lat), 4), lon=round(float(r.detect_lon), 4),
                conf=(None if pd.isna(r.gnn_confidence) else round(float(r.gnn_confidence), 2)),
                km=int(r.km_from_broadcast), during=bool(r.during_freeze),
                chip=O28CH.get(r.detect_id) or figchip.get((n, r.date), "")) for r in rows.itertuples()]
    fs = _dt.datetime.fromisoformat(a).replace(tzinfo=_dt.timezone.utc); fe = _dt.datetime.fromisoformat(b).replace(tzinfo=_dt.timezone.utc) + _dt.timedelta(days=1)
    track = [[round(q[1], 4), round(q[2], 4)] for q in h["hourly"] if q[5] == 1 and fs <= _dt.datetime.fromtimestamp(q[0] / 1000, _dt.timezone.utc) < fe]
    hulls_js.append(dict(name=n, imo=h["imo"], color=COL[n], x=[h["lat"], h["lon"]], frozen_days=h["frozen_days"],
                         start=h["start"], end=h["end"], entry=a, exit=(EXIT.get(n) or "not out by " + FRONTIER),
                         sanctions=h["sanctions"], track=track, pts=pts))
print("sortie windows / dark detections:", {k: (v, len(next(x for x in hulls_js if x["name"] == k)["pts"])) for k, v in WIN.items()})

frozen_js = f"""
const HULLS = {json.dumps(hulls_js)};
const TUR12 = {json.dumps(D["tur12"])};
const TERMINALS = {json.dumps(D["terminals"])};
L.geoJSON(TUR12, {{style:{{color:'#666', weight:1, dashArray:'3 4', opacity:.7, fill:false}}}}).addTo(map)
  .bindTooltip('Turkish 12 nm limit', {{sticky:true}});
TERMINALS.forEach(t=>L.marker([t.lat,t.lon],{{icon:L.divIcon({{className:'',html:'<div style="width:7px;height:7px;background:#222;transform:rotate(45deg);border:1px solid #fff"></div>',iconSize:[7,7],iconAnchor:[4,4]}}),interactive:true}})
  .bindTooltip(t.name+' oil terminal',{{direction:'top',offset:[0,-4]}}).addTo(map));
for(const h of HULLS){{
  const g = L.layerGroup(); groups[h.name]=g; pill(h.name, h.color);
  if(h.track.length>1) L.polyline(h.track, {{color:h.color, weight:1.2, opacity:.4}}).addTo(g)
     .bindTooltip(h.name+" — what its MMSI broadcast (hourly)", {{sticky:true}});
  if(h.pts.length>1) L.polyline(h.pts.map(p=>[p.lat,p.lon]), {{color:h.color, weight:2, dashArray:'5 5', opacity:.95}}).addTo(g);
  L.marker(h.x, {{icon:L.divIcon({{className:'xmark', html:`<span style="color:${{h.color}}">✕</span>`, iconSize:[18,18], iconAnchor:[9,9]}}), zIndexOffset:400}}).addTo(g)
    .bindPopup(`<div class="h">${{h.name}} · IMO ${{h.imo}}</div>broadcast position while frozen<br>${{h.x[0].toFixed(4)}} N, ${{h.x[1].toFixed(4)}} E<br>frozen ${{h.frozen_days}} days, ${{h.start}} → ${{h.end}}<br>entered the Black Sea ${{h.entry}} · exit ${{h.exit}}<br><span style="color:#666">listed: ${{h.sanctions.replace(/,/g,' ')}}</span>`);
  h.pts.forEach((d,i)=>{{
    const m=L.marker([d.lat,d.lon], {{icon:L.divIcon({{className:'num', html:String(i+1), iconSize:[16,16], iconAnchor:[8,8]}}), zIndexOffset:500}});
    m.on('add', e=>{{ e.target.getElement().style.background=h.color; }});
    m.bindTooltip(`${{h.name}} #${{i+1}} · ${{d.date}}`+(d.conf!==null?` · conf ${{d.conf}}`:''), {{direction:'top', offset:[0,-8]}});
    m.bindPopup(`<div class="h">${{h.name}} · #${{i+1}} of ${{h.pts.length}} · ${{d.date}}</div>dark Sentinel-2 detection${{d.during?' — <b>while the transmitter was frozen</b>':''}}<br>${{d.conf!==null?'re-id confidence '+d.conf+'<br>':''}}${{d.km.toLocaleString()}} km from the frozen broadcast position`+(d.chip?`<img src="${{d.chip}}" alt="Sentinel-2 chip">`:''));
    m.addTo(g);
  }});
  g.addTo(map);
}}
map.fitBounds([[40.6,27.4],[45.4,41.9]]);
"""
n_pts = sum(len(h["pts"]) for h in hulls_js)
frozen_legend = ("<b>The frozen fleet's Black Sea sortie, Aug–Sep 2026</b><br>"
                 "<span class='k'>✕</span> position the MMSI broadcast while frozen<br>"
                 f"<span class='k'>●</span> dark Sentinel-2 detections re-identified to the hull between its entry and exit ({n_pts}), "
                 "numbered and linked in date order · click for the chip<br>"
                 "<span class='k'>─</span> what the MMSI broadcast, hourly · <span class='k'>◆</span> oil terminal · dotted grey: Turkish 12 nm")
(S / "interactive/frozen_fleet_map.html").write_text(page("The frozen fleet's Black Sea sortie — every dark detection, numbered", frozen_legend, frozen_js, BASE_OCEAN))

# ───────────────────────── 2. strikes + resting places ─────────────────────────
rest = pd.read_csv(OIL / "o-26-struck-tankers-after-strike/results/o26_resting_places.csv")
rest_by = {r.vessel: r for r in rest.itertuples()}
PAL = ["#d55e00", "#0072b2", "#cc3d8a", "#009e73", "#e69f00", "#56b4e9", "#7b3294", "#a6761d",
       "#1b9e77", "#e7298a", "#66a61e", "#7570b3", "#d95f02"]
ships = []
for a in D["attacks"]:
    if a["ship"] not in ships:
        ships.append(a["ship"])
scol = {s: PAL[i % len(PAL)] for i, s in enumerate(ships)}
strikes_js_rows = [dict(ship=a["ship"], date=a["date"], lat=a["lat"], lon=a["lon"], src=a["source"], grade=a["grade"],
                        weapon=a.get("weapon", ""), outcome=a.get("outcome", ""), color=scol[a["ship"]]) for a in D["attacks"]]
rest_rows = [dict(ship=r.vessel, imo=int(r.imo), lat=float(r.rest_lat), lon=float(r.rest_lon), place=r.rest_place,
                  dwell=int(r.rest_dwell_d), n_s2=int(r.rest_n_s2), color=scol.get(r.vessel, "#333")) for r in rest.itertuples()]
strikes_js = f"""
const STRIKES = {json.dumps(strikes_js_rows)};
const REST = {json.dumps(rest_rows)};
const byShip = {{}};
STRIKES.forEach(s=>{{ (byShip[s.ship]=byShip[s.ship]||{{strikes:[],rest:null,color:s.color}}).strikes.push(s); }});
REST.forEach(r=>{{ (byShip[r.ship]=byShip[r.ship]||{{strikes:[],rest:null,color:r.color}}).rest=r; }});
for(const [ship,o] of Object.entries(byShip)){{
  const g=L.layerGroup(); groups[ship]=g; pill(ship, o.color);
  for(const s of o.strikes){{
    const hollow = s.src!=='ais';
    L.marker([s.lat,s.lon],{{icon:L.divIcon({{className:'star',html:`<span style="color:${{o.color}}">${{hollow?'☆':'★'}}</span>`,iconSize:[18,18],iconAnchor:[9,9]}}),zIndexOffset:600}}).addTo(g)
      .bindPopup(`<div class="h">${{ship}} · struck ${{s.date}}</div>${{s.weapon}}${{s.outcome?' — '+s.outcome:''}}<br><span style="color:#666">position ${{hollow?'from reported wording':"from the victim's own last AIS message"}} (${{s.grade}})</span>`);
    if(o.rest) L.polyline([[s.lat,s.lon],[o.rest.lat,o.rest.lon]],{{color:o.color,weight:1.3,dashArray:'4 5',opacity:.8}}).addTo(g);
  }}
  if(o.rest){{ const r=o.rest; const rad=Math.max(5, Math.min(13, 3+Math.sqrt(r.dwell)*0.65));
    L.circleMarker([r.lat,r.lon],{{radius:rad,color:'#fff',weight:1.5,fillColor:o.color,fillOpacity:.85}}).addTo(g)
      .bindPopup(`<div class="h">${{ship}} · IMO ${{r.imo}}</div>re-identified afterwards at <b>${{r.place}}</b><br>sat there ${{r.dwell}} days · ${{r.n_s2}} dark Sentinel-2 sightings`); }}
  g.addTo(map);
}}
map.fitBounds([[40.4,26.8],[47.2,41.2]]);
"""
strikes_legend = ("<b>Drone strikes on tankers, Nov 2025 – Jul 2026</b><br>"
                  "<span class='k'>★</span> strike, placed from the victim's last AIS message<br>"
                  "<span class='k'>☆</span> strike, placed from reported wording<br>"
                  "<span class='k'>●</span> where GhostShip re-identified the hull afterwards (size: days it stayed)<br>"
                  "<span class='k'>┄</span> same hull")
(S / "interactive/strikes_map.html").write_text(page("Struck tankers — strike positions and resting places", strikes_legend, strikes_js, BASE_OCEAN))

# ───────────────────────── 3. one MMSI, two transmitters ─────────────────────────
raw = pd.read_csv(OIL / "o-23-bosporus-frozen-transmitter-fleet/results/dual_stream_raw.csv", parse_dates=["hr"])
raw = raw.sort_values("hr")
dual = []
for name, grp in raw.groupby("shipname"):
    hull = grp[(grp.stream == "hull") & (~grp.dead_reckoned.astype(bool))]
    decoy = grp[grp.stream == "decoy"]
    # decoy is a fixed point: take the modal position
    if len(decoy):
        dx = decoy.groupby(["flat", "flon"]).size().idxmax()
    else:
        dx = None
    dual.append(dict(name=name, color=COL.get(name, "#333"),
                     x=[float(dx[0]), float(dx[1])] if dx else None,
                     decoy_hours=int(len(decoy)),
                     decoy_span=[str(decoy.hr.min())[:10], str(decoy.hr.max())[:10]] if len(decoy) else None,
                     track=[[round(float(r.lat), 4), round(float(r.lon), 4), str(r.hr)[:13]] for r in hull.itertuples()]))
dual.sort(key=lambda d: HULL_ORDER.index(d["name"]) if d["name"] in HULL_ORDER else 99)
dual_js = f"""
const DUAL = {json.dumps(dual)};
for(const h of DUAL){{
  const g=L.layerGroup(); groups[h.name]=g; pill(h.name, h.color);
  if(h.track.length>1){{
    const segs=[[]]; for(let i=0;i<h.track.length;i++){{ const p=h.track[i];
      if(i>0){{ const q=h.track[i-1]; const dt=(Date.parse(p[2]+':00Z')-Date.parse(q[2]+':00Z'))/3600e3;
        const km=111*Math.hypot(p[0]-q[0],(p[1]-q[1])*Math.cos(p[0]*Math.PI/180));
        if(dt>6 || km/Math.max(dt,0.25)>55) segs.push([]); }}   // gap > 6 h or implied > 30 kn: don't bridge
      segs[segs.length-1].push([p[0],p[1]]); }}
    L.polyline(segs.filter(s=>s.length>1),{{color:h.color,weight:2,opacity:.9}}).addTo(g)
      .bindTooltip(h.name+" — the MMSI's moving broadcast, "+h.track[0][2]+" → "+h.track[h.track.length-1][2]+" UTC (gaps > 6 h not drawn)",{{sticky:true}});
    L.circleMarker([h.track[h.track.length-1][0],h.track[h.track.length-1][1]],{{radius:4,color:'#fff',weight:1,fillColor:h.color,fillOpacity:1}}).addTo(g)
      .bindTooltip(h.name+' — last hour in the data, '+h.track[h.track.length-1][2]+' UTC');
  }}
  if(h.x) L.marker(h.x,{{icon:L.divIcon({{className:'xmark',html:`<span style="color:${{h.color}}">✕</span>`,iconSize:[18,18],iconAnchor:[9,9]}}),zIndexOffset:500}}).addTo(g)
    .bindPopup(`<div class="h">${{h.name}}</div>fixed transmitter at ${{h.x[0].toFixed(4)}} N, ${{h.x[1].toFixed(4)}} E<br>${{h.decoy_hours}} hours of messages, ${{h.decoy_span[0]}} → ${{h.decoy_span[1]}}<br><span style="color:#666">0 kn, fixed course, ~20 msg/h, never drops out</span>`);
  g.addTo(map);
}}
map.fitBounds([[40.4,27.4],[45.2,41.9]]);
"""
dual_legend = ("<b>One MMSI, two transmitters · 12 Aug – 6 Sep 2026</b><br>"
               "<span class='k'>✕</span> the fixed transmitter parked in the Bosporus waiting area<br>"
               "<span class='k'>─</span> the same MMSI's moving broadcast, hour by hour<br>"
               "<span class='k'>●</span> last hour in the data")
(S / "interactive/dual_stream_map.html").write_text(page("One MMSI, two transmitters", dual_legend, dual_js, BASE_IMAGERY,
    extra_css=".legend,.pills button{background:rgba(255,255,255,.96)}"))

for f in ("frozen_fleet_map.html", "strikes_map.html", "dual_stream_map.html"):
    print(f, f"{(S/'interactive'/f).stat().st_size/1024:.0f} KB")
