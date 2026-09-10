#!/usr/bin/env python
"""Build interactive/gemstone_roster.html — the 31-hull gemstone roster, sortable,
filterable, joined to the o-23 GhostShip re-id summary and the frozen-transmitter seven."""
import json, pathlib, pandas as pd

S = pathlib.Path(__file__).resolve().parents[1]
g = pd.read_csv(S / "data/gemstone_fleet_table.csv")
r = pd.read_csv(S / "data/gem_reids_summary.csv")
froz = pd.read_csv(S / "data/bosporus_frozen_roster.csv")

frozen_imos = set(froz.imo.astype(str))
r = r.set_index(r.imo.astype(str))
rows = []
for _, x in g.iterrows():
    imo = str(x.imo)
    s = r.loc[imo] if imo in r.index else None
    rows.append(dict(
        imo=imo, name=x.new_name, english=x.english,
        prev=f"{x.prev_name} ({x.prev_flag})", renamed=str(x.renamed), mmsi=str(x.new_ssvid),
        owner=f"{x.reg_owner} ({x.reg_owner_cty})",
        mgr=x.tech_mgr if isinstance(x.tech_mgr, str) else "",
        mgr_type=x.mgr_type, mgr_inc="" if pd.isna(x.mgr_inc) else str(x.mgr_inc),
        mgr_addr="" if pd.isna(x.mgr_addr) else str(x.mgr_addr),
        sanctions=x.sanctions,
        s2=int(s.s2_matched) if s is not None else 0,
        dark=int(s.gnn_served_clean) if s is not None else 0,
        frozen=imo in frozen_imos,
        rm1801=isinstance(x.mgr_addr, str) and "Easey" in x.mgr_addr,
    ))
rows.sort(key=lambda q: q["renamed"])
COLS = [("name","hull"),("english","gemstone"),("imo","IMO"),("mmsi","new MMSI"),
        ("renamed","renamed"),("prev","was (flag)"),("owner","registered owner"),
        ("mgr","technical manager"),("mgr_inc","mgr incorporated"),("mgr_addr","mgr address"),
        ("s2","S2 AIS-matched"),("dark","dark S2 re-ids"),("sanctions","listed by")]
NUM = {"s2","dark"}

html = """<!doctype html><meta charset="utf-8"><title>The gemstone fleet — 31 sanctioned Aframaxes renamed in eight weeks</title>
<style>
:root{--bg:#fbfaf8;--fg:#141210;--mut:#6d6659;--line:#ded7cb;--acc:#8c2f1f;--hl:#fdf3ea}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:18px 16px 48px}
h1{font-size:19px;margin:0 0 3px;letter-spacing:-.01em}
p.sub{margin:0 0 14px;color:var(--mut);font-size:12.5px;max-width:82ch}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 12px}
input[type=search]{font:inherit;padding:5px 9px;border:1px solid var(--line);border-radius:5px;background:#fff;color:inherit;min-width:220px}
button.chip{font:inherit;font-size:12px;padding:4px 10px;border:1px solid var(--line);border-radius:99px;background:#fff;color:var(--mut);cursor:pointer}
button.chip.on{background:var(--acc);border-color:var(--acc);color:#fff}
.count{font-size:12px;color:var(--mut);margin-left:auto;font-variant-numeric:tabular-nums}
.tl{display:flex;height:34px;align-items:flex-end;gap:1px;border-bottom:1px solid var(--line);margin:0 0 14px;padding-bottom:0}
.tl i{flex:1;background:#e6ded2;border-radius:1px 1px 0 0}
.tl i.on{background:var(--acc)}
.scroll{overflow:auto;max-height:74vh;border:1px solid var(--line);border-radius:7px;background:#fff}
table{border-collapse:separate;border-spacing:0;font-size:12px;width:100%}
th,td{padding:5px 8px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:#f4f0e9;cursor:pointer;font-weight:600;z-index:2;user-select:none}
th:hover{color:var(--acc)}
th .a{color:var(--acc);font-size:10px}
tbody tr:hover td{background:var(--hl)}
td.n{text-align:right;font-variant-numeric:tabular-nums}
td.name{font-weight:600;letter-spacing:.02em}
tr.frozen td.name::after{content:" ❄";color:#2f6f8c}
mark.rm{background:#f6dfd8;color:var(--acc);padding:0 3px;border-radius:2px}
.key{font-size:11.5px;color:var(--mut);margin:10px 0 0;max-width:88ch}
@media (prefers-color-scheme:dark){:root{--bg:#131211;--fg:#eae6df;--mut:#9a9287;--line:#302c27;--acc:#e08a72;--hl:#221c19}
 .scroll,input[type=search],button.chip{background:#1b1917}th{background:#221f1c}
 .tl i{background:#302c27}mark.rm{background:#37211c}}
</style>
<div class="wrap">
<h1>The gemstone fleet</h1>
<p class="sub">31 sanctioned tankers renamed to Russian gemstone words and moved onto Russian <code>27312xxx0</code> MMSIs between 2026-07-14 and 2026-09-05. Sort any column; ❄ = froze its transmitter off the Bosporus (o-23).</p>
<div class="bar">
 <input type="search" id="q" placeholder="filter hull, manager, owner, flag…">
 <button class="chip" data-f="shell">HK place-name shell</button>
 <button class="chip" data-f="rm1801">Rm 1801, Easey Commercial Bldg</button>
 <button class="chip" data-f="frozen">frozen transmitter (o-23)</button>
 <button class="chip" data-f="dark">has dark S2 re-id</button>
 <span class="count" id="cnt"></span>
</div>
<div class="tl" id="tl" title="renames in time order, 2026-07-14 → 2026-09-05"></div>
<div class="scroll"><table><thead><tr id="hd"></tr></thead><tbody id="tb"></tbody></table></div>
<p class="key">Sources: names/MMSIs/dates from <code>ssvids_identities_daily</code>; owner, manager and prior flag from S&amp;P (snapshot 2026-03-20); manager incorporation date and address from Orbis via UCL (2026-09-08). Rm 1801 Easey Commercial Bldg is also the registered address of OFAC-listed Damai Technology Development and EU-listed Zhu Jiang Shipmanagement. <b>S2 AIS-matched</b> = Sentinel-2 detections matched by the hull's own AIS; <b>dark S2 re-ids</b> = dark detections the production GNN re-identified to the hull at confidence &gt; 0.3 since the rename.</p>
</div>
<script>
const ROWS = __ROWS__, COLS = __COLS__, NUM = new Set(__NUM__);
let sk='renamed', sd=1, filt=new Set();
const hd=document.getElementById('hd'), tb=document.getElementById('tb'),
      cnt=document.getElementById('cnt'), tl=document.getElementById('tl'), q=document.getElementById('q');
hd.innerHTML=COLS.map(([k,l])=>`<th data-k="${k}">${l} <span class="a"></span></th>`).join('');
hd.querySelectorAll('th').forEach(th=>th.onclick=()=>{
  const k=th.dataset.k; sd = (k===sk) ? -sd : (NUM.has(k)?-1:1); sk=k; draw();});
document.querySelectorAll('button.chip').forEach(b=>b.onclick=()=>{
  const f=b.dataset.f; filt.has(f)?filt.delete(f):filt.add(f); b.classList.toggle('on'); draw();});
q.oninput=draw;
function keep(r){
  if(filt.has('shell') && !r.mgr_type.startsWith('HK')) return false;
  if(filt.has('rm1801') && !r.rm1801) return false;
  if(filt.has('frozen') && !r.frozen) return false;
  if(filt.has('dark') && !r.dark) return false;
  const s=q.value.trim().toLowerCase();
  return !s || COLS.some(([k])=>String(r[k]).toLowerCase().includes(s));
}
function draw(){
  const v=ROWS.filter(keep).sort((a,b)=>{
    const x=a[sk], y=b[sk];
    return (NUM.has(sk) ? x-y : String(x).localeCompare(String(y))) * sd;});
  tb.innerHTML=v.map(r=>'<tr'+(r.frozen?' class="frozen"':'')+'>'+COLS.map(([k])=>{
    let val=r[k]===''||r[k]===null?'—':r[k];
    if(k==='mgr_addr' && r.rm1801) val='<mark class="rm">'+val+'</mark>';
    return `<td class="${NUM.has(k)?'n':(k==='name'?'name':'')}">${val}</td>`;}).join('')+'</tr>').join('');
  cnt.textContent=v.length+' of '+ROWS.length+' hulls';
  const on=new Set(v.map(r=>r.imo));
  tl.innerHTML=ROWS.slice().sort((a,b)=>a.renamed<b.renamed?-1:1)
    .map(r=>`<i class="${on.has(r.imo)?'on':''}" style="height:${on.has(r.imo)?100:45}%" title="${r.name} — ${r.renamed}"></i>`).join('');
  hd.querySelectorAll('th').forEach(th=>th.querySelector('.a').textContent = th.dataset.k===sk?(sd>0?'▲':'▼'):'');
}
draw();
</script>
"""
html = (html.replace("__ROWS__", json.dumps(rows, ensure_ascii=False))
            .replace("__COLS__", json.dumps(COLS))
            .replace("__NUM__", json.dumps(sorted(NUM))))
out = S / "interactive/gemstone_roster.html"
out.write_text(html)
print("wrote", out, len(rows), "hulls;", sum(r["rm1801"] for r in rows), "at Rm 1801;",
      sum(r["mgr_type"].startswith("HK") for r in rows), "HK shells;",
      sum(r["frozen"] for r in rows), "frozen;", sum(r["dark"] for r in rows), "dark re-ids")
