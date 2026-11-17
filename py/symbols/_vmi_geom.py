"""
Toolkit geometri bersama untuk 12 checker VMI (Beery VMI Form 4–18).

Alur umum:
  gambar → biner (tahan bayangan/foto HP) → potong ke area tinta → skala kerja seragam
  → skeleton (Zhang–Suen) → graf goresan (simpul ujung/percabangan + cabang)
  → besaran geometri yang dipakai kriteria manual: arah garis, panjang kaki,
    titik potong, loop/lengkung tertutup, celah, dsb.

Semua ukuran dihitung pada "skala kerja": sisi terpanjang area tinta = WORK piksel,
sehingga ambang batas relatif terhadap ukuran gambar anak (foto bisa berapa pun resolusinya).
"""
import math
import cv2
import numpy as np

WORK = 320          # sisi terpanjang area tinta pada skala kerja (px)
PAD = 0.08          # margin di sekeliling tinta saat dipotong


# =============================================================================
# 1. Pra-pemrosesan
# =============================================================================
def load(path, max_dim=1000):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Gambar tidak ditemukan: {path}")
    h, w = img.shape[:2]
    s = max_dim / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img


def binarize(bgr):
    """Tinta = 1. Normalisasi pencahayaan dulu agar bayangan foto HP tidak ikut jadi tinta."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    k = max(15, (min(h, w) // 12) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    norm = cv2.divide(gray, bg, scale=255)
    norm = cv2.GaussianBlur(norm, (3, 3), 0)
    t, th = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Otsu kadang terlalu longgar di kertas yang sangat bersih → batasi
    if t > 235:
        _, th = cv2.threshold(norm, 200, 255, cv2.THRESH_BINARY_INV)
    th = (th > 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(th, 8)
    keep = np.ones(n, np.uint8)
    keep[0] = 0
    # buang tepi kertas / bayangan meja: komponen yang menempel di tepi foto dan membentang panjang di situ
    for i in range(1, n):
        x, y, bw, bh = st[i, :4]
        touches = x == 0 or y == 0 or x + bw >= w or y + bh >= h
        if not touches:
            continue
        fill = st[i, cv2.CC_STAT_AREA] / float(max(1, bw * bh))
        if fill > 0.35 and st[i, cv2.CC_STAT_AREA] > 0.01 * h * w:
            keep[i] = 0          # blok gelap padat di tepi (meja, bayangan) — goresan pensil tidak padat
            continue
        if bw >= 0.6 * w or bh >= 0.6 * h:
            ys, xs = np.nonzero(lab == i)
            on_edge = np.mean((xs <= 2) | (ys <= 2) | (xs >= w - 3) | (ys >= h - 3))
            if on_edge > 0.30:
                keep[i] = 0
    # buang bintik kecil (tekstur kertas / debu) — relatif terhadap goresan terbesar, bukan luas
    # foto, agar gambar kecil di foto besar tidak kehilangan bagiannya (mis. sayap panah terpisah)
    areas = st[:, cv2.CC_STAT_AREA] * keep
    big = areas.max() if n > 1 else 0
    keep &= (areas >= max(10, int(0.012 * big))).astype(np.uint8)
    return keep[lab]


class Drawing:
    """Gambar anak pada skala kerja + skeleton + graf goresan."""

    def __init__(self, bgr):
        self.bgr = bgr
        full = binarize(bgr)
        ys, xs = np.nonzero(full)
        if len(xs) < 20:
            raise ValueError("Tidak ada goresan yang terdeteksi")
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        side = max(bw, bh)
        pad = int(side * PAD) + 2
        self.s = WORK / side                         # faktor skala full → kerja
        self.ox, self.oy = x0 - pad, y0 - pad        # offset potongan (koordinat full)
        crop = np.zeros((bh + 2 * pad, bw + 2 * pad), np.uint8)
        crop[pad:pad + bh, pad:pad + bw] = full[y0:y1 + 1, x0:x1 + 1]
        W = max(8, int(round(crop.shape[1] * self.s)))
        H = max(8, int(round(crop.shape[0] * self.s)))
        m = cv2.resize(crop * 255, (W, H), interpolation=cv2.INTER_AREA)
        m = (m > 60).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        self.mask = m
        self.ink_w, self.ink_h = bw * self.s, bh * self.s
        self.size = max(self.ink_w, self.ink_h)  # = WORK
        self.stroke = stroke_width(m)
        self.skel = skeletonize(m)
        self.graph = Graph(self.skel, spur=max(4.0, 1.6 * self.stroke))

    # konversi koordinat kerja (x, y) → koordinat gambar penuh (untuk visualisasi)
    def P(self, p):
        return (int(round(p[0] / self.s + self.ox)), int(round(p[1] / self.s + self.oy)))

    def polyline(self, img, pts, color, thick=3):
        if len(pts) >= 2:
            arr = np.array([self.P(p) for p in pts], np.int32)
            cv2.polylines(img, [arr], False, color, thick, cv2.LINE_AA)

    def dot(self, img, p, color, r=7):
        cv2.circle(img, self.P(p), r, color, -1, cv2.LINE_AA)


def stroke_width(mask):
    """Perkiraan tebal goresan (px skala kerja) = 2 × median jarak ke tepi pada skeleton."""
    if mask.sum() == 0:
        return 1.0
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
    sk = skeletonize(mask)
    v = dist[sk > 0]
    return float(max(1.0, 2 * np.median(v))) if len(v) else 1.0


# =============================================================================
# 2. Skeleton (Zhang–Suen, numpy murni — juga jalan di browser lewat Pyodide)
# =============================================================================
def skeletonize(mask):
    img = np.pad((mask > 0).astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P2 = img[:-2, 1:-1]; P3 = img[:-2, 2:]; P4 = img[1:-1, 2:]; P5 = img[2:, 2:]
            P6 = img[2:, 1:-1]; P7 = img[2:, :-2]; P8 = img[1:-1, :-2]; P9 = img[:-2, :-2]
            C = img[1:-1, 1:-1]
            B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
            seq = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c1 = P2 * P4 * P6 == 0
                c2 = P4 * P6 * P8 == 0
            else:
                c1 = P2 * P4 * P8 == 0
                c2 = P2 * P6 * P8 == 0
            rm = (C == 1) & (B >= 2) & (B <= 6) & (A == 1) & c1 & c2
            if rm.any():
                img[1:-1, 1:-1][rm] = 0
                changed = True
        if not changed:
            break
    return _m_connect(img[1:-1, 1:-1])


def _m_connect(sk):
    """Buang piksel 'tangga' yang berlebih sehingga skeleton benar-benar setebal 1 piksel
    (m-connected). Tanpa ini, piksel sudut tangga terbaca sebagai percabangan palsu."""
    sk = sk.copy()
    h, w = sk.shape
    ys, xs = np.nonzero(sk)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if y == 0 or x == 0 or y == h - 1 or x == w - 1:
            continue
        N, S, E, W = sk[y - 1, x], sk[y + 1, x], sk[y, x + 1], sk[y, x - 1]
        NE, NW, SE, SW = sk[y - 1, x + 1], sk[y - 1, x - 1], sk[y + 1, x + 1], sk[y + 1, x - 1]
        if ((N and E and not S and not W and not SW) or (E and S and not N and not W and not NW) or
                (S and W and not N and not E and not NE) or (W and N and not S and not E and not SE)):
            sk[y, x] = 0
    return sk


_K8 = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], np.float32)
_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _neigh_count(sk):
    return cv2.filter2D(sk.astype(np.float32), -1, _K8, borderType=cv2.BORDER_CONSTANT).astype(np.int32) * (sk > 0)


def _crossing_number(sk):
    """Jumlah transisi 0→1 mengelilingi piksel (P2..P9). 1 = ujung, 2 = jalur, ≥3 = percabangan.
    Lebih tahan terhadap pola 'tangga' skeleton dibanding hitungan tetangga."""
    img = np.pad((sk > 0).astype(np.int32), 1)
    P = [img[:-2, 1:-1], img[:-2, 2:], img[1:-1, 2:], img[2:, 2:],
         img[2:, 1:-1], img[2:, :-2], img[1:-1, :-2], img[:-2, :-2]]
    cn = sum(((P[i] == 0) & (P[(i + 1) % 8] == 1)).astype(np.int32) for i in range(8))
    return cn * (sk > 0)


# =============================================================================
# 3. Graf goresan
# =============================================================================
class Branch:
    __slots__ = ("pts", "a", "b", "length")

    def __init__(self, pts, a, b):
        self.pts = pts              # list (x, y) berurutan dari simpul a ke simpul b
        self.a, self.b = a, b       # id simpul (None untuk loop tertutup)
        self.length = path_length(pts)

    def other(self, node):
        return self.b if self.a == node else self.a

    def from_node(self, node):
        """titik cabang berurutan mulai dari simpul `node`"""
        return self.pts if self.a == node else self.pts[::-1]


class Graph:
    """Simpul: 'E' ujung goresan, 'J' percabangan. Cabang menghubungkan dua simpul."""

    def __init__(self, skel, spur=4.0):
        sk = (skel > 0).astype(np.uint8)
        for _ in range(4):  # pangkas duri kecil berulang
            self._build(sk)
            removed = False
            for br in self.branches:
                if br.a is None:
                    continue
                ka, kb = self.kind[br.a], self.kind[br.b]
                if ((ka == "E") != (kb == "E")) and br.length < spur:
                    for (x, y) in br.pts:
                        xi, yi = int(round(x)), int(round(y))
                        if self.kind_at.get((xi, yi)) != "J" and 0 <= yi < sk.shape[0] and 0 <= xi < sk.shape[1]:
                            sk[yi, xi] = 0
                    removed = True
            if not removed:
                break
            sk = skeletonize(sk)
        self.skel = sk

    def _build(self, sk):
        h, w = sk.shape
        nb = _neigh_count(sk)
        cn = _crossing_number(sk)
        jmask = (((cn >= 3) | (nb >= 4)) & (sk > 0)).astype(np.uint8)
        # gugus piksel percabangan → satu simpul J
        nj, jlab = cv2.connectedComponents(cv2.dilate(jmask, np.ones((3, 3), np.uint8)) * sk, 8)
        self.nodes, self.kind, self.kind_at = [], [], {}
        jnode = {}
        for j in range(1, nj):
            ys, xs = np.nonzero(jlab == j)
            jnode[j] = len(self.nodes)
            self.nodes.append((float(xs.mean()), float(ys.mean())))
            self.kind.append("J")
            for x, y in zip(xs, ys):
                self.kind_at[(int(x), int(y))] = "J"
        chains = sk.copy()
        chains[jlab > 0] = 0
        nc, clab = cv2.connectedComponents(chains, 8)
        self.branches = []
        for c in range(1, nc):
            ys, xs = np.nonzero(clab == c)
            pix = set(zip(xs.tolist(), ys.tolist()))
            ends = [p for p in pix if sum((p[0] + dx, p[1] + dy) in pix for dy, dx in _NB) <= 1]
            if not ends:  # loop tertutup tanpa simpul
                start = next(iter(pix))
                pts = _walk(start, pix)
                self.branches.append(Branch(pts, None, None))
                continue
            pts = _walk(ends[0], pix)
            left = pix - set(pts)
            if len(left) >= 3:   # komponen bercabang yang lolos deteksi: simpan sisanya sebagai cabang
                lab2 = np.zeros_like(chains)
                for (x, y) in left:
                    lab2[y, x] = 1
                n2, l2 = cv2.connectedComponents(lab2, 8)
                for c2 in range(1, n2):
                    yy, xx = np.nonzero(l2 == c2)
                    sub = set(zip(xx.tolist(), yy.tolist()))
                    e2 = [q for q in sub if sum((q[0] + dx, q[1] + dy) in sub for dy, dx in _NB) <= 1] or [next(iter(sub))]
                    sp = _walk(e2[0], sub)
                    if len(sp) >= 2:
                        aa = self._attach(sp[0], jlab, jnode, nb)
                        bb = self._attach(sp[-1], jlab, jnode, nb)
                        self.branches.append(Branch([(float(x), float(y)) for x, y in sp], aa, bb))
            a = self._attach(pts[0], jlab, jnode, nb)
            b = self._attach(pts[-1], jlab, jnode, nb)
            if a is not None and self.kind[a] == "J":
                pts = [self.nodes[a]] + pts
            if b is not None and self.kind[b] == "J":
                pts = pts + [self.nodes[b]]
            self.branches.append(Branch([(float(x), float(y)) for x, y in pts], a, b))
        # cabang langsung J–J (piksel percabangan bersebelahan) tidak punya rantai; abaikan

    def _attach(self, p, jlab, jnode, nb):
        x, y = p
        h, w = jlab.shape
        for dy, dx in _NB:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and jlab[yy, xx] > 0:
                return jnode[jlab[yy, xx]]
        self.nodes.append((float(x), float(y)))
        self.kind.append("E")
        return len(self.nodes) - 1

    # --- utilitas ---
    def degree(self, n):
        return sum((br.a == n) + (br.b == n) for br in self.branches)

    def total_length(self):
        return sum(br.length for br in self.branches)


def _walk(start, pix):
    path = [start]
    seen = {start}
    cur = start
    while True:
        nxt = None
        # utamakan tetangga 4-arah agar jalur tidak melompat
        for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            q = (cur[0] + dx, cur[1] + dy)
            if q in pix and q not in seen:
                nxt = q
                break
        if nxt is None:
            break
        path.append(nxt)
        seen.add(nxt)
        cur = nxt
    return path


# =============================================================================
# 4. Besaran geometri
# =============================================================================
def path_length(pts):
    if len(pts) < 2:
        return 0.0
    a = np.asarray(pts, np.float32)
    return float(np.sum(np.hypot(*(a[1:] - a[:-1]).T)))


def angle_deg(p, q):
    """Arah garis p→q dalam derajat 0–180, konvensi manual VMI (y ke bawah):
    garis '/' ≈ 135°, garis '\\' ≈ 45°, mendatar 0°/180°, tegak 90°."""
    a = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
    return a % 180.0


def ang_diff(a, b):
    """selisih dua arah garis (0–90)"""
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def fit_angle(pts):
    a = np.asarray(pts, np.float32).reshape(-1, 1, 2)
    if len(a) < 2:
        return 0.0
    vx, vy, _, _ = cv2.fitLine(a, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    return math.degrees(math.atan2(vy, vx)) % 180.0


def local_dirs(pts, step=12):
    """(arah, panjang) segmen-segmen pendek sepanjang jalur"""
    out = []
    n = len(pts)
    if n < 2:
        return out
    step = max(1, min(step, n - 1))
    i = 0
    while i < n - 1:
        j = min(n - 1, i + step)
        L = math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
        if L > 0:
            out.append((angle_deg(pts[i], pts[j]), L))
        i = j
    return out


def fraction_within(paths, ok):
    """Proporsi panjang goresan yang arahnya memenuhi fungsi ok(arah)."""
    tot = good = 0.0
    for pts in paths:
        for a, L in local_dirs(pts):
            tot += L
            if ok(a):
                good += L
    return good / tot if tot else 0.0


def chord(pts):
    return math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])


def straightness(pts):
    """chord / panjang jalur (jalur dihaluskan dulu agar pola tangga piksel tidak dihitung)."""
    if len(pts) < 2:
        return 0.0
    a = np.asarray(pts, np.float32).reshape(-1, 1, 2)
    sm = cv2.approxPolyDP(a, 1.2, False).reshape(-1, 2)
    L = path_length([tuple(q) for q in sm])
    return chord(pts) / L if L else 0.0


def line_intersection(p1, d1, p2, d2):
    """Perpotongan dua garis tak hingga (titik + arah satuan)."""
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


def unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def direction_from(pts, L):
    """Arah satuan dari titik pertama ke titik yang berjarak ~L di sepanjang jalur."""
    acc = 0.0
    for i in range(1, len(pts)):
        acc += dist(pts[i - 1], pts[i])
        if acc >= L:
            return unit((pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    return unit((pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]))


def turns(pts, eps_rel=0.06, min_seg_rel=0.12):
    """Belokan tajam: sudut belok (derajat) di titik-titik sudut poligon aproksimasi,
    hanya jika kedua segmen yang mengapitnya cukup panjang."""
    L = path_length(pts)
    if L <= 0 or len(pts) < 3:
        return []
    a = np.asarray(pts, np.float32).reshape(-1, 1, 2)
    ap = cv2.approxPolyDP(a, eps_rel * L, False).reshape(-1, 2)
    out = []
    for i in range(1, len(ap) - 1):
        u = ap[i] - ap[i - 1]
        v = ap[i + 1] - ap[i]
        nu, nv = np.hypot(*u), np.hypot(*v)
        if nu < min_seg_rel * L or nv < min_seg_rel * L:
            continue
        cosang = float(np.dot(u, v) / (nu * nv))
        out.append((math.degrees(math.acos(max(-1.0, min(1.0, cosang)))), tuple(ap[i])))
    return out


# =============================================================================
# 5. Struktur "silang": simpul pusat + kaki-kaki
# =============================================================================
class Leg:
    """Kaki = jalur dari pusat silang ke ujung terjauh (menelusuri cabang yang searah)."""

    def __init__(self, pts):
        self.pts = pts
        self.length = path_length(pts)
        self.tip = pts[-1]

    def dir(self, frac=0.6):
        return direction_from(self.pts, max(4.0, self.length * frac))

    def angle(self):
        return fit_angle(self.pts)


def merged_center(graph, radius):
    """Gabungkan simpul percabangan yang berdekatan (radius) → kelompok.
    Mengembalikan daftar (pusat, set simpul) diurutkan dari derajat terbesar."""
    J = [i for i, k in enumerate(graph.kind) if k == "J"]
    groups = []
    used = set()
    for i in J:
        if i in used:
            continue
        g = {i}
        stack = [i]
        while stack:
            a = stack.pop()
            for b in J:
                if b not in g and dist(graph.nodes[a], graph.nodes[b]) <= radius:
                    g.add(b)
                    stack.append(b)
        used |= g
        pts = [graph.nodes[k] for k in g]
        c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        groups.append((c, g))
    return groups


def legs_from(graph, group, min_len, follow_tol=35.0):
    """Kaki-kaki yang keluar dari kelompok simpul pusat. Kaki diteruskan melewati
    percabangan lain bila ada cabang lanjutan yang searah (≤ follow_tol), sehingga
    kepala panah/duri kecil tidak memutus kaki."""
    legs = []
    for br in graph.branches:
        inside_a = br.a in group
        inside_b = br.b in group
        if inside_a and inside_b:
            continue  # cabang internal antar-simpul pusat
        if not (inside_a or inside_b):
            continue
        start = br.a if inside_a else br.b
        pts = list(br.from_node(start))
        node = br.other(start)
        visited = {id(br)}
        while node is not None and graph.kind[node] == "J":
            d_in = direction_from(pts[::-1], 12)        # arah datang (dari ujung mundur)
            d_in = (-d_in[0], -d_in[1])
            best, best_dev = None, follow_tol
            for nb in graph.branches:
                if id(nb) in visited or (nb.a != node and nb.b != node) or nb.a is None:
                    continue
                seg = nb.from_node(node)
                d_out = direction_from(seg, 12)
                dev = math.degrees(math.acos(max(-1, min(1, d_in[0] * d_out[0] + d_in[1] * d_out[1]))))
                if dev < best_dev:
                    best, best_dev = nb, dev
            if best is None:
                break
            visited.add(id(best))
            pts += list(best.from_node(node))[1:]
            node = best.other(node)
        if path_length(pts) >= min_len:
            legs.append(Leg(pts))
    return legs


def pair_legs(legs, k):
    """Pasangkan kaki menjadi k garis (pasangan paling berlawanan arah)."""
    import itertools
    best, best_cost = None, 1e9
    idx = list(range(len(legs)))
    if len(legs) != 2 * k:
        return None
    def pairings(items):
        if not items:
            yield []
            return
        a = items[0]
        for i in range(1, len(items)):
            b = items[i]
            rest = items[1:i] + items[i + 1:]
            for p in pairings(rest):
                yield [(a, b)] + p
    for pr in pairings(idx):
        cost = 0.0
        for a, b in pr:
            da, db = legs[a].dir(), legs[b].dir()
            dot = da[0] * db[0] + da[1] * db[1]
            cost += math.degrees(math.acos(max(-1, min(1, -dot))))  # 0 = tepat berlawanan
        if cost < best_cost:
            best, best_cost = pr, cost
    return [(legs[a], legs[b]) for a, b in best], best_cost / k


def line_of(pair):
    """Gabungkan dua kaki (berlawanan) menjadi satu garis: titik berurutan ujung→ujung."""
    a, b = pair
    return list(a.pts[::-1]) + list(b.pts[1:])


# =============================================================================
# 6. Loop (lengkung tertutup)
# =============================================================================
def loops(mask, min_rel=0.04):
    """Lubang di dalam goresan = lengkung tertutup. Mengembalikan daftar dict
    (kontur lubang, kotak minAreaRect, rasio panjang:lebar, luas)."""
    cnts, hier = cv2.findContours(mask.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    if hier is None:
        return out
    H, W = mask.shape
    side = max(H, W)
    for c, hh in zip(cnts, hier[0]):
        if hh[3] < 0:
            continue  # bukan lubang
        (cx, cy), (rw, rh), ang = cv2.minAreaRect(c)
        if min(rw, rh) < 2:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if max(w, h) < min_rel * side:
            continue
        out.append({"cnt": c, "center": (cx, cy), "w": w, "h": h, "rw": rw, "rh": rh,
                    "ratio": max(rw, rh) / max(1e-6, min(rw, rh)), "area": cv2.contourArea(c),
                    "bbox": (x, y, w, h)})
    out.sort(key=lambda d: -d["area"])
    return out


# =============================================================================
# 7. Laporan kriteria
# =============================================================================
def criterion(cid, ok, detail=""):
    return {"id": cid, "ok": bool(ok), "detail": detail}


def finish(checker_cls, img, crits, name):
    """Simpan laporan, tulis status (untuk GUI desktop), kembalikan (skor, gambar)."""
    ok = all(c["ok"] for c in crits)
    checker_cls.last_criteria = crits
    status = f"VALID: {name}" if ok else "INVALID: " + "; ".join(
        f"K{c['id']} {c['detail']}" for c in crits if not c["ok"])
    color = (0, 170, 0) if ok else (0, 0, 230)
    cv2.putText(img, status[:70], (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    for i, c in enumerate(crits):
        cv2.putText(img, f"K{c['id']}: {'OK' if c['ok'] else 'X'} {c['detail']}"[:70], (10, 56 + 24 * i),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 140, 0) if c["ok"] else (0, 0, 220), 1)
    return (1 if ok else 0), img


def error_result(checker_cls, msg, n_criteria):
    checker_cls.last_criteria = [criterion(1, False, msg)] + [
        criterion(i, False, "tidak dapat dinilai") for i in range(2, n_criteria + 1)]
    img = np.full((300, 520, 3), 255, np.uint8)
    cv2.putText(img, "INVALID: " + msg[:50], (12, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2)
    return 0, img


# =============================================================================
# 8. Goresan ("stroke"): cabang-cabang yang disambung lurus melewati percabangan
# =============================================================================
class Stroke:
    def __init__(self, pts):
        self.pts = pts
        self.length = path_length(pts)
        self.angle = fit_angle(pts) if len(pts) > 1 else 0.0
        self.a, self.b = pts[0], pts[-1]

    def dir(self):
        return unit((self.b[0] - self.a[0], self.b[1] - self.a[1]))


def strokes(graph, tol=32.0, merge_r=6.0, probe=14.0):
    """Susun goresan lurus: di tiap percabangan, pasangkan ujung-ujung cabang yang paling
    segaris (penyimpangan ≤ tol derajat). Percabangan yang berdekatan (≤ merge_r)
    dianggap satu titik (cabang pendek di antaranya dibuang)."""
    nodes = graph.nodes
    # 1) gabungkan percabangan yang berdekatan
    J = [i for i, k in enumerate(graph.kind) if k == "J"]
    rep = {i: i for i in range(len(nodes))}

    def find(i):
        while rep[i] != i:
            rep[i] = rep[rep[i]]
            i = rep[i]
        return i
    for br in graph.branches:
        if br.a is not None and graph.kind[br.a] == "J" and graph.kind[br.b] == "J" and br.length <= merge_r:
            rep[find(br.a)] = find(br.b)
    for i in J:
        for j in J:
            if i < j and dist(nodes[i], nodes[j]) <= merge_r:
                rep[find(i)] = find(j)
    brs = []
    for br in graph.branches:
        if br.a is None:
            brs.append((br.pts, None, None))
            continue
        a, b = find(br.a), find(br.b)
        if a == b and graph.kind[br.a] == "J" and br.length <= merge_r * 2:
            continue
        brs.append((br.pts, a, b))
    # 2) ujung-ujung cabang per simpul J
    ends = {}  # node -> list (branch_idx, side, dir_out)
    for k, (pts, a, b) in enumerate(brs):
        if a is None:
            continue
        for side, node in ((0, a), (1, b)):
            if graph.kind[node] != "J" and not any(find(j) == node for j in J):
                continue
            seg = pts if side == 0 else pts[::-1]
            ends.setdefault(node, []).append((k, side, direction_from(seg, probe)))
    link = {}  # (k, side) -> (k2, side2)
    for node, lst in ends.items():
        cand = []
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                if lst[i][0] == lst[j][0]:
                    continue
                d1, d2 = lst[i][2], lst[j][2]
                dev = math.degrees(math.acos(max(-1, min(1, -(d1[0] * d2[0] + d1[1] * d2[1])))))
                if dev <= tol:
                    cand.append((dev, i, j))
        cand.sort()
        used = set()
        for dev, i, j in cand:
            if i in used or j in used:
                continue
            used |= {i, j}
            a, b = lst[i][:2], lst[j][:2]
            link[a] = b
            link[b] = a
    # 3) telusuri
    seen = set()
    out = []
    for k, (pts, a, b) in enumerate(brs):
        if k in seen:
            continue
        if a is None:
            seen.add(k)
            out.append(Stroke(list(pts)))
            continue
        # mundur ke awal rantai lewat sisi 0
        cur, side = k, 0
        guard = 0
        while (cur, side) in link and guard < 50:
            nk, ns = link[(cur, side)]
            if nk == k:
                break
            cur, side = nk, 1 - ns
            guard += 1
        # sekarang telusuri maju dari (cur, side) sebagai awal
        chain = []
        c, s = cur, side
        guard = 0
        while guard < 50:
            seen.add(c)
            p = brs[c][0]
            seg = p if s == 0 else p[::-1]
            chain += seg if not chain else seg[1:]
            nxt = link.get((c, 1 - s))
            if nxt is None or nxt[0] in seen:
                break
            c, s = nxt
            guard += 1
        out.append(Stroke(chain))
    out.sort(key=lambda st: -st.length)
    return out


def seg_intersection(p1, p2, q1, q2, ext=0.0):
    """Perpotongan dua ruas garis (boleh diperpanjang ext × panjang di kedua ujung)."""
    d1 = (p2[0] - p1[0], p2[1] - p1[1]); d2 = (q2[0] - q1[0], q2[1] - q1[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((q1[0] - p1[0]) * d2[1] - (q1[1] - p1[1]) * d2[0]) / den
    u = ((q1[0] - p1[0]) * d1[1] - (q1[1] - p1[1]) * d1[0]) / den
    if -ext <= t <= 1 + ext and -ext <= u <= 1 + ext:
        return (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return None


def poly_intersection(A, B, ext=0.0):
    """Titik potong dua polyline (pertama yang ditemukan, cek ruas yang disederhanakan)."""
    def simp(P):
        a = np.asarray(P, np.float32).reshape(-1, 1, 2)
        return [tuple(map(float, q)) for q in cv2.approxPolyDP(a, 1.5, False).reshape(-1, 2)]
    a, b = simp(A), simp(B)
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            e = ext if (i in (0, len(a) - 2) or j in (0, len(b) - 2)) else 0.0
            p = seg_intersection(a[i], a[i + 1], b[j], b[j + 1], e)
            if p is not None:
                return p
    return None


def split_at(pts, p):
    """Pisahkan polyline pada titik terdekat dengan p → (bagian awal dibalik, bagian akhir),
    keduanya dimulai dari titik potong."""
    k = int(np.argmin([dist(q, p) for q in pts]))
    return [p] + list(pts[:k][::-1]), [p] + list(pts[k + 1:])


def point_to_poly(p, pts):
    return min(dist(p, q) for q in pts) if pts else 1e9


def draw_dirs(d, img, paths, ok, thick=3):
    """Gambar goresan: hijau bila arahnya memenuhi ok(arah), merah bila tidak."""
    for pts in paths:
        n = len(pts)
        step = 6
        for i in range(0, n - 1, step):
            j = min(n - 1, i + step)
            a = angle_deg(pts[i], pts[j])
            col = (40, 180, 40) if ok(a) else (40, 40, 220)
            cv2.line(img, d.P(pts[i]), d.P(pts[j]), col, thick, cv2.LINE_AA)


# =============================================================================
# 9. Analisis bentuk silang (dipakai Form 10, 14, 17, 18)
# =============================================================================
GREEN, RED, BLUE, ORANGE, PURPLE = (40, 170, 40), (40, 40, 225), (220, 120, 30), (0, 140, 255), (190, 60, 190)


def _inter_all(lines):
    inter = {}
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            p = poly_intersection(lines[i].pts, lines[j].pts, ext=0.06)
            if p is not None:
                inter[(i, j)] = p
    return inter


def cross_lines(d, n, min_line_rel=0.28):
    """Ambil n garis + titik-titik potongnya. Dua cara disusun lalu dipilih yang terbaik:
      (a) goresan lurus hasil penyambungan cabang di tiap percabangan;
      (b) kaki-kaki yang memancar dari pusat (gabungan percabangan dalam radius 12%)
          dipasangkan menjadi garis yang paling segaris.
    Mengembalikan dict: lines, extra (panjang goresan lain / total), inter (dict (i,j)→titik)."""
    sts = strokes(d.graph, merge_r=max(6.0, 2.5 * d.stroke))
    total = sum(s.length for s in sts) or 1.0
    long_ = [s for s in sts if s.length >= min_line_rel * d.size]
    cands = []
    lines = long_[:n]
    cands.append((lines, _inter_all(lines), len(long_), (total - sum(l.length for l in lines)) / total))
    # (b) kaki dari pusat
    for radius in (0.08, 0.14):
        groups = merged_center(d.graph, radius * d.size)
        for c, g in sorted(groups, key=lambda cg: -sum(d.graph.degree(k) for k in cg[1]))[:2]:
            legs = legs_from(d.graph, g, min_len=0.10 * d.size)
            if len(legs) != 2 * n:
                continue
            pr = pair_legs(legs, n)
            if pr is None or pr[1] > 35.0:
                continue
            L = [Stroke(line_of(p)) for p in pr[0]]
            used = sum(l.length for l in L)
            cands.append((sorted(L, key=lambda s: -s.length), None, n, max(0.0, (total - used) / total)))
    best = None
    for lines, inter, nlong, extra in cands:
        if inter is None:
            inter = _inter_all(lines)
        score = (len(lines) == n, len(inter), -extra)
        if best is None or score > best[0]:
            best = (score, lines, inter, nlong, extra)
    _, lines, inter, nlong, extra = best
    return {"strokes": sts, "lines": lines, "n_long": nlong, "extra": extra, "inter": inter, "total": total}


def legs_at(line, p):
    a, b = split_at(line.pts, p)
    return [Leg(a), Leg(b)]


# =============================================================================
# 10. Poligon (persegi / segitiga): sudut-sudut & sisi pada lengkung tertutup
# =============================================================================
def main_loop(d, close_rel=0.03, open_gap_rel=0.30):
    """Lengkung tertutup terbesar (setelah celah kecil ≤ close_rel ditutup).
    Jika bentuk belum tertutup (mis. sudut tidak bertemu), goresan terpanjang yang kedua
    ujungnya berdekatan (≤ open_gap_rel) ditutup dengan garis lurus.
    Mengembalikan dict {cnt, closed_by_gap} atau None."""
    k = max(3, int(close_rel * d.size)) | 1
    m = cv2.morphologyEx(d.mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    L = loops(m, min_rel=0.2)
    if L:
        return {"cnt": L[0]["cnt"], "gap": 0.0}, m
    # rangkai goresan-goresan (yang ujungnya berdekatan) menjadi satu keliling
    sts = [s for s in strokes(d.graph, merge_r=max(6.0, 2.5 * d.stroke)) if s.length >= 0.1 * d.size]
    if not sts:
        return None, m
    chain = list(sts[0].pts)
    rest = sts[1:]
    gaps = []
    while rest:
        best = None
        for i, s in enumerate(rest):
            for rev in (False, True):
                p = s.pts[::-1] if rev else s.pts
                g = dist(chain[-1], p[0])
                if best is None or g < best[0]:
                    best = (g, i, p)
        if best[0] > open_gap_rel * d.size:
            break
        gaps.append(best[0])
        chain += list(best[2])
        rest.pop(best[1])
    g = dist(chain[0], chain[-1])
    if g <= open_gap_rel * d.size and path_length(chain) >= 2 * d.size:
        cnt = np.array(chain, np.float32).reshape(-1, 1, 2).astype(np.int32)
        return {"cnt": cnt, "gap": max(gaps + [g]) / d.size}, m
    return None, m


def polygon(cnt, eps_rel=0.03, min_side_rel=0.10, min_turn=28.0):
    """Sederhanakan kontur tertutup menjadi titik-titik sudut yang jelas.
    Sudut bulat (rounded corner) digabung menjadi satu sudut; titik yang hampir lurus dibuang."""
    c = cnt.reshape(-1, 2).astype(np.float32)
    peri = cv2.arcLength(cnt, True)
    V = [tuple(map(float, p)) for p in cv2.approxPolyDP(cnt, eps_rel * peri, True).reshape(-1, 2)]
    changed = True
    while changed and len(V) > 2:
        changed = False
        n = len(V)
        # gabungkan sisi yang terlalu pendek
        lens = [dist(V[i], V[(i + 1) % n]) for i in range(n)]
        i = int(np.argmin(lens))
        if lens[i] < min_side_rel * peri:
            a, b = V[i], V[(i + 1) % n]
            V[i] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            del V[(i + 1) % n]
            changed = True
            continue
        # buang titik yang hampir lurus
        for i in range(n):
            p0, p1, p2 = V[i - 1], V[i], V[(i + 1) % n]
            u = (p1[0] - p0[0], p1[1] - p0[1]); v = (p2[0] - p1[0], p2[1] - p1[1])
            nu, nv = math.hypot(*u), math.hypot(*v)
            if nu and nv:
                turn = math.degrees(math.acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / (nu * nv)))))
                if turn < min_turn:
                    del V[i]
                    changed = True
                    break
    return V, peri


def side_bulge(cnt, V):
    """Untuk tiap sisi (V[i]→V[i+1]): simpangan maksimum kontur dari garis lurus / panjang sisi."""
    c = cnt.reshape(-1, 2).astype(np.float32)
    idx = [int(np.argmin(np.hypot(c[:, 0] - v[0], c[:, 1] - v[1]))) for v in V]
    out = []
    n = len(V)
    for k in range(n):
        i, j = idx[k], idx[(k + 1) % n]
        seg = c[i:j + 1] if i <= j else np.vstack([c[i:], c[:j + 1]])
        p, q = np.array(V[k]), np.array(V[(k + 1) % n])
        L = np.hypot(*(q - p))
        if L < 1 or len(seg) < 3:
            out.append(0.0)
            continue
        dv = (q - p) / L
        dev = np.abs((seg[:, 0] - p[0]) * dv[1] - (seg[:, 1] - p[1]) * dv[0])
        out.append(float(dev.max() / L))
    return out


def side_straight(cnt, V, tol=0.06):
    """Untuk tiap sisi: proporsi titik kontur yang berjarak ≤ tol×panjang sisi dari garis lurus.
    Sisi lurus (meski ujungnya sedikit membengkok) ≈ 1; sisi berupa busur ≈ rendah."""
    c = cnt.reshape(-1, 2).astype(np.float32)
    idx = [int(np.argmin(np.hypot(c[:, 0] - v[0], c[:, 1] - v[1]))) for v in V]
    out = []
    n = len(V)
    for k in range(n):
        i, j = idx[k], idx[(k + 1) % n]
        seg = c[i:j + 1] if i <= j else np.vstack([c[i:], c[:j + 1]])
        p, q = np.array(V[k]), np.array(V[(k + 1) % n])
        L = np.hypot(*(q - p))
        if L < 1 or len(seg) < 3:
            out.append(1.0)
            continue
        dv = (q - p) / L
        dev = np.abs((seg[:, 0] - p[0]) * dv[1] - (seg[:, 1] - p[1]) * dv[0])
        out.append(float(np.mean(dev <= tol * L)))
    return out


def total_turning(pts, step=8):
    """Total belokan (derajat, bertanda) sepanjang jalur — 360° = satu putaran penuh."""
    dirs = [math.atan2(pts[j][1] - pts[i][1], pts[j][0] - pts[i][0])
            for i, j in ((k, min(len(pts) - 1, k + step)) for k in range(0, len(pts) - 1, step))]
    tot = 0.0
    for a, b in zip(dirs, dirs[1:]):
        d = (b - a + math.pi) % (2 * math.pi) - math.pi
        tot += d
    return math.degrees(tot)


def clear_sides(cnt, V, max_bulge=0.13, min_straight=0.27):
    """Sisi 'jelas' = hampir lurus (simpangan ≤ max_bulge) ATAU sebagian besar lurus
    (≥ min_straight titiknya dekat garis lurus, mis. hanya ujung sudut yang membulat).
    Mengembalikan daftar (ok, bulge, straight) per sisi."""
    b = side_bulge(cnt, V)
    st = side_straight(cnt, V)
    return [(bb <= max_bulge or ss >= min_straight, bb, ss) for bb, ss in zip(b, st)]


def corner_turns(V):
    """Sudut belok (derajat) di tiap titik sudut poligon."""
    out = []
    n = len(V)
    for i in range(n):
        p0, p1, p2 = V[i - 1], V[i], V[(i + 1) % n]
        u = (p1[0] - p0[0], p1[1] - p0[1]); v = (p2[0] - p1[0], p2[1] - p1[1])
        nu, nv = math.hypot(*u), math.hypot(*v)
        out.append(math.degrees(math.acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / (nu * nv))))) if nu and nv else 0.0)
    return out


def fitted_line(pts):
    a = np.asarray(pts, np.float32).reshape(-1, 1, 2)
    vx, vy, x0, y0 = cv2.fitLine(a, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    return (float(x0), float(y0)), (float(vx), float(vy))


def fitted_intersections(lines):
    """Titik potong antar garis lurus hasil fitting (untuk mengukur 'celah' di pusat)."""
    F = [fitted_line(l.pts) for l in lines]
    out = {}
    for i in range(len(F)):
        for j in range(i + 1, len(F)):
            p = line_intersection(F[i][0], F[i][1], F[j][0], F[j][1])
            if p is not None:
                out[(i, j)] = p
    return out


def max_bend(pts):
    """Belokan terbesar (derajat) pada garis yang disederhanakan."""
    t = turns(pts, eps_rel=0.05, min_seg_rel=0.15)
    return max((a for a, _ in t), default=0.0)


def split_sharp(sts, min_turn=55.0, min_piece=4.0):
    """Pecah goresan pada belokan tajam (mis. batang panah yang langsung diteruskan
    menjadi ujung panah tanpa mengangkat pensil)."""
    out = []
    for st in sts:
        pts = st.pts
        if len(pts) < 8:
            out.append(st)
            continue
        a = np.asarray(pts, np.float32).reshape(-1, 1, 2)
        ap = cv2.approxPolyDP(a, max(2.0, 0.03 * st.length), False).reshape(-1, 2)
        cut = []
        for i in range(1, len(ap) - 1):
            u = ap[i] - ap[i - 1]; v = ap[i + 1] - ap[i]
            nu, nv = np.hypot(*u), np.hypot(*v)
            if nu < min_piece or nv < min_piece:
                continue
            ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(u, v) / (nu * nv))))))
            if ang >= min_turn:
                k = int(np.argmin([dist(q, tuple(ap[i])) for q in pts]))
                cut.append(k)
        prev = 0
        for k in sorted(set(cut)):
            if k - prev >= 2:
                out.append(Stroke(pts[prev:k + 1]))
            prev = k
        if len(pts) - prev >= 2:
            out.append(Stroke(pts[prev:]))
    out.sort(key=lambda s: -s.length)
    return out
