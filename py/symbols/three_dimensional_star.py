"""Form 30 — Bintang tiga dimensi (Three-Dimensional Star).
Kriteria manual:
  1. Semua sudut segitiga melewati sisi segitiga lawan (6 ujung bintang menonjol).
  2. Satu segitiga yang sama ada bagian yang lewat di atas dan ada yang lewat di bawah segitiga lain.
  3. Tidak ada distorsi berat.
Cara ukur: kontur luar → jumlah ujung lancip; celah sempit di antara garis ganda (pita) → 6 garis
tengah pita (RANSAC) → dibagi ke segitiga 'puncak atas' dan 'puncak bawah'. Di tiap persilangan, sisi
yang pitanya tetap menyambung = lewat di atas.
"""
import sys
import math
import cv2
import numpy as np
from symbols import _vmi_geom as G


class ThreeDimensionalStarChecker:
    BAND_MAX_REL = 0.08     # pita: lebar ≤ 8% ukuran gambar
    BAND_MAX_CIRC = 0.40    # pita berbentuk memanjang
    TIP_MAX_ANGLE = 100.0   # ujung bintang = sudut cembung ≤ 100°
    TIP_MARGIN_REL = 0.02   # ujung harus melewati sisi lawan ≥ 2% ukuran gambar
    ANGLE_RANGE = (30.0, 90.0)   # sudut tiap segitiga (distorsi berat bila di luar)
    AREA_RATIO_MAX = 2.2         # luas segitiga besar / kecil
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
        cnt = G.outer_contour(d)
        M = cv2.moments(cnt)
        cen = (M["m10"] / M["m00"], M["m01"] / M["m00"]) if M["m00"] else (d.size / 2, d.size / 2)

        # --- pita & garis tengah ---
        H, _ = G.holes(d, close_rel=0.01, min_area_rel=0.0005)
        bands = [h for h in H if h["thick"] <= C.BAND_MAX_REL * d.size and h["circ"] <= C.BAND_MAX_CIRC]
        lab = np.zeros(d.mask.shape, np.int32)
        pts = []
        for i, h in enumerate(bands):
            lab[h["mask"] > 0] = i + 1
            pts += G.skel_points(h["mask"])
        bw = float(np.median([h["thick"] for h in bands])) if bands else 0.0
        pts = pts + G.skel_points(d.mask)     # garis tengah pita + kedua garis tepinya
        lines = G.ransac_lines(pts, 6, tol=max(3.0, 0.5 * (bw + d.stroke) + 2), iters=800,
                               min_inl=int(0.12 * d.size)) if len(pts) > 20 else []
        up, dn = _split_triangles(lines, cen)
        tris = {}
        for name, grp in (("atas", up), ("bawah", dn)):
            if len(grp) == 3:
                V = []
                for i in range(3):
                    for j in range(i + 1, 3):
                        X = G.line_intersection(grp[i]["p"], grp[i]["v"], grp[j]["p"], grp[j]["v"])
                        if X is not None:
                            V.append(X)
                if len(V) == 3:
                    V.sort(key=lambda p: math.atan2(p[1] - cen[1], p[0] - cen[0]))
                    tris[name] = V

        # 1. ujung bintang
        tips = 0
        if cnt is not None:
            P, _ = G.polygon(cnt, eps_rel=0.012, min_side_rel=0.03, min_turn=20)
            conv = _convex_flags(P)
            ang = G.interior_angles(P)
            tips = sum(1 for k in range(len(P)) if conv[k] and ang[k] <= C.TIP_MAX_ANGLE)
            for k in range(len(P)):
                if conv[k] and ang[k] <= C.TIP_MAX_ANGLE:
                    d.dot(vis, P[k], G.GREEN, 7)
        short = 0
        if len(tris) == 2:
            mg = C.TIP_MARGIN_REL * d.size
            for a_, b_ in (("atas", "bawah"), ("bawah", "atas")):
                for v in tris[a_]:
                    # sisi lawan = sisi segitiga lain yang paling dekat dengan ujung ini
                    W = tris[b_]
                    best = min(range(3), key=lambda k: _seg_dist(v, W[k], W[(k + 1) % 3]))
                    p, q = W[best], W[(best + 1) % 3]
                    if _side(p, q, v) * _side(p, q, cen) > 0 or abs(_signed(p, q, v)) < mg:
                        short += 1
                        d.dot(vis, v, G.RED, 8)
        # sisi lawan hanya dipakai bila kedua segitiga terukur wajar; bila tidak, cukup 6 ujung pada kontur luar
        geo_ok = len(tris) == 2 and all(C.ANGLE_RANGE[0] <= a <= C.ANGLE_RANGE[1] for V in tris.values() for a in _tri_angles(V))
        ok1 = tips >= 6 and (short == 0 or not geo_ok)
        det1 = f"{tips} ujung bintang menonjol (harus 6)" + (f"; {short} sudut tidak melewati sisi lawan" if short else "")

        # 2. atas–bawah
        ok2, det2 = False, "garis tidak ganda (tidak ada pita)" if not bands else "persilangan tidak dapat dinilai"
        if bands and up and dn:
            Hh, Ww = lab.shape

            def labels_at(p, n):
                seen = set()
                for t in np.arange(-bw, bw + 0.1, 1.0):
                    x, y = int(round(p[0] + n[0] * t)), int(round(p[1] + n[1] * t))
                    if 0 <= y < Hh and 0 <= x < Ww and lab[y, x]:
                        seen.add(int(lab[y, x]))
                return seen

            def continuous(L, X, sin_t):
                v = L["v"]
                n = (-v[1], v[0])
                s = 0.8 * (bw + 2 * d.stroke) / max(sin_t, 0.3) + 3
                return bool(labels_at((X[0] - v[0] * s, X[1] - v[1] * s), n) & labels_at((X[0] + v[0] * s, X[1] + v[1] * s), n))
            stat = {"atas": [0, 0], "bawah": [0, 0]}   # [di atas, di bawah]
            n_cross = 0
            for A in up:
                for B in dn:
                    dth = abs(A["angle"] - B["angle"]) % 180
                    dth = min(dth, 180 - dth)
                    if dth < 25:
                        continue
                    X = G.line_intersection(A["p"], A["v"], B["p"], B["v"])
                    if X is None or not (_on_seg(A, X, bw) and _on_seg(B, X, bw)):
                        continue
                    n_cross += 1
                    s_t = math.sin(math.radians(dth))
                    ca, cb = continuous(A, X, s_t), continuous(B, X, s_t)
                    if ca != cb:
                        stat["atas"][0 if ca else 1] += 1
                        stat["bawah"][0 if cb else 1] += 1
                        d.dot(vis, X, G.GREEN, 6)
                    else:
                        d.dot(vis, X, G.ORANGE, 6)
            ok2 = any(o >= 1 and u >= 1 for o, u in stat.values())
            det2 = (f"segitiga puncak-atas: {stat['atas'][0]}× di atas, {stat['atas'][1]}× di bawah; "
                    f"puncak-bawah: {stat['bawah'][0]}× di atas, {stat['bawah'][1]}× di bawah ({n_cross} persilangan)")

        # 3. distorsi
        if len(tris) == 2:
            angs = [a for V in tris.values() for a in _tri_angles(V)]
            areas = [abs(_area(V)) for V in tris.values()]
            ratio = max(areas) / max(min(areas), 1e-6)
            bad = [a for a in angs if not (C.ANGLE_RANGE[0] <= a <= C.ANGLE_RANGE[1])]
            ok3 = not bad and ratio <= C.AREA_RATIO_MAX
            det3 = (f"sudut segitiga {min(angs):.0f}°–{max(angs):.0f}° ({C.ANGLE_RANGE[0]:.0f}°–{C.ANGLE_RANGE[1]:.0f}°), "
                    f"perbandingan luas {ratio:.1f}× (maks {C.AREA_RATIO_MAX}×)")
            for V in tris.values():
                d.polyline(vis, V + [V[0]], G.GREEN if ok3 else G.RED, 2)
        else:
            ok3 = False
            det3 = f"dua segitiga tidak dapat dikenali ({len(up)} + {len(dn)} sisi)"
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3)]
        return G.finish(C, vis, crits, "Three-dimensional star")


def _tri_from(grp):
    V = []
    for i in range(3):
        for j in range(i + 1, 3):
            X = G.line_intersection(grp[i]["p"], grp[i]["v"], grp[j]["p"], grp[j]["v"])
            if X is None:
                return None
            V.append(X)
    return V


def _inside(V, p):
    s = [_side(V[i], V[(i + 1) % 3], p) for i in range(3)]
    return all(x == s[0] for x in s)


def _split_triangles(lines, cen):
    """Bagi 6 garis menjadi 2 segitiga: tiap pasangan garis hampir sejajar dipisah, dan kedua segitiga
    harus memuat pusat gambar. Segitiga yang puncaknya paling atas disebut 'atas'."""
    import itertools
    if len(lines) < 6:
        up, dn = [], []
        for L in lines:   # cadangan: aturan orientasi untuk bintang tegak
            a = L["angle"]
            px, py = L["p"]; vx, vy = L["v"]
            if a < 30 or a > 150:
                y_at = py + (cen[0] - px) * vy / vx if abs(vx) > 1e-6 else py
                (up if y_at > cen[1] else dn).append(L)
            else:
                x_at = px + (cen[1] - py) * vx / vy if abs(vy) > 1e-6 else px
                (up if (a > 90) == (x_at < cen[0]) else dn).append(L)
        return up, dn
    best = None
    for A in itertools.combinations(range(6), 3):
        if 0 not in A:
            continue
        B = [i for i in range(6) if i not in A]
        ga, gb = [lines[i] for i in A], [lines[i] for i in B]
        if min(_adiff(x, y) for g in (ga, gb) for x, y in itertools.combinations(g, 2)) < 25:
            continue
        Va, Vb = _tri_from(ga), _tri_from(gb)
        if not Va or not Vb:
            continue
        if not (_inside(Va, cen) and _inside(Vb, cen)):
            continue
        sc = min(abs(_area(Va)), abs(_area(Vb)))
        if best is None or sc > best[0]:
            best = (sc, ga, gb, Va, Vb)
    if best is None:
        return lines[:3], lines[3:]
    _, ga, gb, Va, Vb = best
    return (ga, gb) if min(p[1] for p in Va) <= min(p[1] for p in Vb) else (gb, ga)


def _adiff(x, y):
    t = abs(x["angle"] - y["angle"]) % 180
    return min(t, 180 - t)


def _signed(p, q, v):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = math.hypot(dx, dy) or 1
    return ((v[0] - p[0]) * dy - (v[1] - p[1]) * dx) / n


def _side(p, q, v):
    return 1 if _signed(p, q, v) > 0 else -1


def _seg_dist(v, p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    L2 = dx * dx + dy * dy or 1
    t = max(0, min(1, ((v[0] - p[0]) * dx + (v[1] - p[1]) * dy) / L2))
    return math.hypot(v[0] - p[0] - t * dx, v[1] - p[1] - t * dy)


def _on_seg(L, X, m):
    a, b = L["a"], L["b"]
    t = (X[0] - a[0]) * L["v"][0] + (X[1] - a[1]) * L["v"][1]
    return -m <= t <= G.dist(a, b) + m


def _area(V):
    return 0.5 * sum(V[i][0] * V[(i + 1) % len(V)][1] - V[(i + 1) % len(V)][0] * V[i][1] for i in range(len(V)))


def _tri_angles(V):
    out = []
    for i in range(3):
        a, b, c = V[i], V[i - 1], V[(i + 1) % 3]
        u = (b[0] - a[0], b[1] - a[1]); w = (c[0] - a[0], c[1] - a[1])
        nu, nw = math.hypot(*u), math.hypot(*w)
        out.append(math.degrees(math.acos(max(-1, min(1, (u[0] * w[0] + u[1] * w[1]) / (nu * nw))))) if nu and nw else 0)
    return out


def _convex_flags(P):
    s = _area(P)
    out = []
    n = len(P)
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        out.append(cr * s > 0)
    return out


if __name__ == "__main__":
    print(ThreeDimensionalStarChecker.check(sys.argv[1])[0], ThreeDimensionalStarChecker.last_criteria)
