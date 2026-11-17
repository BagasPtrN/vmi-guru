"""Logika bersama untuk bentuk silang: Form 10 (+), 14 (×), 17 (✳) dan 18 (panah)."""
import math
from symbols import _vmi_geom as G

EXTRA_MAX = 0.15        # goresan lain (di luar garis utama) maks 15% total panjang goresan
MIN_LEG_REL = 0.06      # kaki minimal ≈ ¼ inci → 6% ukuran gambar (asumsi gambar ±4 inci terbesar)


def two_lines(d, C, extra_max=EXTRA_MAX):
    """Analisis 'dua garis berpotongan'. Mengembalikan dict ringkas + kriteria-1."""
    R = G.cross_lines(d, 2)
    lines, inter = R["lines"], R["inter"]
    p = inter.get((0, 1)) if len(lines) == 2 else None
    legs = []
    if p is not None:
        legs = G.legs_at(lines[0], p) + G.legs_at(lines[1], p)
    if len(lines) < 2:
        det, ok = f"hanya {len(lines)} garis panjang", False
    elif p is None:
        det, ok = "kedua garis tidak berpotongan", False
    elif R["n_long"] > 2 or R["extra"] > extra_max:
        det, ok = f"ada goresan tambahan ({R['extra'] * 100:.0f}% dari total)", False
    else:
        det, ok = "dua garis berpotongan", True
    return {"R": R, "lines": lines, "p": p, "legs": legs, "ok": ok, "det": det}


def legs_long_enough(legs, d, rel=MIN_LEG_REL):
    if len(legs) != 4:
        return False, "kaki tidak dapat diukur (garis tidak berpotongan)"
    m = min(l.length for l in legs) / d.size
    return m >= rel, f"kaki terpendek {m * 100:.0f}% ukuran gambar (min {rel * 100:.0f}%)"


MEASURE_TOL = 3.0       # toleransi ukur (kemiringan kertas/foto, tebal pensil)


def hv_within(lines, tol=20.0, need=0.5):
    """Satu garis mendatar & satu tegak. Lulus bila ≥ need bagian tiap garis berada dalam ±tol
    dari arah yang benar, atau arah rata-rata garis (garis lurus hasil fitting) dalam ±(tol+3°)."""
    if len(lines) < 2:
        return False, "garis kurang", []
    best = None
    for k, (hi, vi) in enumerate(((0, 1), (1, 0))):
        H, V = lines[hi], lines[vi]
        fh = G.fraction_within([H.pts], lambda a: G.ang_diff(a, 0) <= tol)
        fv = G.fraction_within([V.pts], lambda a: G.ang_diff(a, 90) <= tol)
        dh, dv = G.ang_diff(H.angle, 0), G.ang_diff(V.angle, 90)
        okh = fh >= need or dh <= tol + MEASURE_TOL
        okv = fv >= need or dv <= tol + MEASURE_TOL
        score = (okh + okv, -(dh + dv))
        if best is None or score > best[0]:
            best = (score, okh and okv, f"mendatar miring {dh:.0f}°, tegak miring {dv:.0f}° (maks {tol:.0f}°)",
                    [0, 1] if k == 0 else [1, 0])
    return best[1], best[2], best[3]


def draw_lines(d, vis, lines, ok_fn=None, col=G.GREEN):
    for l in lines:
        if ok_fn:
            G.draw_dirs(d, vis, [l.pts], ok_fn)
        else:
            d.polyline(vis, l.pts, col, 3)


def draw_extra(d, vis, R, lines):
    for s in R["strokes"]:
        if all(s is not l for l in lines) and s.length > 3:
            d.polyline(vis, s.pts, G.ORANGE, 2)
