"""Form 16 — Persegi terbuka dan lingkaran (Open Square and Circle).
Kriteria manual:
  1. Celah atau tumpang-tindih antar-bentuk tidak lebih dari 1/16 inci.
  2. Tidak ada distorsi berat pada lingkaran atau persegi terbuka.
  3. Tinggi lingkaran dan persegi dalam perbandingan 2 : 1.
  4. Garis bagi lingkaran yang melewati sudut persegi harus masuk ke dalam persegi.
"""
import sys
import math
import cv2
import numpy as np
from symbols import _vmi_geom as G


class OpenSquareCircleChecker:
    JOIN_REL = 0.06        # 1/16 inci ≈ 6% sisi persegi (asumsi sisi persegi ±1 inci)
    INTRUDE_MAX = 0.05     # maks 5% luas lingkaran berada di dalam kotak persegi
    CIRCLE_MAX_RATIO = 1.8 # lingkaran tidak gepeng berat
    SIDE_TOL = 25.0        # sisi persegi: tegak/mendatar dalam ±25°
    HEIGHT_RATIO = 2.0
    PROJECT_REL = 0.25     # garis bagi diperpanjang 25% sisi persegi melewati sudut
    last_criteria = []

    @staticmethod
    def _circle(d):
        k = max(3, int(0.02 * d.size)) | 1
        m = cv2.morphologyEx(d.mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        best = None
        Ls = G.loops(m, min_rel=0.05)
        for L in Ls:
            if max(L["bbox"][2], L["bbox"][3]) < 0.15 * d.size:
                continue
            rw, rh = L["rw"] + d.stroke, L["rh"] + d.stroke
            ratio = max(rw, rh) / min(rw, rh)
            if ratio > 3.0:
                continue
            pts = L["cnt"].reshape(-1, 2).astype(np.float32)
            score = L["area"] / ratio
            if best is None or score > best[0]:
                M = cv2.moments(L["cnt"])
                c = (M["m10"] / M["m00"], M["m01"] / M["m00"]) if M["m00"] else L["center"]
                x, y, w, h = L["bbox"]
                best = (score, {"pts": pts, "c": c, "R": math.sqrt(L["area"] / math.pi) + d.stroke / 2,
                                "ratio": ratio, "h": h + d.stroke, "w": w + d.stroke, "cnt": L["cnt"]})
        if not best:
            return None
        circ = best[1]
        # lubang lain yang hanya dipisah satu goresan (mis. garis persegi masuk ke lingkaran)
        # digabung kembali menjadi satu lingkaran
        region = np.zeros(m.shape, np.uint8)
        cv2.drawContours(region, [circ["cnt"]], -1, 1, -1)
        gapk = int(2 * d.stroke + 3) | 1
        changed = True
        while changed:
            changed = False
            grown = cv2.dilate(region, np.ones((gapk, gapk), np.uint8))
            for L in Ls:
                hole = np.zeros(m.shape, np.uint8)
                cv2.drawContours(hole, [L["cnt"]], -1, 1, -1)
                if (hole & region).any() or not (hole & grown).any():
                    continue
                uni = cv2.morphologyEx(region | hole, cv2.MORPH_CLOSE, np.ones((gapk, gapk), np.uint8))
                cs, _ = cv2.findContours(uni, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cu = max(cs, key=cv2.contourArea)
                (_, _), (rw, rh), _ = cv2.minAreaRect(cu)
                if max(rw, rh) / max(1, min(rw, rh)) <= 2.0:
                    region = uni
                    changed = True
        cs, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cu = max(cs, key=cv2.contourArea)
        (cx, cy), (rw, rh), _ = cv2.minAreaRect(cu)
        x, y, w, h = cv2.boundingRect(cu)
        M = cv2.moments(cu)
        A = cv2.contourArea(cu)
        return {"pts": cu.reshape(-1, 2).astype(np.float32), "cnt": cu,
                "c": (M["m10"] / M["m00"], M["m01"] / M["m00"]) if M["m00"] else (cx, cy),
                "R": math.sqrt(A / math.pi) + d.stroke / 2,
                "ratio": (max(rw, rh) + d.stroke) / (min(rw, rh) + d.stroke),
                "h": h + d.stroke, "w": w + d.stroke}

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 4)
        vis = img.copy()
        circ = C._circle(d)
        skel = [q for br in d.graph.branches for q in br.pts]
        if circ is None:
            for br in d.graph.branches:
                d.polyline(vis, br.pts, G.RED, 3)
            crits = [G.criterion(1, False, "lingkaran tidak ditemukan"),
                     G.criterion(2, False, "lingkaran tidak ditemukan / terdistorsi"),
                     G.criterion(3, False, "tidak dapat dinilai"), G.criterion(4, False, "tidak dapat dinilai")]
            return G.finish(C, vis, crits, "Open square and circle")
        c, R = circ["c"], circ["R"]
        ring = 1.6 * d.stroke + 2
        cnt = circ["cnt"].astype(np.float32)
        sd = [cv2.pointPolygonTest(cnt, (float(q[0]), float(q[1])), True) for q in skel]
        # titik di luar lingkaran (jauh dari garisnya) = persegi; di dalam (jauh dari garis) = tumpang-tindih
        sq = [q for q, v in zip(skel, sd) if v < -(ring + d.stroke / 2)]
        inside = [q for q, v in zip(skel, sd) if v > ring]
        # --- persegi terbuka: sisi kiri, bawah, kanan
        ok_sq, det_sq, corner, box = False, "persegi terbuka tidak ditemukan", None, None
        if len(sq) >= 20:
            xs = [q[0] for q in sq]; ys = [q[1] for q in sq]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            w, h = x1 - x0, y1 - y0
            side = max(w, h, 1.0)
            # sisi-sisi persegi = ruas goresan (dipecah di sudut tajam) yang berada di luar lingkaran
            segs = []
            for st in G.split_sharp(G.strokes(d.graph, merge_r=max(6.0, 2.5 * d.stroke)), min_turn=50.0):
                pts = [q for q in st.pts if cv2.pointPolygonTest(cnt, (float(q[0]), float(q[1])), True) < -(ring + d.stroke / 2)]
                if len(pts) < 5 or G.path_length(pts) < 0.12 * d.size:
                    continue
                a = G.fit_angle(pts)
                kind = "V" if G.ang_diff(a, 90) <= C.SIDE_TOL else ("H" if G.ang_diff(a, 0) <= C.SIDE_TOL else "X")
                mx = sum(q[0] for q in pts) / len(pts); my = sum(q[1] for q in pts) / len(pts)
                segs.append((kind, a, mx, my, pts))
            probs = []
            V = [s_ for s_ in segs if s_[0] == "V"]
            H = [s_ for s_ in segs if s_[0] == "H"]
            Xs = [s_ for s_ in segs if s_[0] == "X"]
            if len(V) < 2 or max(v[2] for v in V) - min(v[2] for v in V) < 0.35 * w:
                probs.append("sisi tegak kiri/kanan tidak jelas")
            if not H:
                probs.append("sisi bawah tidak jelas")
            elif V and max(H, key=lambda h_: h_[3])[3] < y0 + 0.5 * h:
                probs.append("sisi mendatar tidak berada di bawah")
            for x_ in Xs:
                probs.append(f"ada sisi miring {min(G.ang_diff(x_[1], 0), G.ang_diff(x_[1], 90)):.0f}°")
            top_closed = any(h_[3] < y0 + 0.3 * h for h_ in H) and len(H) >= 2
            if top_closed:
                probs.append("bagian atas tertutup")
            box = (x0, y0, x1, y1)
            # sudut persegi tempat lingkaran menempel = titik persegi (setengah kanan-bawah) terdekat ke lingkaran
            quad = [q for q in sq if q[0] >= x0 + 0.5 * w and q[1] >= y0 + 0.5 * h] or sq
            corner = min(quad, key=lambda q: -cv2.pointPolygonTest(cnt, (float(q[0]), float(q[1])), True))
            ok_sq = not probs
            det_sq = "persegi terbuka jelas" if ok_sq else "; ".join(probs)
        intr = 0.0
        if box is not None:
            reg = np.zeros(d.mask.shape, np.uint8)
            cv2.drawContours(reg, [circ["cnt"]], -1, 1, -1)
            bx0, by0, bx1, by1 = [int(round(v)) for v in box]
            tot = reg.sum()
            intr = float(reg[by0:by1 + 1, bx0:bx1 + 1].sum()) / tot if tot else 0.0
        ok_ci = circ["ratio"] <= C.CIRCLE_MAX_RATIO
        ok2 = ok_sq and ok_ci
        det2 = det_sq + ("; lingkaran rasio %.1f : 1" % circ["ratio"]) + ("" if ok_ci else " (gepeng)")
        # --- 1. celah / tumpang-tindih
        if corner is not None and box is not None:
            side = max(box[2] - box[0], box[3] - box[1], 1.0)
            # kontur lingkaran = tepi DALAM goresan → kurangi tebal goresan lingkaran + setengah goresan persegi
            sep = -cv2.pointPolygonTest(cnt, (float(corner[0]), float(corner[1])), True) - 1.5 * d.stroke
            pen = max([cv2.pointPolygonTest(cnt, (float(q[0]), float(q[1])), True) for q in inside], default=0.0)
            ov = max(pen, -sep, 0.0)
            gap = max(sep, 0.0)
            worst = max(ov, gap) / side
            if intr > C.INTRUDE_MAX:   # lingkaran masuk ke dalam area persegi = tumpang-tindih
                ov = max(ov, intr * side)
                worst = max(worst, ov / side)
            ok1 = worst <= C.JOIN_REL
            det1 = (f"celah {gap / side * 100:.0f}%" if gap >= ov else f"tumpang-tindih {ov / side * 100:.0f}%") + \
                   f" sisi persegi (maks {C.JOIN_REL * 100:.0f}%)"
        else:
            ok1, det1 = False, "sudut persegi tidak ditemukan"
        # --- 3. tinggi
        if box is not None:
            sh = box[3] - box[1]
            hr = circ["h"] / max(sh, 1.0)
            ok3 = 1 / C.HEIGHT_RATIO <= hr <= C.HEIGHT_RATIO
            det3 = f"tinggi lingkaran : persegi = {hr:.2f} : 1"
        else:
            ok3, det3 = False, "persegi tidak ditemukan"
        # --- 4. garis bagi
        if corner is not None and box is not None:
            v = G.unit((corner[0] - c[0], corner[1] - c[1]))
            side = max(box[2] - box[0], box[3] - box[1], 1.0)
            q = (corner[0] + v[0] * C.PROJECT_REL * side, corner[1] + v[1] * C.PROJECT_REL * side)
            mx, my = 0.08 * (box[2] - box[0]), 0.08 * (box[3] - box[1])
            # harus benar-benar masuk ke bagian dalam persegi (bukan menyusuri sisinya)
            ok4 = box[0] + mx <= q[0] <= box[2] - mx and box[1] + my <= q[1] <= box[3] - my
            det4 = "garis bagi masuk ke persegi" if ok4 else "garis bagi tidak masuk ke persegi"
            d.polyline(vis, [c, q], G.GREEN if ok4 else G.RED, 2)
            d.dot(vis, corner, G.BLUE, 7)
        else:
            ok4, det4 = False, "sudut persegi tidak ditemukan"
        # visual
        d.polyline(vis, [tuple(p) for p in circ["pts"]] + [tuple(circ["pts"][0])], G.GREEN if ok_ci else G.RED, 3)
        d.dot(vis, c, G.BLUE, 6)
        if box is not None:
            d.polyline(vis, [(box[0], box[1]), (box[0], box[3]), (box[2], box[3]), (box[2], box[1])],
                       G.GREEN if ok_sq else G.RED, 2)
        for q in inside:
            d.dot(vis, q, G.ORANGE, 2)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2),
                 G.criterion(3, ok3, det3), G.criterion(4, ok4, det4)]
        return G.finish(C, vis, crits, "Open square and circle")


if __name__ == "__main__":
    print(OpenSquareCircleChecker.check(sys.argv[1])[0], OpenSquareCircleChecker.last_criteria)
