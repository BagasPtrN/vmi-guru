"""Form 27 — Cincin tiga dimensi (Three-Dimensional Rings).
Kriteria manual:
  1. Tiga lingkaran bergaris ganda yang lengkap.
  2. Semua lingkaran saling bertumpuk.
  3. Minimal satu tumpang-tindih 3-D yang bersih (satu cincin lewat di atas cincin lain).
Cara ukur: celah sempit di antara garis ganda ("pita") dikumpulkan, lalu 3 lingkaran dicocokkan
pada garis tengah pita. Di titik silang, cincin yang pitanya tetap menyambung = cincin di atas.
"""
import sys
import math
import cv2
import numpy as np
from symbols import _vmi_geom as G


class ThreeDimensionalRingsChecker:
    BAND_MAX_REL = 0.07     # pita = bukaan yang lebarnya ≤ 7% ukuran gambar
    MIN_COVER = 0.6         # lingkaran 'lengkap': pita menutupi ≥ 60% kelilingnya
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
        H, _ = G.holes(d, close_rel=0.01, min_area_rel=0.0008)
        bands = [h for h in H if h["thick"] <= C.BAND_MAX_REL * d.size and h["per"] > 0.15 * d.size]
        lab = np.zeros(d.mask.shape, np.int32)
        pts = []
        for i, h in enumerate(bands):
            lab[h["mask"] > 0] = i + 1
            pts += G.skel_points(h["mask"])
        bw = float(np.median([h["thick"] for h in bands])) if bands else 0.0
        circ = G.ransac_circles(pts, 3, tol=max(3.0, 0.5 * (bw + d.stroke) + 1), iters=800, min_inl=int(0.3 * d.size), rmax=0.42 * d.size) if len(pts) > 30 else []
        full = [c for c in circ if c["cover"] >= C.MIN_COVER]
        ok1 = len(full) == 3 and len(bands) >= 3
        det1 = (f"{len(full)} cincin bergaris ganda yang lengkap (harus 3)" if bands else "garis tidak ganda (tidak ada pita)")
        # 2. saling bertumpuk
        ok2, det2 = False, "cincin kurang untuk dinilai"
        if len(circ) >= 3:
            c3 = circ[:3]
            pairs = [(i, j) for i in range(3) for j in range(i + 1, 3)]
            ov = [G.dist(c3[i]["c"], c3[j]["c"]) < (c3[i]["r"] + c3[j]["r"]) * 0.95 for i, j in pairs]
            ok2 = all(ov)
            det2 = f"{sum(ov)} dari 3 pasang cincin bertumpuk"
        # 3. tumpang-tindih 3-D
        ok3, det3 = False, "tidak ada persilangan yang dapat dinilai"
        clean = 0
        if len(circ) >= 2 and bw > 0:
            c3 = circ[:3]
            H_, W_ = lab.shape

            def L(p):
                x, y = int(round(p[0])), int(round(p[1]))
                return lab[y, x] if 0 <= y < H_ and 0 <= x < W_ else 0

            def continuous(c, X):
                a = math.atan2(X[1] - c["c"][1], X[0] - c["c"][0])
                da = 2.2 * (bw + 2 * d.stroke) / max(c["r"], 1)
                def lab_at(t):
                    seen = {}
                    for dr in np.arange(-bw, bw + 0.1, 1.0):
                        rr = c["r"] + dr
                        v = L((c["c"][0] + rr * math.cos(t), c["c"][1] + rr * math.sin(t)))
                        if v:
                            seen[v] = seen.get(v, 0) + 1
                    return set(seen)
                l1, l2 = lab_at(a - da), lab_at(a + da)
                return bool(l1 & l2)
            n_cross = 0
            for i in range(len(c3)):
                for j in range(i + 1, len(c3)):
                    for X in _circ_inter(c3[i], c3[j]):
                        n_cross += 1
                        a, b = continuous(c3[i], X), continuous(c3[j], X)
                        if a != b:
                            clean += 1
                            d.dot(vis, X, G.GREEN, 8)
                        else:
                            d.dot(vis, X, G.ORANGE, 6)
            ok3 = clean >= 1
            det3 = f"{clean} dari {n_cross} persilangan menunjukkan tumpang-tindih 3-D"
        for c in circ[:3]:
            cc = [(c["c"][0] + c["r"] * math.cos(t), c["c"][1] + c["r"] * math.sin(t)) for t in np.linspace(0, 6.3, 80)]
            d.polyline(vis, cc, G.GREEN if c["cover"] >= C.MIN_COVER else G.RED, 2)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)]
        return G.finish(C, vis, crits, "Three-dimensional rings")


def _circ_inter(A, B):
    (x0, y0), r0 = A["c"], A["r"]
    (x1, y1), r1 = B["c"], B["r"]
    dd = math.hypot(x1 - x0, y1 - y0)
    if dd == 0 or dd > r0 + r1 or dd < abs(r0 - r1):
        return []
    a = (r0 * r0 - r1 * r1 + dd * dd) / (2 * dd)
    h = math.sqrt(max(0.0, r0 * r0 - a * a))
    xm, ym = x0 + a * (x1 - x0) / dd, y0 + a * (y1 - y0) / dd
    return [(xm + h * (y1 - y0) / dd, ym - h * (x1 - x0) / dd), (xm - h * (y1 - y0) / dd, ym + h * (x1 - x0) / dd)]


if __name__ == "__main__":
    print(ThreeDimensionalRingsChecker.check(sys.argv[1])[0], ThreeDimensionalRingsChecker.last_criteria)
