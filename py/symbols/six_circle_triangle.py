"""Form 20 — Segitiga enam lingkaran (Six-Circle Triangle).
Kriteria manual:
  1. Enam lingkaran.
  2. Garis dasar dan minimal satu sisi lain "lurus" (garis dari pusat dua lingkaran ujung minimal
     menyentuh tepi lingkaran di antaranya).
  3. Garis dasar dalam 10° dari horizontal.
  4. Jarak antar-lingkaran pada sisi yang sama tidak lebih dari 2 : 1.
"""
import sys
import math
import itertools
from symbols import _vmi_geom as G


class SixCircleTriangleChecker:
    N = 6
    BASE_TOL = 10.0
    SPACE_RATIO = 2.0
    last_criteria = []

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 4)
        vis = img.copy()
        comps = G.components(d, min_rel_area=0.15)
        circles = []
        for c in comps:
            x, y, w, h = c["bbox"]
            r = (w + h) / 4.0
            fill = c["area"] / float(max(1, w * h))
            # lingkaran = bentuk berlubang, atau goresan melengkung yang hampir tertutup (bukan titik padat)
            ring = bool(c["holes"]) or (fill < 0.55 and max(w, h) / max(1, min(w, h)) < 2.5)
            circles.append({"c": (x + w / 2.0, y + h / 2.0), "r": r, "ring": ring, "bbox": c["bbox"]})
        rings = [c for c in circles if c["ring"]]
        ok1 = len(rings) == C.N and len(circles) == C.N
        det1 = f"{len(rings)} lingkaran" + (f" (+{len(circles) - len(rings)} titik/coretan)" if len(circles) > len(rings) else "") + " (harus 6)"
        ok2 = ok3 = ok4 = False
        det2 = det3 = det4 = "susunan segitiga tidak dapat dinilai"
        if len(circles) >= 4:
            cs = circles
            best = None
            for tri in itertools.combinations(range(len(cs)), 3):
                a, b, c = (cs[i]["c"] for i in tri)
                area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
                if best is None or area > best[0]:
                    best = (area, tri)
            corners = list(best[1])
            mids = [i for i in range(len(cs)) if i not in corners]
            sides = [(corners[i], corners[(i + 1) % 3]) for i in range(3)]
            side_mid = {s: [] for s in sides}
            for m in mids:
                p = cs[m]["c"]
                s = min(sides, key=lambda s_: _seg_dist(p, cs[s_[0]]["c"], cs[s_[1]]["c"]))
                side_mid[s].append(m)
            base = max(sides, key=lambda s: (cs[s[0]]["c"][1] + cs[s[1]]["c"][1]) / 2)
            straight = {}
            spacing = {}
            for s in sides:
                a, b = cs[s[0]], cs[s[1]]
                ms = side_mid[s]
                if len(ms) != 1:
                    straight[s] = False
                    spacing[s] = None
                    continue
                m = cs[ms[0]]
                dd = _line_dist(m["c"], a["c"], b["c"])
                straight[s] = dd <= m["r"] + d.stroke / 2
                g1 = G.dist(a["c"], m["c"])       # jarak antar-pusat
                g2 = G.dist(m["c"], b["c"])
                spacing[s] = max(g1, g2) / min(g1, g2)
            others = [s for s in sides if s != base]
            ok2 = straight[base] and any(straight[s] for s in others)
            det2 = "garis dasar " + ("lurus" if straight[base] else "tidak lurus") + \
                   f"; {sum(straight[s] for s in others)} sisi lain lurus"
            ang = G.ang_diff(G.angle_deg(cs[base[0]]["c"], cs[base[1]]["c"]), 0)
            ok3, det3 = ang <= C.BASE_TOL, f"garis dasar miring {ang:.0f}° (maks 10°)"
            rat = [v for v in spacing.values() if v is not None]
            ok4 = len(rat) == 3 and max(rat) <= C.SPACE_RATIO
            det4 = ("jarak antar-lingkaran: " + ", ".join(f"{v:.1f}:1" for v in rat)) if rat else "susunan sisi tidak lengkap"
            for s in sides:
                d.polyline(vis, [cs[s[0]]["c"], cs[s[1]]["c"]], G.GREEN if straight[s] else G.ORANGE, 2)
        for c in circles:
            d.dot(vis, c["c"], G.BLUE if c["ring"] else G.RED, 5)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3), G.criterion(4, ok4, det4)]
        return G.finish(C, vis, crits, "Six-circle triangle")


def _line_dist(p, a, b):
    L = G.dist(a, b) or 1.0
    return abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / L


def _seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy or 1.0
    t = max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return G.dist(p, (a[0] + t * vx, a[1] + t * vy))


if __name__ == "__main__":
    print(SixCircleTriangleChecker.check(sys.argv[1])[0], SixCircleTriangleChecker.last_criteria)
