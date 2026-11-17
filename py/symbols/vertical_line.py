"""Form 4 & 7 — Garis tegak (Vertical Line).
Kriteria manual:
  1. Lebih dari 1/2 garis berada dalam 30° dari vertikal.
"""
import sys
from symbols import _vmi_geom as G


class VerticalLineChecker:
    TOL_DEG = 30.0        # toleransi dari vertikal (manual)
    MIN_FRACTION = 0.5    # "over 1/2 of line(s)"
    last_criteria = []

    @staticmethod
    def check(image_path):
        C = VerticalLineChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 1)
        vis = img.copy()
        paths = [br.pts for br in d.graph.branches]
        ok_dir = lambda a: G.ang_diff(a, 90) <= C.TOL_DEG
        frac = G.fraction_within(paths, ok_dir)
        G.draw_dirs(d, vis, paths, ok_dir)
        crits = [G.criterion(1, frac > C.MIN_FRACTION, f"{frac * 100:.0f}% goresan dalam ±30° vertikal")]
        return G.finish(C, vis, crits, "Vertical line")


if __name__ == "__main__":
    print(VerticalLineChecker.check(sys.argv[1])[0], VerticalLineChecker.last_criteria)
