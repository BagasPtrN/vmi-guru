"""Form 13 — Garis miring kiri (\\). Sudut 20°–70° (konvensi manual, sumbu y ke bawah)."""
import sys
from symbols._oblique import check_oblique


class LeftObliqueChecker:
    ANGLE_RANGE = (20.0, 70.0)
    last_criteria = []

    @staticmethod
    def check(image_path):
        return check_oblique(LeftObliqueChecker, image_path, *LeftObliqueChecker.ANGLE_RANGE, "Left oblique line")


if __name__ == "__main__":
    print(LeftObliqueChecker.check(sys.argv[1])[0], LeftObliqueChecker.last_criteria)
