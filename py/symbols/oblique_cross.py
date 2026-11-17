"""Form 14 — Silang miring (Oblique Cross).
Kriteria manual:
  1. Dua garis berpotongan.
  2. Garis membentuk sudut antara 20°–70° dan antara 110°–160°.
  3. Kaki terpanjang (tanpa perpanjangan) tidak lebih dari 2× kaki terpendek.
"""
import sys
from symbols import _vmi_geom as G
from symbols import _cross as X


class ObliqueCrossChecker:
    RANGE_A = (20.0, 70.0)
    RANGE_B = (110.0, 160.0)
    MAX_LEG_RATIO = 2.0
    last_criteria = []

    @staticmethod
    def check(image_path):
        C = ObliqueCrossChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 3)
        vis = img.copy()
        T = X.two_lines(d, C)
        lines = T["lines"]
        # 2. sudut garis
        if len(lines) == 2:
            a1, a2 = lines[0].angle, lines[1].angle
            inA = lambda a: C.RANGE_A[0] <= a <= C.RANGE_A[1]
            inB = lambda a: C.RANGE_B[0] <= a <= C.RANGE_B[1]
            ok2 = (inA(a1) and inB(a2)) or (inA(a2) and inB(a1))
            det2 = f"sudut garis {min(a1, a2):.0f}° dan {max(a1, a2):.0f}°"
        else:
            ok2, det2 = False, "garis kurang"
        # 3. rasio kaki
        if len(T["legs"]) == 4:
            Ls = [l.length for l in T["legs"]]
            ratio = max(Ls) / max(1e-6, min(Ls))
            ok3, det3 = ratio <= C.MAX_LEG_RATIO, f"kaki terpanjang {ratio:.1f}× kaki terpendek"
        else:
            ok3, det3 = False, "kaki tidak dapat diukur (garis tidak berpotongan)"
        X.draw_extra(d, vis, T["R"], lines)
        ok_ang = lambda a: (C.RANGE_A[0] <= a <= C.RANGE_A[1]) or (C.RANGE_B[0] <= a <= C.RANGE_B[1])
        X.draw_lines(d, vis, lines, ok_ang)
        if T["p"] is not None:
            d.dot(vis, T["p"], G.BLUE, 8)
            for leg in T["legs"]:
                d.dot(vis, leg.tip, G.PURPLE, 6)
        crits = [G.criterion(1, T["ok"], T["det"]), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)]
        return G.finish(C, vis, crits, "Oblique cross")


if __name__ == "__main__":
    print(ObliqueCrossChecker.check(sys.argv[1])[0], ObliqueCrossChecker.last_criteria)
