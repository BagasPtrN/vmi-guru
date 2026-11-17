"""Form 29 — Kotak meruncing (Tapered Box).
Kriteria manual:
  1. Bentuk luar jajaran genjang (boleh persegi).
  2. Bentuk dalam persegi panjang mendatar.
  3. Bentuk dalam jelas bergeser ke kanan dan ke bawah (garis diagonal kanan-bawah paling pendek).
  4. Tidak ada kebingungan atau distorsi.
"""
import sys
import cv2
import numpy as np
from symbols import _vmi_geom as G


class TaperedBoxChecker:
    PARALLEL_TOL = 12.0
    INNER_TOL = 15.0
    INNER_ASPECT = 1.15
    SHIFT_REL = 0.03
    SPUR_REL = 0.07
    last_criteria = []

    @staticmethod
    def _order(V):
        cx, cy = sum(p[0] for p in V) / 4, sum(p[1] for p in V) / 4
        tl = min(V, key=lambda p: (p[0] - cx) + (p[1] - cy))
        br = max(V, key=lambda p: (p[0] - cx) + (p[1] - cy))
        tr = max(V, key=lambda p: (p[0] - cx) - (p[1] - cy))
        bl = min(V, key=lambda p: (p[0] - cx) - (p[1] - cy))
        return [tl, tr, br, bl]

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 4)
        vis = img.copy()
        oc = G.outer_contour(d)
        OV, _ = G.polygon(oc, eps_rel=0.03, min_side_rel=0.10, min_turn=35) if oc is not None else ([], 0)
        ok1, det1 = False, f"bentuk luar {len(OV)} sudut (harus 4)"
        if len(OV) == 4:
            O = C._order(OV)
            sa = [G.angle_deg(O[i], O[(i + 1) % 4]) for i in range(4)]
            p1, p2 = G.ang_diff(sa[0], sa[2]), G.ang_diff(sa[1], sa[3])
            ok1 = p1 <= C.PARALLEL_TOL and p2 <= C.PARALLEL_TOL
            det1 = f"sisi berhadapan beda arah {p1:.0f}° & {p2:.0f}° (maks 12°)"
        H, _ = G.holes(d, close_rel=0.015, min_area_rel=0.003)
        band = np.zeros(d.mask.shape, np.uint8)
        if oc is not None:
            cv2.drawContours(band, [oc], -1, 1, max(2, int(d.stroke)))
        gap = 2.5 * d.stroke + 3
        inner = [h for h in H if not G.touching(h["mask"], band, gap)]
        inner = max(inner, key=lambda h: h["area"]) if inner else None
        IV = G.polygon(inner["cnt"], eps_rel=0.05, min_side_rel=0.12, min_turn=40)[0] if inner is not None else []
        ok2, det2 = False, "bentuk dalam tidak ditemukan"
        if len(IV) == 4:
            I = C._order(IV)
            sa = [G.angle_deg(I[i], I[(i + 1) % 4]) for i in range(4)]
            dev = max(G.ang_diff(sa[0], 0), G.ang_diff(sa[2], 0), G.ang_diff(sa[1], 90), G.ang_diff(sa[3], 90))
            w = (G.dist(I[0], I[1]) + G.dist(I[3], I[2])) / 2
            h = (G.dist(I[1], I[2]) + G.dist(I[0], I[3])) / 2
            ok2 = dev <= C.INNER_TOL and w >= C.INNER_ASPECT * h
            det2 = f"bentuk dalam lebar:tinggi {w / max(h, 1):.2f}, sisi miring maks {dev:.0f}°"
        elif inner is not None:
            det2 = f"bentuk dalam {len(IV)} sudut (harus 4)"
        ok3, det3 = False, "tidak dapat dinilai"
        if len(OV) == 4 and len(IV) == 4:
            O, I = C._order(OV), C._order(IV)
            L = [G.dist(O[i], I[i]) for i in range(4)]
            oc_ = (sum(p[0] for p in O) / 4, sum(p[1] for p in O) / 4)
            ic_ = (sum(p[0] for p in I) / 4, sum(p[1] for p in I) / 4)
            W = max(p[0] for p in O) - min(p[0] for p in O)
            Hh = max(p[1] for p in O) - min(p[1] for p in O)
            dx, dy = (ic_[0] - oc_[0]) / W, (ic_[1] - oc_[1]) / Hh
            ok3 = L[2] == min(L) and dx >= C.SHIFT_REL and dy >= C.SHIFT_REL
            det3 = f"diagonal kanan-bawah {'paling pendek' if L[2] == min(L) else 'bukan yang terpendek'}; geser kanan {dx * 100:.0f}%, bawah {dy * 100:.0f}%"
            for i in range(4):
                d.polyline(vis, [O[i], I[i]], G.GREEN if (i != 2 or ok3) else G.RED, 3 if i == 2 else 2)
        spurs = [br for br in d.graph.branches if br.a is not None and
                 ((d.graph.kind[br.a] == "E") != (d.graph.kind[br.b] == "E")) and br.length > C.SPUR_REL * d.size]
        traps = [h for h in H if h is not inner]
        quad = sum(1 for h in traps if len(G.polygon(h["cnt"], eps_rel=0.03, min_side_rel=0.03, min_turn=25)[0]) in (4, 5))
        ok4 = len(H) == 5 and quad >= 3 and not spurs
        det4 = "tidak ada kebingungan" if ok4 else f"{len(H)} bukaan (harus 5), {quad} trapesium, {len(spurs)} garis kebablasan"
        if len(OV) == 4:
            d.polyline(vis, OV + OV[:1], G.GREEN if ok1 else G.RED, 3)
        if len(IV) >= 3:
            d.polyline(vis, IV + IV[:1], G.GREEN if ok2 else G.RED, 3)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3), G.criterion(4, ok4, det4)]
        return G.finish(C, vis, crits, "Tapered box")


if __name__ == "__main__":
    print(TaperedBoxChecker.check(sys.argv[1])[0], TaperedBoxChecker.last_criteria)
