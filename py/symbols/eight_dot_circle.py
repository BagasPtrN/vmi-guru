"""Form 24 — Lingkaran delapan titik (Eight-Dot Circle).
Kriteria manual:
  1. Delapan titik, lingkaran kecil, atau garis pendek.
  2. Kebulatan: tidak ada tiga titik berurutan yang segaris.
  3. Jarak: jarak terbesar antara dua titik bersebelahan tidak lebih dari 2× jarak terkecil.
"""
import sys
import math
from symbols import _vmi_geom as G


class EightDotCircleChecker:
    N = 8
    COLLINEAR_REL = 0.05    # titik tengah menyimpang < 5% panjang tali busur = segaris
    SPACE_RATIO = 2.0
    last_criteria = []

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 3)
        vis = img.copy()
        comps = G.components(d, min_rel_area=0.08)
        P = [c["center"] for c in comps]
        n = len(P)
        ok1, det1 = n == C.N, f"{n} titik (harus 8)"
        ok2 = ok3 = False
        det2 = det3 = "titik kurang untuk dinilai"
        if n >= 4:
            cx, cy = sum(p[0] for p in P) / n, sum(p[1] for p in P) / n
            P = sorted(P, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
            lines = []
            for i in range(n):
                a, m, b = P[i - 1], P[i], P[(i + 1) % n]
                ch = G.dist(a, b) or 1.0
                dev = abs((b[0] - a[0]) * (a[1] - m[1]) - (a[0] - m[0]) * (b[1] - a[1])) / ch / ch
                if dev < C.COLLINEAR_REL:
                    lines.append((a, m, b))
            ok2 = not lines
            det2 = "tidak ada tiga titik segaris" if ok2 else f"{len(lines)} kelompok tiga titik segaris"
            gaps = [G.dist(P[i], P[(i + 1) % n]) for i in range(n)]
            rr = max(gaps) / max(1e-6, min(gaps))
            ok3, det3 = rr <= C.SPACE_RATIO, f"jarak terbesar {rr:.1f}× jarak terkecil"
            d.polyline(vis, P + [P[0]], G.GREEN if ok3 else G.ORANGE, 1)
            for a, m, b in lines:
                d.polyline(vis, [a, b], G.RED, 3)
        for p in P:
            d.dot(vis, p, G.BLUE, 6)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)]
        return G.finish(C, vis, crits, "Eight-dot circle")


if __name__ == "__main__":
    print(EightDotCircleChecker.check(sys.argv[1])[0], EightDotCircleChecker.last_criteria)
