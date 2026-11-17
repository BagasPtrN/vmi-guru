"""Form 18 — Panah empat arah (Directional Arrows).
Kriteria manual:
  1. Tidak ada ujung panah yang terbalik atau "melayang" (terlepas dari batang).
  2. Ujung panah runcing.
  3. Tidak ada arah yang membingungkan.
  4. Kaki terpanjang tidak lebih dari 2× kaki terpendek.
  5. Juga memenuhi semua kriteria Form 10 (dua garis berpotongan, kaki ≥ 1/4 inci,
     ≥ 1/2 tiap garis dalam 20° dari arah yang benar).
"""
import sys
import math
from symbols import _vmi_geom as G
from symbols import _cross as X


class DirectionalArrowsChecker:
    ATTACH_REL = 0.20      # sayap panah harus berada ≤ 20% ukuran gambar dari ujung kaki
    FLOAT_REL = 0.045      # sayap dianggap "melayang" bila celahnya ke batang > 4,5% ukuran
    MEET_REL = 0.13        # sayap bertemu di ujung (runcing) bila pangkalnya ≤ 13% dari ujung
    BARB_ANGLE = (8.0, 85.0)   # sudut sayap terhadap batang (mengarah balik ke pusat)
    BLUNT_MAX = 130.0      # arah awal satu sayap > 130° dari arah balik = ujung membulat (seperti U)
    BLUNT_MEAN = 100.0     # rata-rata arah awal sayap di satu ujung > 100° = ujung tumpul
    HEAD_DIR_MAX = 60.0    # arah kepala panah menyimpang maks 60° dari arah kakinya
    STRAY_REL = 0.10       # goresan lepas ≥ 10% ukuran yang bukan bagian panah = membingungkan
    MAX_LEG_RATIO = 2.0
    ANGLE_TOL = 20.0
    last_criteria = []

    @staticmethod
    def _shafts(d):
        sts = G.split_sharp(G.strokes(d.graph, merge_r=max(6.0, 2.5 * d.stroke)))
        cand = [s for s in sts[:6] if s.length >= 0.35 * d.size]
        best = None
        for i in range(len(cand)):
            for j in range(i + 1, len(cand)):
                a, b = cand[i], cand[j]
                if G.ang_diff(a.angle, b.angle) < 45:
                    continue
                p = G.poly_intersection(a.pts, b.pts, ext=0.06)
                if p is None:
                    continue
                sc = a.length + b.length
                if best is None or sc > best[0]:
                    best = (sc, [a, b], p)
        if best is None:
            # cadangan: analisis silang biasa
            T = X.two_lines(d, None, extra_max=1.0)
            return sts, T["lines"], T["p"]
        return sts, best[1], best[2]

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 5)
        vis = img.copy()
        sts, shafts, p = C._shafts(d)
        legs = (G.legs_at(shafts[0], p) + G.legs_at(shafts[1], p)) if (p is not None and len(shafts) == 2) else []
        S = d.size
        heads = [[] for _ in legs]
        strays = []
        for s in sts:
            if any(s is sh for sh in shafts) or s.length < 0.04 * S:
                continue
            best = None
            for k, leg in enumerate(legs):
                dn = min(G.dist(s.a, leg.tip), G.dist(s.b, leg.tip))
                # boleh menempel di bagian ujung kaki (30% terakhir)
                tail = leg.pts[int(len(leg.pts) * 0.7):]
                dl = min(G.point_to_poly(s.a, tail), G.point_to_poly(s.b, tail))
                dd = min(dn, dl)
                if best is None or dd < best[0]:
                    best = (dd, k)
            if best is not None and best[0] <= C.ATTACH_REL * S:
                heads[best[1]].append(s)
            elif s.length >= C.STRAY_REL * S:
                strays.append(s)
        # goresan kepala yang melewati ujung (mis. "^" atau ")" satu goresan) → pecah di titik terdekat ujung
        for k, leg in enumerate(legs):
            T = leg.tip
            new = []
            for b in heads[k]:
                dd = [G.dist(q, T) for q in b.pts]
                i = min(range(len(dd)), key=dd.__getitem__)
                n = len(b.pts)
                if 0.15 * n < i < 0.85 * n and dd[i] <= 1.5 * C.MEET_REL * S:
                    new += [G.Stroke(b.pts[:i + 1][::-1]), G.Stroke(b.pts[i:])]
                else:
                    new.append(b)
            heads[k] = new
        # komponen tinta: sayap yang terpisah dari batang = "melayang"
        ncomp, lab = G.cv2.connectedComponents(d.mask, connectivity=8)

        def comp(pt):
            x, y = int(round(pt[0])), int(round(pt[1]))
            y = min(max(y, 0), lab.shape[0] - 1); x = min(max(x, 0), lab.shape[1] - 1)
            return int(lab[y, x])
        # --- per ujung panah
        bad1, bad2, bad3 = [], [], []
        for k, leg in enumerate(legs):
            T = leg.tip
            u = G.unit((T[0] - p[0], T[1] - p[1]))
            if not heads[k]:
                bad1.append("ujung tanpa kepala panah")
                bad3.append("ada ujung tanpa kepala panah")
                d.dot(vis, T, G.RED, 10)
                continue
            sides, dirs, tip_ang0 = set(), [], []
            leg_comp = max(set(comp(q) for q in leg.pts), key=lambda c: sum(comp(q) == c for q in leg.pts))
            for b in heads[k]:
                e, f = (b.a, b.b) if G.dist(b.a, T) <= G.dist(b.b, T) else (b.b, b.a)
                v = G.unit((f[0] - e[0], f[1] - e[1]))
                gap = min(G.point_to_poly(q, leg.pts) for q in b.pts[:: max(1, len(b.pts) // 15)] + [e])
                floating = comp(b.pts[len(b.pts) // 2]) != leg_comp and gap > C.FLOAT_REL * S
                minor = b.length < 0.10 * S     # coretan kecil (mis. batang sedikit kebablasan)
                reversed_ = (v[0] * u[0] + v[1] * u[1] > 0.25) and not minor
                ang = math.degrees(math.acos(max(-1, min(1, -(v[0] * u[0] + v[1] * u[1])))))
                # ujung runcing: sayap berangkat dari titik ujung dengan sudut (bukan melengkung
                # menyinggung seperti huruf U). Arah awal sayap diukur pada 35% panjang pertamanya.
                bp = b.pts if G.dist(b.pts[0], T) <= G.dist(b.pts[-1], T) else b.pts[::-1]
                v0 = G.direction_from(bp, 0.35 * b.length)
                ang0 = math.degrees(math.acos(max(-1, min(1, -(v0[0] * u[0] + v0[1] * u[1])))))
                straight = ang0 <= C.BLUNT_MAX
                meet = G.dist(e, T) <= C.MEET_REL * S
                sharp = straight and meet and C.BARB_ANGLE[0] <= ang <= C.BARB_ANGLE[1] + 10
                if floating:
                    bad1.append("kepala panah melayang")
                if reversed_:
                    bad1.append("kepala panah terbalik")
                if minor:
                    continue
                if not sharp and not floating and not reversed_:
                    bad2.append("ujung membulat/tumpul" if not straight else
                                ("sayap tidak bertemu di ujung" if not meet else "sayap tegak lurus batang"))
                tip_ang0.append(ang0)
                cr = u[0] * (f[1] - T[1]) - u[1] * (f[0] - T[0])
                sides.add(cr > 0)
                dirs.append(v)
                col = G.RED if (floating or reversed_) else (G.GREEN if sharp else G.ORANGE)
                d.polyline(vis, b.pts, col, 3)
            if tip_ang0 and sum(tip_ang0) / len(tip_ang0) > C.BLUNT_MEAN:
                bad2.append("ujung membulat/tumpul")
            if not dirs:
                continue
            mv = G.unit((sum(v[0] for v in dirs), sum(v[1] for v in dirs)))
            dev = math.degrees(math.acos(max(-1, min(1, -(mv[0] * u[0] + mv[1] * u[1])))))
            if dev > C.HEAD_DIR_MAX and len(sides) == 2:
                bad3.append(f"kepala panah menyimpang {dev:.0f}° dari arah kaki")
            d.dot(vis, T, G.BLUE, 7)
        if strays:
            bad3.append(f"{len(strays)} goresan lepas di luar kepala panah")
            for s in strays:
                d.polyline(vis, s.pts, G.RED, 3)
        # --- 4. rasio kaki
        if len(legs) == 4:
            Ls = [l.length for l in legs]
            ratio = max(Ls) / max(1e-6, min(Ls))
            ok4, det4 = ratio <= C.MAX_LEG_RATIO, f"kaki terpanjang {ratio:.1f}× kaki terpendek"
        else:
            ok4, det4 = False, "kaki tidak dapat diukur"
        # --- 5. kriteria Form 10 pada batang
        if p is None or len(shafts) < 2:
            ok5, det5 = False, "batang silang tidak ditemukan / tidak berpotongan"
        else:
            okL, detL = X.legs_long_enough(legs, d)
            okA, detA, roles = X.hv_within(shafts, C.ANGLE_TOL)
            ok5 = okL and okA
            det5 = "dua garis berpotongan; " + detL + "; " + detA
            for i, l in enumerate(shafts):
                tgt = 0 if (roles and roles[i] == 0) else 90
                G.draw_dirs(d, vis, [l.pts], lambda a, t=tgt: G.ang_diff(a, t) <= C.ANGLE_TOL)
            d.dot(vis, p, G.BLUE, 8)
        if not legs:
            bad1.append("kepala panah tidak dapat dinilai")
            bad2.append("kepala panah tidak dapat dinilai")
            bad3.append("kepala panah tidak dapat dinilai")

        def summ(lst, okmsg):
            if not lst:
                return True, okmsg
            u = sorted(set(lst), key=lst.index)
            return False, "; ".join(u)
        ok1, det1 = summ(bad1, "4 kepala panah menempel & tidak terbalik")
        ok2, det2 = summ(bad2, "semua ujung panah runcing")
        ok3, det3 = summ(bad3, "arah keempat panah jelas")
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3),
                 G.criterion(4, ok4, det4), G.criterion(5, ok5, det5)]
        return G.finish(C, vis, crits, "Directional arrows")


if __name__ == "__main__":
    print(DirectionalArrowsChecker.check(sys.argv[1])[0], DirectionalArrowsChecker.last_criteria)
