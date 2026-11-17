"""Form 17 — Silang tiga garis (Three-Line Cross).
Kriteria manual:
  1. Tiga garis yang saling berpotongan.
  2. Celah di titik potong tingginya tidak lebih dari 1/8 inci.
  3. Lebih dari 1/2 garis mendatar berada dalam 15° dari horizontal.
  4. Lebih dari 1/2 kedua garis diagonal berjarak lebih dari 10° dari vertikal.
"""
import sys
import itertools
from symbols import _vmi_geom as G
from symbols import _cross as X


class ThreeLineCrossChecker:
    EXTRA_MAX = 0.18
    GAP_REL = 0.075         # 1/8 inci ≈ 7,5% lebar gambar (asumsi lebar bentuk ±1,7 inci)
    MAX_BEND = 35.0         # garis yang bengkok tajam (> 35°) tidak dihitung sebagai satu garis
    H_TOL = 15.0
    DIAG_FROM_V = 10.0
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
        R = G.cross_lines(d, 3)
        lines, inter = R["lines"], R["inter"]
        # 1. tiga garis saling berpotongan
        if len(lines) < 3:
            ok1, det1 = False, f"hanya {len(lines)} garis panjang"
        elif len(inter) < 3:
            ok1, det1 = False, f"hanya {len(inter)} dari 3 pasang garis yang berpotongan"
        elif max(G.max_bend(l.pts) for l in lines) > C.MAX_BEND:
            ok1, det1 = False, f"ada garis yang bengkok tajam ({max(G.max_bend(l.pts) for l in lines):.0f}°)"
        elif R["n_long"] > 3 or R["extra"] > C.EXTRA_MAX:
            ok1, det1 = False, f"ada goresan tambahan ({R['extra'] * 100:.0f}%)"
        else:
            ok1, det1 = True, "tiga garis saling berpotongan"
        # 2. celah titik potong (tinggi)
        FI = G.fitted_intersections(lines) if len(lines) == 3 else {}
        if len(FI) == 3:
            ys = [p[1] for p in FI.values()]
            gap = (max(ys) - min(ys)) / max(1.0, d.ink_w)
            ok2 = gap <= C.GAP_REL
            det2 = f"celah titik potong {gap * 100:.0f}% lebar gambar (maks {C.GAP_REL * 100:.0f}%)"
        else:
            ok2, det2 = False, "titik potong tidak cukup untuk diukur"
        # 3 & 4. garis mendatar & diagonal
        ok3 = ok4 = False
        det3 = det4 = "garis kurang"
        if len(lines) >= 3:
            h = min(range(3), key=lambda i: G.ang_diff(lines[i].angle, 0))
            fh = G.fraction_within([lines[h].pts], lambda a: G.ang_diff(a, 0) <= C.H_TOL)
            dh = G.ang_diff(lines[h].angle, 0)
            ok3 = fh > 0.5 or dh <= C.H_TOL + X.MEASURE_TOL
            det3 = f"garis mendatar miring {dh:.0f}° ({fh * 100:.0f}% dalam ±{C.H_TOL:.0f}°)"
            diags = [i for i in range(3) if i != h]
            fd = [G.fraction_within([lines[i].pts], lambda a: G.ang_diff(a, 90) > C.DIAG_FROM_V) for i in diags]
            ok4 = all(f > 0.5 for f in fd)
            det4 = "diagonal: " + ", ".join(f"{f * 100:.0f}%" for f in fd) + f" bagian > {C.DIAG_FROM_V:.0f}° dari vertikal"
            G.draw_dirs(d, vis, [lines[h].pts], lambda a: G.ang_diff(a, 0) <= C.H_TOL)
            G.draw_dirs(d, vis, [lines[i].pts for i in diags], lambda a: G.ang_diff(a, 90) > C.DIAG_FROM_V)
        else:
            X.draw_lines(d, vis, lines, col=G.RED)
        X.draw_extra(d, vis, R, lines)
        for p in FI.values():
            d.dot(vis, p, G.BLUE if ok2 else G.RED, 6)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2),
                 G.criterion(3, ok3, det3), G.criterion(4, ok4, det4)]
        return G.finish(C, vis, crits, "Three-line cross")


if __name__ == "__main__":
    print(ThreeLineCrossChecker.check(sys.argv[1])[0], ThreeLineCrossChecker.last_criteria)
