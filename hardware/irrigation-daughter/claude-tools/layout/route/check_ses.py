#!/usr/bin/env python3
"""Independent connectivity check for a Freerouting .ses result.

Freerouting's own "incomplete_count" is unreliable — it reports 0 on results that
have dropped segments. This builds a union-find over trace segments, vias and pad
centres and reports any net that ends up in more than one piece.

Usage
-----
    # under KiCad's bundled python (reads pads straight from the board):
    kicad-python check_ses.py routed.ses board.kicad_pcb

    # anywhere, using a previously dumped pad list:
    python3 check_ses.py routed.ses pads.json

pads.json is a list of {"ref","pad","net","x","y"} in mm. Dump it with:

    import pcbnew, json
    b = pcbnew.LoadBoard("board.kicad_pcb")
    json.dump([{"ref": f.GetReference(), "pad": p.GetNumber(),
                "net": str(p.GetNetname()),
                "x": p.GetPosition().x/1e6, "y": p.GetPosition().y/1e6}
               for f in b.GetFootprints() for p in f.Pads()],
              open("pads.json", "w"))

Exit status is 0 when every net is whole, 1 otherwise.
"""

import collections
import json
import math
import os
import re
import sys

# Freerouting writes SES at 10 units per micron; 1 mm = 10000 units.
SES_PER_MM = 10000.0
# Two pieces of copper touching within this (mm) are treated as connected.
TOL = 0.06
# Nets never routed as traces (ground pour, etc.) — skip them.
SKIP_NETS = {"/GND", "GND"}

_PATH = re.compile(r"\(path (\S+) (\d+)\n((?:\s+-?\d+ -?\d+\n)+)")
_VIA = re.compile(r'\(via "([^"]+)"\s+(-?\d+)\s+(-?\d+)')


def _seg_point_distance(a, b, p):
    (ax, ay), (bx, by), (px, py) = a, b, p
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        t = 0.0
    else:
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def load_pads(path):
    """Pad centres by net name, from pads.json or straight from a .kicad_pcb."""
    if path.endswith(".json"):
        rows = json.load(open(path))
    else:
        import pcbnew  # only available under KiCad's bundled interpreter

        board = pcbnew.LoadBoard(path)
        rows = [
            {
                "ref": f.GetReference(),
                "pad": p.GetNumber(),
                "net": str(p.GetNetname()),
                "x": p.GetPosition().x / 1e6,
                "y": p.GetPosition().y / 1e6,
            }
            for f in board.GetFootprints()
            for p in f.Pads()
        ]
    by_net = collections.defaultdict(list)
    for r in rows:
        net = (r.get("net") or "").strip('"')
        if not net or net.startswith("unconnected-"):
            continue
        by_net[net].append(("%s-%s" % (r["ref"], r["pad"]), (r["x"], r["y"])))
    return by_net


def parse_ses(path):
    """{net name: [(kind, layer, (p0, p1), label), ...]} from a Specctra session."""
    text = open(path).read()
    body = text[text.find("(network_out"):]
    nets = {}
    for block in re.split(r"\n      \(net ", body)[1:]:
        name = block.split("\n", 1)[0].strip().strip('"')
        nodes = []
        for m in _PATH.finditer(block):
            layer = m.group(1)
            pts = [
                (x / SES_PER_MM, -y / SES_PER_MM)
                for x, y in (
                    tuple(map(int, line.split()))
                    for line in m.group(3).strip().split("\n")
                )
            ]
            for a, b in zip(pts, pts[1:]):
                nodes.append(("trace", layer, (a, b), None))
        for m in _VIA.finditer(block):
            c = (int(m.group(2)) / SES_PER_MM, -int(m.group(3)) / SES_PER_MM)
            nodes.append(("via", None, (c, c), None))
        nets[name] = nodes
    return nets


def pieces(nodes):
    """Split a net's copper into connected components."""
    n = len(nodes)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        kind_i, layer_i, geom_i, _ = nodes[i]
        for j in range(i + 1, n):
            kind_j, layer_j, geom_j, _ = nodes[j]
            # two traces only meet if they share a layer; pads and vias span layers
            if kind_i == "trace" and kind_j == "trace" and layer_i != layer_j:
                continue
            touching = any(
                _seg_point_distance(geom_j[0], geom_j[1], p) <= TOL for p in geom_i
            ) or any(
                _seg_point_distance(geom_i[0], geom_i[1], p) <= TOL for p in geom_j
            )
            if touching:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[ra] = rb

    groups = collections.defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return list(groups.values())


def check(ses_path, pads_path, verbose=True):
    nets = parse_ses(ses_path)
    pads_by_net = load_pads(pads_path)

    for net, pads in pads_by_net.items():
        nodes = nets.setdefault(net, [])
        for label, centre in pads:
            nodes.append(("pad", None, (centre, centre), label))

    broken = {}
    for net, nodes in nets.items():
        if net in SKIP_NETS or net.startswith("unconnected-") or not nodes:
            continue
        groups = pieces(nodes)
        if len(groups) > 1:
            broken[net] = [
                sorted(nodes[i][3] for i in g if nodes[i][0] == "pad") for g in groups
            ]

    if verbose:
        if broken:
            for net in sorted(broken):
                print("  %-16s %s" % (net, broken[net]))
        print("%s: %d net(s) in more than one piece" % (
            os.path.basename(ses_path), len(broken)))
    return broken


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(1 if check(sys.argv[1], sys.argv[2]) else 0)
