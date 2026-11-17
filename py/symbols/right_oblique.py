"""Form 11 — Garis miring kanan (/). Sudut 110°–160° (konvensi manual, sumbu y ke bawah)."""
import sys
from symbols._oblique import check_oblique


class RightObliqueChecker:
    ANGLE_RANGE = (110.0, 160.0)
    last_criteria = []

    @staticmethod
    def check(image_path):
        return check_oblique(RightObliqueChecker, image_path, *RightObliqueChecker.ANGLE_RANGE, "Right oblique line")


if __name__ == "__main__":
    print(RightObliqueChecker.check(sys.argv[1])[0], RightObliqueChecker.last_criteria)
