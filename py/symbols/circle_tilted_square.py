"""Form 21 — Lingkaran dan persegi miring (Circle and Tilted Square).
Kriteria manual:
  1. Persegi bersudut empat dan sebuah lingkaran.
  2. Sudut-sudut yang berhadapan dalam 10° dari vertikal dan horizontal.
  3. Persegi "menyentuh" lingkaran dengan sudut yang tertutup.
  4. Celah atau tumpang-tindih antar-bentuk tidak lebih dari 1/16 inci.
  5. Titik sentuh sudut berada di 1/3 tengah lingkaran.
  6. Tinggi lingkaran dan persegi tidak lebih dari 2 : 1.
"""
import sys
import math
from symbols import _vmi_geom as G


class CircleTiltedSquareChecker:
    AXIS_TOL = 10.0
    JOIN_REL = 0.08        # 1/16 inci ≈ 8% tinggi persegi (asumsi tinggi ±0,8 inci)
    HEIGHT_RATIO = 2.0
    MIN_CIRC = 0.70        # kebulatan lingkaran (4πA/P²)
    last_criteria = []

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 6)
        vis = img.copy()
        H, _ = G.holes(d, close_rel=0.015, min_area_rel=0.02)
        cands = H[:3]
        circle = sq = None
        sqV = None
        for h in cands:
            V, _ = G.polygon(h["cnt"], eps_rel=0.03, min_side_rel=0.12, min_turn=35)
            sides = G.clear_sides(h["cnt"], V) if len(V) == 4 else []
            is_sq = len(V) == 4 and all(sd[0] for sd in sides) and min(G.corner_turns(V)) >= 55
            if is_sq and sq is None:
                sq, sqV = h, V
            elif h["circ"] >= C.MIN_CIRC and circle is None:
                circle = h
        ok1 = circle is not None and sq is not None
        det1 = ("persegi 4 sudut dan lingkaran" if ok1 else
                ("lingkaran tidak ditemukan" if circle is None else "") + ("; " if circle is None and sq is None else "") +
                ("persegi 4 sudut tidak ditemukan" if sq is None else ""))
        crits = [G.criterion(1, ok1, det1)]
        if not ok1:
            for h in H[:3]:
                d.polyline(vis, [tuple(p) for p in h["cnt"].reshape(-1, 2)], G.RED, 2)
            crits += [G.criterion(k, False, "tidak dapat dinilai") for k in range(2, 7)]
            return G.finish(C, vis, crits, "Circle and tilted square")
        # lingkaran: pusat & jari-jari garis tengah goresan
        cc = circle["center"]
        R = math.sqrt(circle["area"] / math.pi) + d.stroke / 2
        # 2. diagonal persegi
        top, bot = min(sqV, key=lambda p: p[1]), max(sqV, key=lambda p: p[1])
        lef, rig = min(sqV, key=lambda p: p[0]), max(sqV, key=lambda p: p[0])
        dv = G.ang_diff(G.angle_deg(top, bot), 90)
        dh = G.ang_diff(G.angle_deg(lef, rig), 0)
        ok2 = dv <= C.AXIS_TOL and dh <= C.AXIS_TOL and len({top, bot, lef, rig}) == 4
        det2 = f"diagonal tegak miring {dv:.0f}°, mendatar miring {dh:.0f}° (maks 10°)"
        # sudut persegi yang menghadap lingkaran → ujung garis (pusat goresan)
        k = min(range(4), key=lambda i: G.dist(sqV[i], cc))
        P0 = sqV[k]
        ang_in = 180 - G.corner_turns(sqV)[k]
        bis = G.unit((P0[0] - sum(p[0] for p in sqV) / 4, P0[1] - sum(p[1] for p in sqV) / 4))
        off = (d.stroke / 2) / max(0.2, math.sin(math.radians(ang_in) / 2))
        tip = (P0[0] + bis[0] * off, P0[1] + bis[1] * off)
        sq_h = (bot[1] - top[1]) + d.stroke
        sep = G.dist(tip, cc) - R
        # 3. menyentuh dengan sudut tertutup: sudut itu adalah sudut nyata persegi (tidak membulat)
        closed = ang_in <= 120 and abs(sep) <= 3 * C.JOIN_REL * sq_h
        ok3 = closed
        det3 = "sudut persegi tertutup & menyentuh lingkaran" if ok3 else \
               ("sudut persegi tidak menghadap/menyentuh lingkaran" if abs(sep) > 3 * C.JOIN_REL * sq_h else "sudut kontak membulat/terbuka")
        # 4. celah / tumpang-tindih
        ok4 = abs(sep) <= C.JOIN_REL * sq_h
        det4 = (f"celah {sep / sq_h * 100:.0f}%" if sep > 0 else f"tumpang-tindih {-sep / sq_h * 100:.0f}%") + \
               f" tinggi persegi (maks {C.JOIN_REL * 100:.0f}%)"
        # 5. titik sentuh di 1/3 tengah lingkaran (arah vertikal)
        rel = (tip[1] - cc[1]) / R
        ok5 = abs(rel) <= 1 / 3
        det5 = f"titik sentuh {abs(rel) * 100:.0f}% jari-jari dari tengah (maks 33%)"
        # 6. tinggi
        hr = (2 * R) / max(1.0, sq_h)
        ok6 = 1 / C.HEIGHT_RATIO <= hr <= C.HEIGHT_RATIO
        det6 = f"tinggi lingkaran : persegi = {hr:.2f} : 1"
        # visual
        d.polyline(vis, [tuple(p) for p in circle["cnt"].reshape(-1, 2)] + [tuple(circle["cnt"][0][0])], G.GREEN, 2)
        for i in range(4):
            d.polyline(vis, [sqV[i], sqV[(i + 1) % 4]], G.GREEN if ok2 else G.ORANGE, 3)
        d.polyline(vis, [top, bot], G.GREEN if dv <= C.AXIS_TOL else G.RED, 1)
        d.polyline(vis, [lef, rig], G.GREEN if dh <= C.AXIS_TOL else G.RED, 1)
        d.dot(vis, tip, G.BLUE if ok4 else G.RED, 7)
        d.polyline(vis, [(cc[0] - R, cc[1] - R / 3), (cc[0] + R, cc[1] - R / 3)], G.PURPLE, 1)
        d.polyline(vis, [(cc[0] - R, cc[1] + R / 3), (cc[0] + R, cc[1] + R / 3)], G.PURPLE, 1)
        crits += [G.criterion(2, ok2, det2), G.criterion(3, ok3, det3), G.criterion(4, ok4, det4),
                  G.criterion(5, ok5, det5), G.criterion(6, ok6, det6)]
        return G.finish(C, vis, crits, "Circle and tilted square")


if __name__ == "__main__":
    print(CircleTiltedSquareChecker.check(sys.argv[1])[0], CircleTiltedSquareChecker.last_criteria)
