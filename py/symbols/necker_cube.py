"""Form 28 — Kubus Necker (Necker Cube).
Kriteria manual:
  1. Jumlah bagian benar (12 rusuk).
  2. Orientasi benar (persegi belakang di kanan-atas: rusuk penghubung miring '/').
  3. Tidak ada tanda kebingungan.
"""
import sys
from symbols import _vmi_geom as G


class NeckerCubeChecker:
    N_EDGES = 12
    HV_TOL = 22.0
    DIAG_RANGE = (105.0, 165.0)    # '/' pada konvensi manual (sumbu y ke bawah)
    SPUR_REL = 0.06
    JOIN_REL = 0.07
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
        segs = [s for s in G.split_sharp(G.strokes(d.graph, tol=22.0, merge_r=max(6.0, 2.5 * d.stroke)), min_turn=30)
                if s.length >= 0.12 * d.size]
        kind = lambda s: "H" if G.ang_diff(s.angle, 0) <= C.HV_TOL else ("V" if G.ang_diff(s.angle, 90) <= C.HV_TOL else "D")
        K = [kind(s) for s in segs]
        nH, nV, nD = K.count("H"), K.count("V"), K.count("D")
        ok1 = len(segs) == C.N_EDGES
        det1 = f"{len(segs)} rusuk (harus 12): {nH} mendatar, {nV} tegak, {nD} miring"
        diags = [s for s, k in zip(segs, K) if k == "D"]
        ok2 = nD == 4 and all(C.DIAG_RANGE[0] <= s.angle <= C.DIAG_RANGE[1] for s in diags) and nH == 4 and nV == 4
        det2 = ("rusuk penghubung: " + ", ".join(f"{s.angle:.0f}°" for s in diags) + " (harus miring '/' ke kanan-atas)") if diags else "rusuk penghubung tidak ditemukan"
        spurs = [br for br in d.graph.branches if br.a is not None and
                 ((d.graph.kind[br.a] == "E") != (d.graph.kind[br.b] == "E")) and C.SPUR_REL * d.size < br.length < 0.12 * d.size]
        ends = [p for s, k in zip(segs, K) if k != "D" for p in (s.a, s.b)]
        loose = [s for s in diags if min((G.dist(s.a, e) for e in ends), default=1e9) > C.JOIN_REL * d.size or
                 min((G.dist(s.b, e) for e in ends), default=1e9) > C.JOIN_REL * d.size]
        # ujung rusuk mendatar/tegak juga harus bertemu rusuk lain (sudut kubus)
        allends = [p for s in segs for p in (s.a, s.b)]
        dangling = [p for p in allends if sum(G.dist(p, q) <= C.JOIN_REL * d.size for q in allends) < 2]
        ok3 = not spurs and not loose and not dangling and ok1
        det3 = "sambungan rusuk rapi" if ok3 else "; ".join(x for x in (
            f"{len(spurs)} coretan kecil" if spurs else "", f"{len(loose)} rusuk miring tidak menyambung sudut" if loose else "",
            f"{len(dangling)} ujung rusuk menggantung" if dangling else "", "jumlah rusuk salah" if not ok1 else "") if x)
        for s, k in zip(segs, K):
            col = G.GREEN if k != "D" or (C.DIAG_RANGE[0] <= s.angle <= C.DIAG_RANGE[1]) else G.RED
            d.polyline(vis, s.pts, col if k != "D" else (G.BLUE if col == G.GREEN else G.RED), 3)
        for p in dangling:
            d.dot(vis, p, G.RED, 8)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)]
        return G.finish(C, vis, crits, "Necker cube")


if __name__ == "__main__":
    print(NeckerCubeChecker.check(sys.argv[1])[0], NeckerCubeChecker.last_criteria)
