"""Form 6 & 9 — Lingkaran (Circle).
Kriteria manual:
  1. Ada lengkung (loop) dengan perbandingan tinggi : lebar tidak lebih dari 2 : 1.
Lengkung = lubang tertutup pada goresan, atau goresan yang berputar hampir penuh
(≥ 300°) walau ujungnya belum bertemu.
"""
import sys
import cv2
import numpy as np
from symbols import _vmi_geom as G


class CircleChecker:
    MAX_RATIO = 2.0         # manual: no more than 2 to 1
    MIN_LOOP_REL = 0.25     # lengkung minimal 25% ukuran gambar (abaikan celah kecil antar coretan)
    MIN_TURN_DEG = 300.0    # goresan terbuka yang berputar ≥ 300° dianggap lengkung
    last_criteria = []

    @staticmethod
    def check(image_path):
        C = CircleChecker
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 1)
        vis = img.copy()
        cands = []  # (rasio, titik-titik kerja, jenis)
        k = max(3, int(0.02 * d.size)) | 1
        m = cv2.morphologyEx(d.mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        for L in G.loops(m, min_rel=C.MIN_LOOP_REL):
            rw, rh = L["rw"] + d.stroke, L["rh"] + d.stroke
            cands.append((max(rw, rh) / min(rw, rh), L["cnt"].reshape(-1, 2), "tertutup"))
        for s in G.strokes(d.graph, merge_r=max(6.0, 2.5 * d.stroke)):
            if len(s.pts) > 10 and abs(G.total_turning(s.pts)) >= C.MIN_TURN_DEG:
                pts = np.array(s.pts, np.float32)
                (cx, cy), (rw, rh), _ = cv2.minAreaRect(pts)
                if max(rw, rh) >= C.MIN_LOOP_REL * d.size and min(rw, rh) > 1:
                    cands.append((max(rw, rh) / min(rw, rh), pts, "hampir tertutup"))
        best = min(cands, key=lambda c: c[0]) if cands else None
        for ratio, pts, kind in cands:
            col = G.GREEN if ratio <= C.MAX_RATIO else G.RED
            d.polyline(vis, [tuple(p) for p in pts] + [tuple(pts[0])], col, 3)
            box = cv2.boxPoints(cv2.minAreaRect(np.array(pts, np.float32)))
            d.polyline(vis, [tuple(p) for p in box] + [tuple(box[0])], G.ORANGE, 1)
        if best is None:
            crit = G.criterion(1, False, "tidak ada lengkung (loop)")
            for br in d.graph.branches:
                d.polyline(vis, br.pts, G.RED, 3)
        else:
            crit = G.criterion(1, best[0] <= C.MAX_RATIO, f"lengkung {best[2]}, rasio {best[0]:.2f} : 1")
        return G.finish(C, vis, [crit], "Circle")


if __name__ == "__main__":
    print(CircleChecker.check(sys.argv[1])[0], CircleChecker.last_criteria)
