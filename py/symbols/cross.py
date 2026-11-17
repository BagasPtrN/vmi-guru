"""Form 10 — Silang tegak-mendatar (Vertical-Horizontal Cross).
Kriteria manual:
  1. Dua garis berpotongan.
  2. Keempat "kaki" minimal 1/4 inci (tanpa perpanjangan).
  3. Minimal 1/2 tiap garis berada dalam 20° dari sudut yang benar.
"""
import sys
from symbols import _vmi_geom as G
from symbols import _cross as X


class CrossChecker:
    ANGLE_TOL = 20.0
    last_criteria = []

    @staticmethod
    def evaluate(d, vis):
        T = X.two_lines(d, CrossChecker)
        ok2, det2 = X.legs_long_enough(T["legs"], d)
        ok3, det3, roles = X.hv_within(T["lines"], CrossChecker.ANGLE_TOL)
        X.draw_extra(d, vis, T["R"], T["lines"])
        for i, l in enumerate(T["lines"]):
            tgt = 0 if (roles and roles[i] == 0) else 90
            G.draw_dirs(d, vis, [l.pts], lambda a, t=tgt: G.ang_diff(a, t) <= CrossChecker.ANGLE_TOL)
        if T["p"] is not None:
            d.dot(vis, T["p"], G.BLUE, 8)
            for leg in T["legs"]:
                d.dot(vis, leg.tip, G.PURPLE, 6)
        return [G.criterion(1, T["ok"], T["det"]), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)], T

    @staticmethod
    def check(image_path):
        C = CrossChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 3)
        vis = img.copy()
        crits, _ = C.evaluate(d, vis)
        return G.finish(C, vis, crits, "Vertical-horizontal cross")


if __name__ == "__main__":
    print(CrossChecker.check(sys.argv[1])[0], CrossChecker.last_criteria)
