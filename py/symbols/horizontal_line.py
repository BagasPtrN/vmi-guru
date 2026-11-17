"""Form 5 & 8 — Garis mendatar (Horizontal Line).
Kriteria manual:
  1. Lebih dari 1/2 garis berada dalam 30° dari horizontal.
"""
import sys
from symbols import _vmi_geom as G


class HorizontalLineChecker:
    TOL_DEG = 30.0        # toleransi dari horizontal (manual)
    MIN_FRACTION = 0.5    # "over 1/2 of line(s)"
    last_criteria = []

    @staticmethod
    def check(image_path):
        C = HorizontalLineChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 1)
        vis = img.copy()
        paths = [br.pts for br in d.graph.branches]
        ok_dir = lambda a: G.ang_diff(a, 0) <= C.TOL_DEG
        frac = G.fraction_within(paths, ok_dir)
        G.draw_dirs(d, vis, paths, ok_dir)
        crits = [G.criterion(1, frac > C.MIN_FRACTION, f"{frac * 100:.0f}% goresan dalam ±30° horizontal")]
        return G.finish(C, vis, crits, "Horizontal line")


if __name__ == "__main__":
    print(HorizontalLineChecker.check(sys.argv[1])[0], HorizontalLineChecker.last_criteria)
