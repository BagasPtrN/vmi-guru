"""Form 19 — Cincin dua dimensi (Two-Dimensional Rings).
Kriteria manual:
  1. Tiga lingkaran bertumpuk yang membentuk tujuh bukaan; bukaan segitiga di tengah harus tampak.
  2. Satu lingkaran jelas berada di bawah yang lain (hubungkan titik tengah ketiga lingkaran menjadi
     segitiga; sisi terbawah segitiga harus miring ≥ 20° dari horizontal).
"""
import sys
import math
from symbols import _vmi_geom as G


class TwoDimensionalRingsChecker:
    N_OPENINGS = 7
    MIN_LOW_SIDE_DEG = 20.0
    last_criteria = []

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 2)
        vis = img.copy()
        H, _ = G.holes(d, close_rel=0.02, min_area_rel=0.004)
        n = len(H)
        allc = (sum(h["center"][0] for h in H) / n, sum(h["center"][1] for h in H) / n) if n else (0, 0)
        center = min(H, key=lambda h: G.dist(h["center"], allc)) if H else None
        tri = False
        if center is not None:
            # bukaan segitiga tengah: bukaan pusat yang berbatasan (dipisah satu garis) dengan ≥ 3 bukaan lain
            nb = sum(G.touching(center["mask"], h["mask"], 2.5 * d.stroke + 2) for h in H if h is not center)
            tri = nb >= 3 and center["area"] < 0.6 * max(h["area"] for h in H)
        # Cara 2 (lebih tahan garis yang tidak tertutup rapat): cocokkan 3 lingkaran pada goresan,
        # lalu hitung daerah-daerah Venn yang terbentuk secara geometris.
        circ = G.ransac_circles([q for br in d.graph.branches for q in br.pts], 3, tol=max(3.0, 0.03 * d.size),
                                min_inl=int(0.25 * d.size))
        circ = [c for c in circ if c["cover"] >= 0.55]
        venn_ok, venn_det = False, ""
        if len(circ) == 3:
            import numpy as np
            xs = np.linspace(0, d.mask.shape[1], 120); ys = np.linspace(0, d.mask.shape[0], 120)
            X, Y = np.meshgrid(xs, ys)
            code = sum(((np.hypot(X - c["c"][0], Y - c["c"][1]) < c["r"]).astype(int) << k) for k, c in enumerate(circ))
            tot = (code > 0).sum() or 1
            areas = [(code == k).sum() / tot for k in range(1, 8)]
            venn_ok = min(areas) >= 0.008
            venn_det = f"; dari 3 lingkaran: {sum(a >= 0.008 for a in areas)} daerah, tengah {areas[6] * 100:.0f}%"
            for c in circ:
                cv_ = [(c["c"][0] + c["r"] * G.math.cos(t), c["c"][1] + c["r"] * G.math.sin(t)) for t in np.linspace(0, 6.3, 60)]
                d.polyline(vis, cv_, G.BLUE, 1)
        ok1 = (n == C.N_OPENINGS and tri) or venn_ok
        det1 = f"{n} bukaan tertutup" + ("" if tri else ", bukaan tengah tidak tampak") + venn_det
        if len(circ) == 3:
            H_centers = [c["c"] for c in circ]
        else:
            H_centers = None
        # 2. posisi: tiga bukaan terluar (milik satu lingkaran saja) ~ arah pusat tiap lingkaran
        ok2, det2 = False, "posisi lingkaran tidak dapat diukur"
        P = None
        if H_centers is not None:
            P = H_centers
        elif n >= 3:
            outer = sorted(H, key=lambda h: -h["area"] * (1 + G.dist(h["center"], allc) / d.size))[:3]
            P = [h["center"] for h in outer]
        if P is not None:
            sides = [(P[i], P[(i + 1) % 3]) for i in range(3)]
            low = max(sides, key=lambda s: (s[0][1] + s[1][1]) / 2)
            ang = G.ang_diff(G.angle_deg(low[0], low[1]), 0)
            ok2 = ang >= C.MIN_LOW_SIDE_DEG
            det2 = f"sisi terbawah segitiga pusat miring {ang:.0f}° (min 20°)"
            d.polyline(vis, P + [P[0]], G.GREEN if ok2 else G.RED, 2)
            d.polyline(vis, [low[0], low[1]], G.BLUE, 3)
        for h in H:
            col = G.GREEN if ok1 else G.ORANGE
            d.polyline(vis, [tuple(p) for p in h["cnt"].reshape(-1, 2)] + [tuple(h["cnt"][0][0])], col, 2)
        if center is not None:
            d.dot(vis, center["center"], G.GREEN if tri else G.RED, 7)
        return G.finish(C, vis, [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2)], "Two-dimensional rings")


if __name__ == "__main__":
    print(TwoDimensionalRingsChecker.check(sys.argv[1])[0], TwoDimensionalRingsChecker.last_criteria)
