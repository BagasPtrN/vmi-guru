"""Form 23 — Segitiga miring (Tilted Triangles).
Kriteria manual:
  1. Dua segitiga.
  2. Dua sudut segitiga dalam menyentuh rapi 1/3 tengah sisi segitiga luar; sudut ketiga
     dalam 1/16 inci dari menyentuh (boleh kurang atau lebih).
  3. Sudut kiri segitiga luar 60°–120°.
  4. Sisi kanan segitiga luar miring 100° atau lebih.
"""
import sys
import math
from symbols import _vmi_geom as G


class TiltedTrianglesChecker:
    TOUCH_REL = 0.035      # menyentuh rapi: ≤ 3,5% ukuran gambar dari sisi luar
    NEAR_REL = 0.06        # ≤ 1/16 inci ≈ 6% ukuran gambar
    LEFT_ANGLE = (60.0, 120.0)
    RIGHT_SLOPE_MIN = 100.0
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
        oc = G.outer_contour(d)
        OV, _ = G.polygon(oc, eps_rel=0.04, min_side_rel=0.12, min_turn=40) if oc is not None else ([], 0)
        outer_ok = len(OV) == 3
        H, _ = G.holes(d, close_rel=0.015, min_area_rel=0.004)
        inner, IV = None, None
        if outer_ok:
            cen = (sum(p[0] for p in OV) / 3, sum(p[1] for p in OV) / 3)
            for h in sorted(H, key=lambda h: G.dist(h["center"], cen)):
                V, _ = G.polygon(h["cnt"], eps_rel=0.05, min_side_rel=0.12, min_turn=40)
                if len(V) == 3:
                    # sudut segitiga dalam tidak boleh berimpit dengan sudut segitiga luar
                    if min(G.dist(v, o) for v in V for o in OV) > 0.08 * d.size:
                        inner, IV = h, V
                        break
        ok1 = outer_ok and inner is not None and len(H) >= 3
        det1 = "dua segitiga" if ok1 else ("segitiga luar tidak jelas" if not outer_ok else "segitiga dalam tidak ditemukan")
        # 2. sentuhan sudut segitiga dalam
        ok2, det2 = False, "tidak dapat dinilai"
        if outer_ok and IV is not None:
            ic = (sum(p[0] for p in IV) / 3, sum(p[1] for p in IV) / 3)
            sides = [(OV[i], OV[(i + 1) % 3]) for i in range(3)]
            info = []
            for v in IV:
                u = G.unit((v[0] - ic[0], v[1] - ic[1]))
                tipv = (v[0] + u[0] * d.stroke, v[1] + u[1] * d.stroke)
                best = None
                for a, b in sides:
                    vx, vy = b[0] - a[0], b[1] - a[1]
                    L2 = vx * vx + vy * vy
                    t = ((tipv[0] - a[0]) * vx + (tipv[1] - a[1]) * vy) / L2
                    q = (a[0] + max(0, min(1, t)) * vx, a[1] + max(0, min(1, t)) * vy)
                    dd = G.dist(tipv, q) - d.stroke
                    if best is None or dd < best[0]:
                        best = (dd, t)
                info.append(best)
            clean = [i for i in info if i[0] <= C.TOUCH_REL * d.size and 1 / 3 - 0.04 <= i[1] <= 2 / 3 + 0.04]
            near = [i for i in info if i[0] <= C.NEAR_REL * d.size]
            ok2 = len(clean) >= 2 and len(near) == 3
            det2 = f"{len(clean)} sudut menyentuh 1/3 tengah sisi, {len(near)} dari 3 sudut menyentuh/dekat"
            d.polyline(vis, IV + [IV[0]], G.GREEN if ok2 else G.RED, 3)
        # 3 & 4. sudut kiri & kemiringan sisi kanan segitiga luar
        ok3 = ok4 = False
        det3 = det4 = "segitiga luar tidak jelas"
        if outer_ok:
            iang = G.interior_angles(OV)
            k = min(range(3), key=lambda i: OV[i][0])
            ok3 = C.LEFT_ANGLE[0] <= iang[k] <= C.LEFT_ANGLE[1]
            det3 = f"sudut kiri {iang[k]:.0f}° (60°–120°)"
            a, b = [OV[i] for i in range(3) if i != k]
            slope = G.angle_deg(a, b)
            ok4 = C.RIGHT_SLOPE_MIN <= slope < 180
            det4 = f"sisi kanan miring {slope:.0f}° (min 100°)"
            d.polyline(vis, OV + [OV[0]], G.GREEN if ok3 else G.ORANGE, 3)
            d.polyline(vis, [a, b], G.GREEN if ok4 else G.RED, 4)
            d.dot(vis, OV[k], G.GREEN if ok3 else G.RED, 9)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3), G.criterion(4, ok4, det4)]
        return G.finish(C, vis, crits, "Tilted triangles")


if __name__ == "__main__":
    print(TiltedTrianglesChecker.check(sys.argv[1])[0], TiltedTrianglesChecker.last_criteria)
