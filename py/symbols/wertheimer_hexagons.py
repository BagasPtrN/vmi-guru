"""Form 25 — Segi enam Wertheimer (Wertheimer's Hexagons).
Kriteria manual:
  1. Semua sisi tergambar (salah satu sudut paling tumpul boleh membulat).
  2. Tidak ada tanda kebingungan arah di sudut-sudut.
  3. Tumpang-tindih jelas terlihat, tetapi tidak berlebihan.
"""
import sys
import cv2
import numpy as np
from symbols import _vmi_geom as G


class WertheimerHexagonsChecker:
    CORNERS = (5, 6)          # 6 sudut; 5 bila satu sudut tumpul membulat
    SPUR_REL = 0.07           # ujung garis kebablasan > 7% ukuran = kebingungan arah
    OVERLAP = (0.04, 0.60)    # luas tumpang-tindih / luas segi enam terkecil
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
        H, m = G.holes(d, close_rel=0.015, min_area_rel=0.003)
        gap = 2.5 * d.stroke + 3
        hexes, ov = [], None
        if len(H) >= 3:
            top3 = H[:3]
            # daerah tumpang-tindih = bukaan yang berada di tengah dua bukaan lainnya
            ov = min(top3, key=lambda h: sum(G.dist(h["center"], o["center"]) for o in top3 if o is not h))
            if sum(G.touching(ov["mask"], o["mask"], gap) for o in top3 if o is not ov) < 2:
                ov = None
        if ov is not None:
            others = [h for h in H[:3] if h is not ov]
            for h in others:
                reg = cv2.dilate(h["mask"] | ov["mask"], np.ones((int(d.stroke) * 2 + 3,) * 2, np.uint8))
                reg = cv2.morphologyEx(reg, cv2.MORPH_CLOSE, np.ones((int(d.stroke) * 3 + 3,) * 2, np.uint8))
                cs, _ = cv2.findContours(reg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cnt = max(cs, key=cv2.contourArea)
                V, _ = G.polygon(cnt, eps_rel=0.025, min_side_rel=0.07, min_turn=22)
                hexes.append({"cnt": cnt, "V": V, "area": h["area"] + ov["area"]})
        elif len(H) >= 2:
            for h in H[:2]:
                V, _ = G.polygon(h["cnt"], eps_rel=0.025, min_side_rel=0.07, min_turn=22)
                hexes.append({"cnt": h["cnt"], "V": V, "area": h["area"]})
        # 1. sisi
        ns = [len(x["V"]) for x in hexes]
        ok1 = len(hexes) == 2 and all(C.CORNERS[0] <= n <= C.CORNERS[1] for n in ns) and ns.count(5) <= 1
        det1 = ("sudut tiap segi enam: " + ", ".join(map(str, ns))) if hexes else "dua segi enam tidak ditemukan"
        # 2. kebingungan arah: ujung goresan yang kebablasan / sudut bercabang
        spurs = [br for br in d.graph.branches if br.a is not None and
                 ((d.graph.kind[br.a] == "E") != (d.graph.kind[br.b] == "E")) and br.length > C.SPUR_REL * d.size]
        ok2 = not spurs and len(H) <= 3 + 1
        det2 = "sudut-sudut rapi" if ok2 else (f"{len(spurs)} garis kebablasan di sudut" if spurs else f"{len(H)} bukaan (garis saling silang tidak rapi)")
        # 3. tumpang-tindih
        if ov is not None and len(hexes) == 2:
            fr = ov["area"] / max(1.0, min(x["area"] for x in hexes))
            ok3 = C.OVERLAP[0] <= fr <= C.OVERLAP[1]
            det3 = f"tumpang-tindih {fr * 100:.0f}% segi enam (4%–60%)"
        else:
            ok3, det3 = False, "tumpang-tindih tidak terlihat"
        for x in hexes:
            V = x["V"]
            d.polyline(vis, V + V[:1], G.GREEN if ok1 else G.RED, 3)
            for v in V:
                d.dot(vis, v, G.BLUE, 6)
        if ov is not None:
            d.polyline(vis, [tuple(p) for p in ov["cnt"].reshape(-1, 2)] + [tuple(ov["cnt"][0][0])], G.GREEN if ok3 else G.RED, 2)
        for br in spurs:
            d.polyline(vis, br.pts, G.RED, 4)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)]
        return G.finish(C, vis, crits, "Wertheimer's hexagons")


if __name__ == "__main__":
    print(WertheimerHexagonsChecker.check(sys.argv[1])[0], WertheimerHexagonsChecker.last_criteria)
