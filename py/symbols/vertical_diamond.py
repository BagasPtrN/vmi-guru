"""Form 22 — Belah ketupat tegak (Vertical Diamond).
Kriteria manual:
  1. Empat sudut yang baik (bukaan < 1/16 inci).
  2. Sumbu mendatar dalam 170°–190°.
  3. Tidak ada "telinga anjing" (garis & sudut tambahan di pojok).
  4. Sisi terpendek minimal 2/3 sisi terpanjang.
  5. Kedua sudut lancip 60° atau kurang.
"""
import sys
from symbols import _vmi_geom as G
from symbols import _diamond as D


class VerticalDiamondChecker:
    last_criteria = []

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 5)
        vis = img.copy()
        A = D.analyse(d)
        ok1, det1 = D.corners_ok(A)
        if A is None or len(A["V"]) != 4:
            crits = [G.criterion(1, ok1, det1)] + [G.criterion(k, False, "tidak dapat dinilai (bukan 4 sudut)") for k in (2, 3, 4, 5)]
            if A is not None:
                D.draw(d, vis, A, False)
            return G.finish(C, vis, crits, "Vertical diamond")
        ok2, det2, lr = D.axis(A, True)
        ok3, det3 = D.dog_ears(A)
        ok4, det4 = D.sides(A)
        ok5, det5 = D.acute(A)
        # pada belah ketupat tegak, sudut lancip harus di atas & bawah
        top, bot = min(A["V"], key=lambda p: p[1]), max(A["V"], key=lambda p: p[1])
        if (bot[1] - top[1]) < (lr[1][0] - lr[0][0]):
            ok5, det5 = False, det5 + "; bentuk lebih lebar daripada tinggi"
        D.draw(d, vis, A, all([ok1, ok2, ok3, ok4, ok5]))
        d.polyline(vis, list(lr), G.GREEN if ok2 else G.RED, 2)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3),
                 G.criterion(4, ok4, det4), G.criterion(5, ok5, det5)]
        return G.finish(C, vis, crits, "Vertical diamond")


if __name__ == "__main__":
    print(VerticalDiamondChecker.check(sys.argv[1])[0], VerticalDiamondChecker.last_criteria)
