#!/usr/bin/env python
"""Every Sentinel-2 detection that names one of the eight frozen-transmitter hulls, from
every source we have — not just the during-freeze rows the o-23 figure plotted.

  reid   prod GNN re-id table (post-v4 re-score 2026-09-07), any confidence, with the
         serving-exclusion flags and whether the row survives into the routed (served) view
  raw    prod raw inference: rows whose top candidate is the hull even when the decision
         was `novel` (below the assign threshold) — never materialised into reid
  hunt   o-23 embedding hunt (own AIS-matched chips vs every unmatched 170–320 m detection
         in the Black Sea + Marmara), cosine >= 0.7

Writes build/frozen_fleet_all_dets.csv (one row per detect_id, best source first).
"""
import glob, json, pathlib, math
import pandas as pd
from ghostship.bq import query
from ghostship.pipeline import config as C

S = pathlib.Path(__file__).resolve().parents[1]
O23 = pathlib.Path("/home/sai/users/ollie/GFW/GhostShip/experiments/oil/o-23-bosporus-frozen-transmitter-fleet/results")
D = json.load(open(S / "build/frozen_data.json"))
HULLS = {h["imo"]: h for h in D["hulls"]}
lst = "','".join(HULLS)
IMO_RE = r"^IMO-(\d{7})"

excl_cols = query(f"SELECT column_name FROM `world-fishing-827.scratch_ollie.INFORMATION_SCHEMA.COLUMNS` WHERE table_name='gnn_serving_exclusion_v1' ORDER BY ordinal_position",
                  cap_gb=1, why="frozen fleet: exclusion schema", quiet=True).column_name.tolist()
flag_cols = [c for c in excl_cols if c.startswith("excluded_")]
flags_sel = ", ".join(f"x.{c}" for c in flag_cols) if flag_cols else "NULL AS no_flags"

CACHE = S / "build"
_reid_pq = CACHE / "ff_reid.parquet"
reid = pd.read_parquet(_reid_pq) if _reid_pq.exists() else query(f"""
SELECT r.detect_id, r.detect_ts, r.detect_lat, r.detect_lon, r.gnn_decision, r.gnn_vessel_id, r.gnn_confidence,
       r.gnn_empirical_precision, r.gnn_candidate_count, r.ais_verdict, r.ais_before_km, r.ais_after_km,
       p.length_m_inferred, p.speed_kn_inferred, p.matching_score, p.matching_score_secondary, p.score_no_length,
       (IFNULL(p.matching_score,0) > 1e-3 OR IFNULL(p.matching_score_secondary,0) > 0.05) AS is_band1,
       (IFNULL(p.matching_score,0) < 1e-5 AND IFNULL(p.matching_score_secondary,0) < 1e-3 AND IFNULL(p.score_no_length,0)*0.1 < 1e-5) AS is_band3,
       (v.detect_id IS NOT NULL) AS in_routed, {flags_sel}
FROM `{C.GNN_REID_TABLE}` r
JOIN `{C.PRODUCTION_EMBED_TABLE}` p USING (detect_id)
LEFT JOIN (SELECT DISTINCT detect_id FROM `{C.GNN_REID_TABLE}_routed` WHERE REGEXP_EXTRACT(gnn_vessel_id, r'{IMO_RE}') IN ('{lst}')) v USING (detect_id)
LEFT JOIN `{C.SERVING_EXCLUSION_TABLE}` x USING (detect_id)
WHERE REGEXP_EXTRACT(r.gnn_vessel_id, r'{IMO_RE}') IN ('{lst}')
""", cap_gb=60, why="frozen fleet: every prod re-id naming the 8 hulls")
reid.to_parquet(_reid_pq)
reid["imo"] = reid.gnn_vessel_id.str.extract(IMO_RE)[0]
reid["source"] = "reid"

_raw_pq = CACHE / "ff_raw.parquet"
raw = pd.read_parquet(_raw_pq) if _raw_pq.exists() else query(f"""
SELECT g.detect_id, p.detect_timestamp AS detect_ts, p.detect_lat, p.detect_lon, g.decision AS gnn_decision,
       g.vessel_id AS gnn_vessel_id, g.vessel_id_topcand, g.confidence AS gnn_confidence, g.top_candidate_prob, g.candidate_count AS gnn_candidate_count,
       p.length_m_inferred, p.speed_kn_inferred, p.matching_score, p.matching_score_secondary, p.score_no_length,
       (IFNULL(p.matching_score,0) > 1e-3 OR IFNULL(p.matching_score_secondary,0) > 0.05) AS is_band1,
       (IFNULL(p.matching_score,0) < 1e-5 AND IFNULL(p.matching_score_secondary,0) < 1e-3 AND IFNULL(p.score_no_length,0)*0.1 < 1e-5) AS is_band3
FROM `{C.GNN_RAW_TABLE}` g JOIN `{C.PRODUCTION_EMBED_TABLE}` p USING (detect_id)
WHERE REGEXP_EXTRACT(g.vessel_id, r'{IMO_RE}') IN ('{lst}') OR REGEXP_EXTRACT(g.vessel_id_topcand, r'{IMO_RE}') IN ('{lst}')
""", cap_gb=80, why="frozen fleet: raw inference rows whose top candidate is one of the 8 hulls")
raw.to_parquet(_raw_pq)
raw["imo"] = raw.gnn_vessel_id.str.extract(IMO_RE)[0].fillna(raw.vessel_id_topcand.str.extract(IMO_RE)[0])
raw["source"] = "raw"

hunts = []
for f in sorted(glob.glob(str(O23 / "hunt_*.csv"))):
    if f.endswith("_null.csv"):
        continue
    name = pathlib.Path(f).stem[5:]
    imo = next(i for i, h in HULLS.items() if h["name"] == name)
    h = pd.read_csv(f)
    h = h[h.max_cos >= 0.7].rename(columns={"d": "detect_ts", "lat": "detect_lat", "lon": "detect_lon", "len": "length_m_inferred", "conf": "gnn_confidence"})
    h["imo"] = imo; h["source"] = "hunt"
    hunts.append(h[["detect_id", "detect_ts", "detect_lat", "detect_lon", "length_m_inferred", "gnn_decision", "gnn_vessel_id", "gnn_confidence", "max_cos", "imo", "source"]])
hunt = pd.concat(hunts, ignore_index=True)

allr = pd.concat([reid, raw, hunt], ignore_index=True)
allr["detect_ts"] = pd.to_datetime(allr.detect_ts, utc=True, errors="coerce")
allr["date"] = allr.detect_ts.dt.strftime("%Y-%m-%d")
# during-freeze + km from the broadcast position
def km(a, b, c, d):
    p = math.pi / 180
    return 6371 * 2 * math.asin(math.sqrt(math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2))
allr["name"] = allr.imo.map(lambda i: HULLS[i]["name"])
allr["during_freeze"] = [ (HULLS[i]["start"] <= d <= HULLS[i]["end"]) if isinstance(d, str) else False for i, d in zip(allr.imo, allr.date)]
allr["km_from_broadcast"] = [round(km(la, lo, HULLS[i]["lat"], HULLS[i]["lon"])) for la, lo, i in zip(allr.detect_lat, allr.detect_lon, allr.imo)]
# one row per detect_id: reid > raw > hunt, but keep which sources saw it
src = allr.groupby("detect_id").source.agg(lambda s: "+".join(sorted(set(s))))
best = allr.sort_values("source", key=lambda s: s.map({"reid": 0, "raw": 1, "hunt": 2})).drop_duplicates("detect_id").copy()
best["sources"] = best.detect_id.map(src)
best["excluded"] = best[flag_cols].fillna(False).astype(bool).any(axis=1) if flag_cols else False
fl = best[flag_cols].fillna(False).astype(bool) if flag_cols else None
best["excl_flags"] = fl.apply(lambda r: ",".join(c.replace("excluded_", "") for c in flag_cols if r[c]), axis=1) if flag_cols else ""
best = best.sort_values(["name", "detect_ts"])
out = S / "build/frozen_fleet_all_dets.csv"
best.to_csv(out, index=False)
print("flag cols:", flag_cols)
print("reid", len(reid), "raw", len(raw), "hunt", len(hunt), "-> unique detections", len(best))
dark = best[(best.is_band1 != True)]
print("\nDARK (not band-1) detections per hull:")
print(dark.groupby("name").agg(n=("detect_id", "size"), during_freeze=("during_freeze", "sum"), conf03=("gnn_confidence", lambda x: int((x > 0.3).sum())),
                               served=("in_routed", lambda x: int((x == True).sum())), gate_hidden=("excluded", "sum"),
                               raw_only=("sources", lambda s: int((s == "raw").sum())), hunt_only=("sources", lambda s: int((s == "hunt").sum())),
                               first=("date", "min"), last=("date", "max")).to_string())
