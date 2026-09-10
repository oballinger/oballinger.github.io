#!/usr/bin/env python
"""interactive/dark_tankers_map.html — every dark tanker detection in the Black Sea in
2026 (band 3, GNN hull = tanker, conf > 0.3, no serving-exclusion flag), one colour per
re-identified hull. Click a dot to isolate that hull; ring = sanctioned at the time.
Source: o-28 results/blacksea_dets_2024_2026.parquet + dark_hull_names.csv + o28_map_chips.json."""
import json, pathlib, colorsys
import pandas as pd

S = pathlib.Path(__file__).resolve().parents[1]
R = pathlib.Path("/home/sai/users/ollie/GFW/GhostShip/experiments/oil/o-28-black-sea-coast-hugging/results")
d = pd.read_parquet(R / "blacksea_dets_2024_2026.parquet")
d["date"] = pd.to_datetime(d["date"])
excl = [c for c in d.columns if c.startswith("excluded_")]
m = (d.band == 3) & (d.gnn_confidence > 0.3) & (d.hull_class == "tanker") & (d.date.dt.year == 2026)
for c in excl:
    m &= ~d[c].fillna(False).astype(bool)
dk = d[m].copy()
names = pd.read_csv(R / "dark_hull_names.csv").set_index("vessel_id")
chips = json.load(open(R / "o28_map_chips.json"))

counts = dk.reid_hull_token.value_counts()
rank = {h: i for i, h in enumerate(counts.index)}
def col(i):
    h = (i * 0.618033988749895) % 1.0
    l = 0.42 if i % 2 else 0.55
    r, g, b = colorsys.hls_to_rgb(h, l, 0.85)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))

hulls = {}
for h, n in counts.items():
    nm = names.shipname.get(h) if h in names.index else None
    aka = names.aka.get(h) if h in names.index else None
    lists = dk[dk.reid_hull_token == h].sanc_lists.dropna()
    hulls[h] = dict(name=(nm if isinstance(nm, str) else h.replace("IMO-", "IMO ")), token=h, n=int(n),
                    color=col(rank[h]), aka=(aka if isinstance(aka, str) else ""),
                    lists=(lists.iloc[0] if len(lists) else ""), gem=bool(dk[dk.reid_hull_token == h].is_gemstone.fillna(False).astype(bool).any()))
pts = []
for r in dk.sort_values("date").itertuples():
    pts.append([round(float(r.lat), 4), round(float(r.lon), 4), r.reid_hull_token, r.date.strftime("%Y-%m-%d"),
                round(float(r.gnn_confidence), 2), int(isinstance(r.sanc_lists, str)),
                chips.get(r.detect_id, "")])
east = dk[dk.lon > 37]
stats = dict(n=len(dk), hulls=int(dk.reid_hull_token.nunique()), east_n=len(east), east_hulls=int(east.reid_hull_token.nunique()),
             east_sanc=round(float(east.sanc_lists.notna().mean()), 3), n_chips=sum(1 for p in pts if p[6]))

html = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dark tanker detections, Black Sea 2026 — coloured by hull</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
html,body{{margin:0;height:100%;font:12px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#16130f}}
#map{{position:absolute;inset:0;background:#dfe9ef}}
.pills{{position:absolute;top:10px;left:10px;z-index:1000;display:flex;flex-wrap:wrap;gap:4px;max-width:calc(100% - 80px)}}
.pills button{{font:600 11px/1 inherit;font-family:inherit;padding:5px 8px;border-radius:99px;border:1px solid rgba(0,0,0,.18);background:rgba(255,255,255,.94);cursor:pointer;color:#333;box-shadow:0 1px 2px rgba(0,0,0,.08)}}
.pills button.on{{background:#16130f;color:#fff;border-color:#16130f}}
.card{{position:absolute;top:44px;left:10px;z-index:1000;background:rgba(255,255,255,.96);border:1px solid rgba(0,0,0,.14);border-radius:6px;padding:8px 10px;font-size:11.5px;line-height:1.45;max-width:260px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.card b{{font-weight:600}} .card i.sw{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.card .x{{float:right;cursor:pointer;color:#888;margin-left:8px}}
.legend{{position:absolute;bottom:22px;right:10px;z-index:1000;background:rgba(255,255,255,.94);border:1px solid rgba(0,0,0,.14);border-radius:6px;padding:8px 10px;font-size:11.5px;line-height:1.5;max-width:300px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.legend b{{font-weight:600}} .legend .k{{display:inline-block;width:14px;text-align:center;margin-right:3px}}
.num{{font:700 9.5px/16px sans-serif;color:#fff;text-align:center;width:16px;height:16px;border-radius:50%;border:1.5px solid #fff;box-shadow:0 0 2px rgba(0,0,0,.5)}}
.leaflet-popup-content{{margin:10px 12px;font-size:12px;line-height:1.45}}
.leaflet-popup-content img{{display:block;width:120px;height:120px;image-rendering:pixelated;border:1px solid #ccc;margin:6px 0 2px}}
.leaflet-popup-content .h{{font-weight:600;font-size:12.5px}}
.leaflet-container{{font-family:inherit}} .leaflet-control-attribution{{font-size:9.5px}}
</style></head><body>
<div id="map"></div>
<div class="pills" id="pills"><button class="on" data-f="all">all hulls</button><button data-f="sanc">sanctioned only</button><button data-f="gem">gemstone fleet</button></div>
<div class="card" id="card" hidden></div>
<div class="legend"><b>Dark tanker detections, Black Sea, Jan–Aug 2026</b><br>
{stats['n']:,} Sentinel-2 detections with no AIS, re-identified to {stats['hulls']} tanker hulls at confidence &gt; 0.3.<br>
<span class="k">●</span> one colour per hull · <span class="k">◉</span> dark ring = hull sanctioned<br>
Click a dot to isolate that hull and link its detections in date order; click the map to reset. East of 37 E: {stats['east_n']} detections, {stats['east_hulls']} hulls, {round(stats['east_sanc']*100)}% sanctioned.</div>
<script>
const HULLS = {json.dumps(hulls)};
const PTS = {json.dumps(pts)};
const map = L.map('map', {{zoomControl:false, scrollWheelZoom:false, preferCanvas:true}});
L.control.zoom({{position:'topright'}}).addTo(map);
map.on('click', ()=>{{ map.scrollWheelZoom.enable(); reset(); }}); map.on('mouseout', ()=>map.scrollWheelZoom.disable());
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:13,attribution:'Esri, GEBCO, NOAA, Garmin'}}).addTo(map);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}',{{maxZoom:13,opacity:.85}}).addTo(map);
let filt='all', solo=null; const markers=[]; const link=L.layerGroup().addTo(map);
const card=document.getElementById('card');
function style(p){{ const h=HULLS[p[2]]; const on = (solo? p[2]===solo : true) && (filt==='all' || (filt==='sanc'&&p[5]) || (filt==='gem'&&h.gem));
  return {{radius: solo&&on?6:4.5, fillColor:h.color, fillOpacity: on?0.9:0.06, color: p[5]?'#16130f':'#fff', weight: on?(p[5]?1.6:0.8):0, opacity: on?1:0}}; }}
function redraw(){{ markers.forEach(([m,p])=>{{ m.setStyle(style(p)); }}); }}
function reset(){{ solo=null; card.hidden=true; link.clearLayers(); redraw(); }}
function drawLink(tok){{ link.clearLayers(); const h=HULLS[tok]; const pts=PTS.filter(p=>p[2]===tok);
  if(pts.length>1) L.polyline(pts.map(p=>[p[0],p[1]]),{{color:h.color,weight:2,dashArray:'5 5',opacity:.95,interactive:false}}).addTo(link);
  pts.forEach((p,i)=>L.marker([p[0],p[1]],{{icon:L.divIcon({{className:'num',html:String(i+1),iconSize:[16,16],iconAnchor:[8,8]}}),interactive:false,zIndexOffset:900}})
    .on('add',e=>{{e.target.getElement().style.background=h.color;}}).addTo(link)); }}
for(const p of PTS){{ const h=HULLS[p[2]];
  const m=L.circleMarker([p[0],p[1]], style(p)).addTo(map);
  m.bindTooltip(`${{h.name}} · ${{p[3]}} · conf ${{p[4]}}`+(p[5]?' · listed':''), {{direction:'top', offset:[0,-4]}});
  m.bindPopup(`<div class="h">${{h.name}}</div>${{h.token}}${{h.aka?'<br><span style="color:#666">aka '+h.aka+'</span>':''}}<br>${{p[3]}} · re-id confidence ${{p[4]}}<br>${{h.lists?'listed: '+h.lists.replace(/,/g,' '):'not listed'}}<br>${{h.n}} dark detections in 2026`+(p[6]?`<img src="${{p[6]}}" alt="Sentinel-2 chip">`:''));
  m.on('click', e=>{{ L.DomEvent.stopPropagation(e); solo=p[2]; redraw(); drawLink(p[2]);
    card.innerHTML=`<span class="x" onclick="reset()">✕</span><i class="sw" style="background:${{h.color}}"></i><b>${{h.name}}</b> · ${{h.n}} detections, numbered and linked in date order`+(h.lists?`<br><span style="color:#666">listed: ${{h.lists.replace(/,/g,' ')}}</span>`:'')+(h.gem?'<br><span style="color:#8c2f1f">gemstone-fleet rename</span>':''); card.hidden=false; }});
  markers.push([m,p]); }}
document.querySelectorAll('.pills button').forEach(b=>b.onclick=()=>{{ filt=b.dataset.f; document.querySelectorAll('.pills button').forEach(x=>x.classList.toggle('on',x===b)); redraw(); }});
map.fitBounds([[40.6,27.4],[45.6,41.8]]);
</script></body></html>"""
out = S / "interactive/dark_tankers_map.html"
out.write_text(html)
print("wrote", out, f"{out.stat().st_size/1024:.0f} KB", stats)
