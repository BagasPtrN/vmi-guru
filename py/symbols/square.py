"""Form 12 — Persegi (Square).
Kriteria manual:
  1. Empat sisi yang jelas (sudut tidak harus lancip).
Diukur pada lengkung tertutup terbesar: disederhanakan menjadi sudut-sudut yang jelas
(sudut bulat digabung), harus tepat 4 sisi, dan tiap sisi cukup lurus.
"""
import sys
from symbols import _vmi_geom as G


class SquareChecker:
    N_SIDES = 4
    last_criteria = []

    @staticmethod
    def check(image_path):
        C = SquareChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 1)
        vis = img.copy()
        loop, _ = G.main_loop(d)
        if loop is None:
            for br in d.graph.branches:
                d.polyline(vis, br.pts, G.RED, 3)
            return G.finish(C, vis, [G.criterion(1, False, "bentuk tidak tertutup")], "Square")
        V, peri = G.polygon(loop["cnt"])
        sides = G.clear_sides(loop["cnt"], V)
        ok_n = len(V) == C.N_SIDES
        ok_straight = ok_n and all(sd[0] for sd in sides)
        d.polyline(vis, [tuple(p) for p in loop["cnt"].reshape(-1, 2)], (170, 170, 170), 2)
        for i in range(len(V)):
            col = G.GREEN if (ok_n and sides[i][0]) else G.RED
            d.polyline(vis, [V[i], V[(i + 1) % len(V)]], col, 3)
            d.dot(vis, V[i], G.BLUE, 7)
        if not ok_n:
            det = f"{len(V)} sisi jelas (harus 4)"
        elif not ok_straight:
            det = f"ada sisi melengkung (simpangan {max(sd[1] for sd in sides if not sd[0]) * 100:.0f}% panjang sisi)"
        else:
            det = "4 sisi jelas"
        return G.finish(C, vis, [G.criterion(1, ok_n and ok_straight, det)], "Square")


if __name__ == "__main__":
    print(SquareChecker.check(sys.argv[1])[0], SquareChecker.last_criteria)
