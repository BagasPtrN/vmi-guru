"""Form 26 — Belah ketupat mendatar (Horizontal Diamond).
Kriteria manual:
  1. Empat sudut yang baik (bukaan < 1/16 inci).
  2. Kedua sudut lancip 60° atau kurang.
  3. Sumbu mendatar dalam 170°–190°.
  4. Sisi terpendek minimal 2/3 sisi terpanjang.
"""
import sys
from symbols import _vmi_geom as G
from symbols import _diamond as D


class HorizontalDiamondChecker:
    last_criteria = []

    @classmethod
    def check(cls, image_path):
        C = cls
        try:
            img = G.load(image_path)
            d = G.Drawing(img)
        except Exception as e:
            return G.error_result(C, str(e), 4)
        vis = img.copy()
        A = D.analyse(d)
        ok1, det1 = D.corners_ok(A)
        if A is None or len(A["V"]) != 4:
            crits = [G.criterion(1, ok1, det1)] + [G.criterion(k, False, "tidak dapat dinilai (bukan 4 sudut)") for k in (2, 3, 4)]
            if A is not None:
                D.draw(d, vis, A, False)
            return G.finish(C, vis, crits, "Horizontal diamond")
        ok2, det2 = D.acute(A)
        top, bot = min(A["V"], key=lambda p: p[1]), max(A["V"], key=lambda p: p[1])
        ok3, det3, lr = D.axis(A, False)
        if (bot[1] - top[1]) > (lr[1][0] - lr[0][0]):
            ok2, det2 = False, det2 + "; bentuk lebih tinggi daripada lebar"
        ok4, det4 = D.sides(A)
        D.draw(d, vis, A, all([ok1, ok2, ok3, ok4]))
        d.polyline(vis, list(lr), G.GREEN if ok3 else G.RED, 2)
        crits = [G.criterion(1, ok1, det1), G.criterion(2, ok2, det2), G.criterion(3, ok3, det3), G.criterion(4, ok4, det4)]
        return G.finish(C, vis, crits, "Horizontal diamond")


if __name__ == "__main__":
    print(HorizontalDiamondChecker.check(sys.argv[1])[0], HorizontalDiamondChecker.last_criteria)
