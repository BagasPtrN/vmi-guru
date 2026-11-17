"""Logika bersama Form 11 (garis miring kanan /) dan Form 13 (garis miring kiri \\).
Kriteria manual:
  1. Garis "tunggal" (perpanjangan boleh).
  2. Minimal 1/2 garis berada dalam rentang sudut (Form 11: 110°–160°, Form 13: 20°–70°).
  3. Tidak ada perubahan arah yang mendadak.
"""
from symbols import _vmi_geom as G

MAIN_SHARE = 0.80      # goresan utama (+ perpanjangan segaris) ≥ 80% total goresan
EXT_ANGLE = 20.0       # perpanjangan / goresan ulang: arah selisih ≤ 20° ...
EXT_OFFSET = 0.08      # ... dan ujung terdekatnya ≤ 8% ukuran gambar dari garis utama
ABRUPT_DEG = 30.0      # belokan > 30° (pada ruas yang cukup panjang) = perubahan arah mendadak
MIN_FRACTION = 0.5


def check_oblique(C, image_path, lo, hi, name):
    try:
        img = G.load(image_path)
        d = G.Drawing(img)
    except Exception as e:
        return G.error_result(C, str(e), 3)
    vis = img.copy()
    sts = G.strokes(d.graph, merge_r=max(6.0, 2.5 * d.stroke))
    main = sts[0]
    total = sum(s.length for s in sts) or 1.0
    # perpanjangan: goresan lain yang segaris dengan goresan utama
    m_ang = main.angle
    p0 = (sum(q[0] for q in main.pts) / len(main.pts), sum(q[1] for q in main.pts) / len(main.pts))
    nrm = (-G.math.sin(G.math.radians(m_ang)), G.math.cos(G.math.radians(m_ang)))
    line_pts = [main.pts]
    used = main.length
    for s in sts[1:]:
        off = min(abs((q[0] - p0[0]) * nrm[0] + (q[1] - p0[1]) * nrm[1]) for q in (s.a, s.b))
        if G.ang_diff(s.angle, m_ang) <= EXT_ANGLE and off <= EXT_OFFSET * d.size:
            line_pts.append(s.pts)
            used += s.length
    loops = G.loops(d.mask, min_rel=0.06)
    share = used / total
    single = share >= MAIN_SHARE and not loops
    # 2. sudut
    ok_dir = lambda a: lo <= a <= hi
    frac = G.fraction_within(line_pts, ok_dir)
    # 3. belokan mendadak pada goresan utama
    tr = G.turns(main.pts, eps_rel=0.05, min_seg_rel=0.12)
    abrupt = [t for t in tr if t[0] > ABRUPT_DEG]
    # visual
    for s in sts:
        if all(s.pts is not lp for lp in line_pts):
            d.polyline(vis, s.pts, G.ORANGE, 3)
    G.draw_dirs(d, vis, line_pts, ok_dir)
    for ang, p in abrupt:
        d.dot(vis, p, G.PURPLE, 10)
    crits = [
        G.criterion(1, single, ("garis tunggal" if single else
                                (f"ada lengkung/coretan berulang" if loops else
                                 f"goresan utama hanya {share * 100:.0f}% (ada garis lain)"))),
        G.criterion(2, frac >= MIN_FRACTION, f"{frac * 100:.0f}% garis dalam {lo:.0f}°–{hi:.0f}°"),
        G.criterion(3, not abrupt, (f"belokan tajam {max(a for a, _ in abrupt):.0f}°" if abrupt else "tidak ada belokan tajam")),
    ]
    return G.finish(C, vis, crits, name)
