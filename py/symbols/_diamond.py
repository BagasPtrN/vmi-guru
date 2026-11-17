"""Logika bersama Form 22 (belah ketupat tegak) dan Form 26 (belah ketupat mendatar)."""
import math
from symbols import _vmi_geom as G

OPEN_MAX = 0.05     # celah sudut ≤ 1/16 inci ≈ 5% ukuran gambar (asumsi bentuk ±1,25 inci)
AXIS_TOL = 10.0     # 170°–190°
ACUTE_MAX = 60.0
SIDE_RATIO = 2 / 3
DOG_TURN = 25.0


def analyse(d):
    loop, _ = G.main_loop(d, open_gap_rel=0.25)
    if loop is None:
        return None
    V, peri = G.polygon(loop["cnt"], eps_rel=0.03, min_side_rel=0.10, min_turn=30.0)
    fine, _ = G.polygon(loop["cnt"], eps_rel=0.009, min_side_rel=0.03, min_turn=DOG_TURN)
    return {"loop": loop, "V": V, "fine": fine}


def corners_ok(A):
    if A is None:
        return False, "bentuk tidak tertutup"
    n = len(A["V"])
    gap = A["loop"]["gap"]
    if n != 4:
        return False, f"{n} sudut jelas (harus 4)"
    if gap > OPEN_MAX:
        return False, f"sudut terbuka (celah {gap * 100:.0f}% ukuran gambar)"
    return True, "4 sudut tertutup"


def axis(A, vertical_diamond):
    """Sumbu mendatar = garis antara sudut kiri dan kanan."""
    V = A["V"]
    left, right = min(V, key=lambda p: p[0]), max(V, key=lambda p: p[0])
    ang = G.ang_diff(G.angle_deg(left, right), 0)
    return ang <= AXIS_TOL, f"sumbu mendatar miring {ang:.0f}° (maks 10°)", (left, right)


def acute(A):
    ia = sorted(G.interior_angles(A["V"]))
    a1, a2 = ia[0], ia[1]
    return a2 <= ACUTE_MAX + 2, f"dua sudut lancip {a1:.0f}° dan {a2:.0f}° (maks 60°)"


def sides(A):
    V = A["V"]
    L = [G.dist(V[i], V[(i + 1) % 4]) for i in range(4)]
    r = min(L) / max(L)
    return r >= SIDE_RATIO - 0.02, f"sisi terpendek {r * 100:.0f}% sisi terpanjang (min 67%)"


def dog_ears(A):
    extra = len(A["fine"]) - 4
    return extra <= 0, ("tidak ada 'telinga anjing'" if extra <= 0 else f"{extra} sudut tambahan (telinga anjing)")


def draw(d, vis, A, ok):
    V = A["V"]
    d.polyline(vis, [tuple(p) for p in A["loop"]["cnt"].reshape(-1, 2)], (170, 170, 170), 2)
    for i in range(len(V)):
        d.polyline(vis, [V[i], V[(i + 1) % len(V)]], G.GREEN if ok else G.RED, 3)
        d.dot(vis, V[i], G.BLUE, 7)
