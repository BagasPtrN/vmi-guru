"""Form 15 — Segitiga (Triangle).
Kriteria manual:
  1. Tiga sisi yang jelas.
  2. Satu sudut lebih tinggi dari yang lain (puncak di atas, tidak terbalik).
"""
import sys
from symbols import _vmi_geom as G


class TriangleChecker:
    N_SIDES = 3
    MIN_CORNER_TURN = 75.0 # tiap sudut harus benar-benar berbelok (bukan sekadar lengkungan)
    APEX_MARGIN = 0.15     # puncak minimal 15% tinggi bentuk di atas sudut tertinggi berikutnya
    last_criteria = []

    @staticmethod
    def check(image_path):
        C = TriangleChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 2)
        vis = img.copy()
        loop, _ = G.main_loop(d)
        if loop is None:
            for br in d.graph.branches:
                d.polyline(vis, br.pts, G.RED, 3)
            return G.finish(C, vis, [G.criterion(1, False, "bentuk tidak tertutup"),
                                     G.criterion(2, False, "tidak dapat dinilai")], "Triangle")
        V, peri = G.polygon(loop["cnt"], eps_rel=0.04, min_turn=35.0)
        sides = G.clear_sides(loop["cnt"], V)
        tv = G.corner_turns(V)
        ok1 = len(V) == C.N_SIDES and all(sd[0] for sd in sides) and min(tv) >= C.MIN_CORNER_TURN
        ys = sorted(v[1] for v in V)
        hgt = (ys[-1] - ys[0]) or 1.0
        margin = (ys[1] - ys[0]) / hgt if len(ys) >= 2 else 0.0
        ok2 = margin >= C.APEX_MARGIN
        d.polyline(vis, [tuple(p) for p in loop["cnt"].reshape(-1, 2)], (170, 170, 170), 2)
        for i in range(len(V)):
            d.polyline(vis, [V[i], V[(i + 1) % len(V)]], G.GREEN if ok1 else G.RED, 3)
            d.dot(vis, V[i], G.BLUE, 7)
        top = min(V, key=lambda v: v[1])
        d.dot(vis, top, G.GREEN if ok2 else G.RED, 11)
        if len(V) != C.N_SIDES:
            det1 = f"{len(V)} sisi jelas (harus 3)"
        elif min(tv) < C.MIN_CORNER_TURN:
            det1 = "sudut tidak jelas (bentuk melengkung)"
        elif not ok1:
            det1 = f"ada sisi melengkung (simpangan {max(sd[1] for sd in sides if not sd[0]) * 100:.0f}%)"
        else:
            det1 = "3 sisi jelas"
        crits = [G.criterion(1, ok1, det1),
                 G.criterion(2, ok2, f"puncak {margin * 100:.0f}% tinggi di atas sudut lain")]
        return G.finish(C, vis, crits, "Triangle")


if __name__ == "__main__":
    print(TriangleChecker.check(sys.argv[1])[0], TriangleChecker.last_criteria)
