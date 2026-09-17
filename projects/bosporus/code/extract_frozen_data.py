#!/usr/bin/env python
"""Slice the o-23 frozen-fleet figure's `const DATA` into the two build inputs.

    build/frozen_data.json   the FROZEN hulls (frozen_days > 0), minus `chips`/`ref`
    build/frozen_chips.json  {hull name: its chips}

The o-23 figure carries every roster hull including the moving decoys, which have no
frozen point to draw an ✕ at; the page's frozen-fleet map is the frozen ones only.
Run this first on any refresh, then build_maps.py.

    PYTHONPATH=<GhostShip> python code/extract_frozen_data.py [path to o23_frozen_fleet.html]
"""
import json, pathlib, sys

S = pathlib.Path(__file__).resolve().parents[1]
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                   "/home/sai/users/ollie/GFW/GhostShip/experiments/oil/"
                   "o-23-bosporus-frozen-transmitter-fleet/figures/o23_frozen_fleet.html")

line = next(l for l in SRC.read_text().splitlines() if l.startswith("const DATA = "))
D = json.loads(line[len("const DATA = "):].rstrip(";"))

chips, hulls = {}, []
for h in D["hulls"]:
    if not h.get("frozen_days"):
        continue                      # moving decoy: no frozen point, not on this map
    chips[h["name"]] = h.get("chips", [])
    hulls.append({k: v for k, v in h.items() if k not in ("chips", "ref")})
D["hulls"] = hulls

json.dump(D, open(S / "build/frozen_data.json", "w"), separators=(",", ":"))
json.dump(chips, open(S / "build/frozen_chips.json", "w"), separators=(",", ":"))
print(f"{len(hulls)} frozen hulls: {', '.join(h['name'] for h in hulls)}")
print(f"meta: {D['meta']}")
