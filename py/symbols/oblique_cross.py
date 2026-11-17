import cv2
import numpy as np
import math
import sys

class ObliqueCrossChecker:
    """
    Kelas yang berisi metode statis untuk mendeteksi dan memvalidasi objek
    berbentuk silang miring (oblique cross) dari sebuah gambar.
    """

    # =================================================================================
    # KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    _MAX_DIMENSION = 1000
    _BLUR_FACTOR = 0.01
    _CLOSING_KERNEL_FACTOR = 0.02
    _PERI_APPROX_FACTOR = 0.028
    _POINT_MERGE_THRESHOLD = 80
    _MIN_CONTOUR_AREA = 500
    _ROI_WIDTH_FACTOR = 0.20
    _HOUGH_THRESHOLD = 15
    _HOUGH_MIN_LENGTH_FACTOR = 0.08
    _HOUGH_MAX_GAP = 40
    _ANGLE_DIFF_THRESHOLD = 5.0
       
    # --- RENTANG SUDUT BARU UNTUK SILANG MIRING (OBLIQUE) ---
    # Grup 1: Garis miring ke kanan (/)
    _OBLIQUE_1_MIN = 20
    _OBLIQUE_1_MAX = 70
    # Grup 2: Garis miring ke kiri (\)
    _OBLIQUE_2_MIN = 110
    _OBLIQUE_2_MAX = 160

    # =================================================================================
    # METODE BANTU UNTUK VISUALISASI DAN GEOMETRI
    # =================================================================================
    @staticmethod
    def draw_dashed_line(img, pt1, pt2, color, thickness=1, dash_length=10):
        """Menggambar garis putus-putus pada gambar."""
        dist = ((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)**0.5
        dashes = int(dist / dash_length)
        if dashes == 0:
            return
        for i in range(dashes):
            start = [int(pt1[0] + (pt2[0] - pt1[0]) * i / dashes), int(pt1[1] + (pt2[1] - pt1[1]) * i / dashes)]
            end = [int(pt1[0] + (pt2[0] - pt1[0]) * (i + 0.5) / dashes), int(pt1[1] + (pt2[1] - pt1[1]) * (i + 0.5) / dashes)]
            cv2.line(img, tuple(start), tuple(end), color, thickness)

    @staticmethod
    def draw_dashed_poly(img, points, color, thickness=1):
        """Menggambar poligon putus-putus pada gambar."""
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            ObliqueCrossChecker.draw_dashed_line(img, tuple(p1), tuple(p2), color, thickness)

    @staticmethod
    def _on_segment(p, q, r):
        """Memeriksa apakah titik q terletak pada segmen garis pr."""
        return (q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and
                q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1]))

    @staticmethod
    def _orientation(p, q, r):
        """Menentukan orientasi triplet (p, q, r)."""
        val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if val == 0: return 0
        return 1 if val > 0 else 2

    @staticmethod
    def check_intersection(p1, q1, p2, q2):
        """Memeriksa apakah segmen garis 'p1q1' dan 'p2q2' berpotongan."""
        o1 = ObliqueCrossChecker._orientation(p1, q1, p2)
        o2 = ObliqueCrossChecker._orientation(p1, q1, q2)
        o3 = ObliqueCrossChecker._orientation(p2, q2, p1)
        o4 = ObliqueCrossChecker._orientation(p2, q2, q1)

        if o1 != o2 and o3 != o4:
            return True
        return False

    @staticmethod
    def _get_intersection_point(line1, line2):
        """Menghitung titik potong antara dua segmen garis jika ada."""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
        if 0 < t < 1 and 0 < u < 1:
            intersect_x = int(x1 + t * (x2 - x1))
            intersect_y = int(y1 + t * (y2 - y1))
            return (intersect_x, intersect_y)
        return None

    @staticmethod
    def _calculate_angle(line):
        """Menghitung sudut garis dalam rentang 0-180 derajat."""
        x1, y1, x2, y2 = line
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        return angle + 180 if angle < 0 else angle

    # =================================================================================
    # METODE UNTUK KONDISI SUDUT (TELAH DIMODIFIKASI)
    # =================================================================================
    @staticmethod
    def _is_in_oblique_group1(angle):
        """Memeriksa apakah sudut berada di Grup Miring 1 (20-70 derajat)."""
        return (ObliqueCrossChecker._OBLIQUE_1_MIN <= angle <= ObliqueCrossChecker._OBLIQUE_1_MAX)

    @staticmethod
    def _is_in_oblique_group2(angle):
        """Memeriksa apakah sudut berada di Grup Miring 2 (110-160 derajat)."""
        return (ObliqueCrossChecker._OBLIQUE_2_MIN <= angle <= ObliqueCrossChecker._OBLIQUE_2_MAX)

    # =================================================================================
    # LOGIKA INTI UNTUK DETEKSI
    # =================================================================================
    @staticmethod
    def is_four_sided(approx):
        """Memeriksa apakah aproksimasi poligon memiliki empat sisi."""
        return len(approx) == 4

    @staticmethod
    def check(image_path):
        """Fungsi utama untuk memproses gambar dan mendeteksi objek cross."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"Error: Gambar tidak ditemukan di path: {image_path}")
                return 0, np.zeros((300, 300, 3), dtype=np.uint8)

            if max(image.shape) > ObliqueCrossChecker._MAX_DIMENSION:
                scale = ObliqueCrossChecker._MAX_DIMENSION / max(image.shape)
                image = cv2.resize(image, (0, 0), fx=scale, fy=scale)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur_size = max(3, int(min(gray.shape) * ObliqueCrossChecker._BLUR_FACTOR))
            if blur_size % 2 == 0: blur_size += 1
            blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            closing_kernel_size = max(3, int(min(gray.shape) * ObliqueCrossChecker._CLOSING_KERNEL_FACTOR))
            if closing_kernel_size % 2 == 0: closing_kernel_size += 1
            kernel = np.ones((closing_kernel_size, closing_kernel_size), np.uint8)
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            result = image.copy()
            final_status_text = "INVALID: Not a valid four-point object"
            is_fully_valid = False
            angle_line1, angle_line2 = None, None

            if not contours:
                cv2.putText(result, "No contours detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                return 0, result

            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            full_edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

            for cnt in contours:
                if cv2.contourArea(cnt) < ObliqueCrossChecker._MIN_CONTOUR_AREA:
                    continue
                hull = cv2.convexHull(cnt)
                peri = cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, ObliqueCrossChecker._PERI_APPROX_FACTOR * peri, True)
                if len(approx) > 0:
                    merged_points = []
                    for point in approx:
                        is_close = any(np.linalg.norm(point[0] - mp[0]) < ObliqueCrossChecker._POINT_MERGE_THRESHOLD for mp in merged_points)
                        if not is_close:
                            merged_points.append(point)
                    approx = np.array(merged_points)

                if ObliqueCrossChecker.is_four_sided(approx):
                    points = approx.reshape(4, 2)
                    groups = [(points[0], points[2]), (points[1], points[3])]
                    all_roi_lines = []
                    for pt1, pt2 in groups:
                        patokan_color = (255, 0, 255)
                        cv2.circle(result, tuple(pt1.astype(int)), 8, patokan_color, -1)
                        cv2.circle(result, tuple(pt2.astype(int)), 8, patokan_color, -1)
                        cv2.circle(result, tuple(pt1.astype(int)), 9, (255, 255, 255), 2)
                        cv2.circle(result, tuple(pt2.astype(int)), 9, (255, 255, 255), 2)
                        length = np.linalg.norm(pt1 - pt2)
                        center = (pt1 + pt2) / 2
                        width_roi = length * ObliqueCrossChecker._ROI_WIDTH_FACTOR
                        angle_deg = math.degrees(math.atan2(pt2[1] - pt1[1], pt2[0] - pt1[0]))
                        rect = (tuple(center), (length, width_roi), angle_deg)
                        box = np.intp(cv2.boxPoints(rect))
                        ObliqueCrossChecker.draw_dashed_poly(result, box, color=(255, 120, 0), thickness=2)
                        mask = np.zeros(gray.shape, dtype=np.uint8)
                        cv2.fillConvexPoly(mask, box, 255)
                        roi_edges = cv2.bitwise_and(full_edges, full_edges, mask=mask)
                        lines = cv2.HoughLinesP(roi_edges, 1, np.pi / 180, threshold=ObliqueCrossChecker._HOUGH_THRESHOLD, minLineLength=int(length * ObliqueCrossChecker._HOUGH_MIN_LENGTH_FACTOR), maxLineGap=ObliqueCrossChecker._HOUGH_MAX_GAP)
                        all_roi_lines.append(lines)
                        if lines is not None:
                            for line in lines:
                                x1, y1, x2, y2 = line[0]
                                cv2.line(result, (x1, y1), (x2, y2), (255, 255, 0), 1)
                    
                    main_intersecting_pair = None
                    max_len_in_pair = 0
                    if len(all_roi_lines) == 2 and all_roi_lines[0] is not None and all_roi_lines[1] is not None:
                        for line1 in all_roi_lines[0]:
                            for line2 in all_roi_lines[1]:
                                p1, q1 = (line1[0][0], line1[0][1]), (line1[0][2], line1[0][3])
                                p2, q2 = (line2[0][0], line2[0][1]), (line2[0][2], line2[0][3])
                                if ObliqueCrossChecker.check_intersection(p1, q1, p2, q2):
                                    angle1_rad = ObliqueCrossChecker._calculate_angle(line1[0])
                                    angle2_rad = ObliqueCrossChecker._calculate_angle(line2[0])
                                    if abs(angle1_rad - angle2_rad) > ObliqueCrossChecker._ANGLE_DIFF_THRESHOLD:
                                        len1 = np.linalg.norm(np.array(p1) - np.array(q1))
                                        len2 = np.linalg.norm(np.array(p2) - np.array(q2))
                                        current_max = max(len1, len2)
                                        if current_max > max_len_in_pair:
                                            max_len_in_pair = current_max
                                            main_intersecting_pair = (line1[0], line2[0])
                    
                    if main_intersecting_pair is not None:
                        lineA, lineB = main_intersecting_pair
                        angle_line1 = ObliqueCrossChecker._calculate_angle(lineA)
                        angle_line2 = ObliqueCrossChecker._calculate_angle(lineB)

                        is_A_g1 = ObliqueCrossChecker._is_in_oblique_group1(angle_line1)
                        is_A_g2 = ObliqueCrossChecker._is_in_oblique_group2(angle_line1)
                        is_B_g1 = ObliqueCrossChecker._is_in_oblique_group1(angle_line2)
                        is_B_g2 = ObliqueCrossChecker._is_in_oblique_group2(angle_line2)

                        if not ((is_A_g1 and is_B_g2) or (is_A_g2 and is_B_g1)):
                            if (is_A_g1 and is_B_g1) or (is_A_g2 and is_B_g2):
                                final_status_text = "INVALID: Both lines in same oblique group"
                            else:
                                final_status_text = "INVALID: Line angles out of range"
                        else:
                            intersection_point = ObliqueCrossChecker._get_intersection_point(lineA, lineB)
                            if intersection_point:
                                # --- ATURAN BARU: Validasi Rasio Jarak Lengan ---
                                distances = [
                                    np.linalg.norm(p - np.array(intersection_point))
                                    for p in points
                                ]
                                
                                # Pastikan ada jarak untuk dihitung
                                if len(distances) == 4:
                                    min_dist = min(distances)
                                    max_dist = max(distances)

                                    # Jika jarak terpendek > 0 dan rasio valid
                                    if min_dist > 0 and max_dist <= 2 * min_dist:
                                        is_fully_valid = True
                                        final_status_text = "VALID: All rules passed"
                                    else:
                                        # Gagal karena rasio tidak terpenuhi
                                        final_status_text = "INVALID: Asymmetric arms (ratio > 2:1)"
                                else:
                                    # Kasus aneh jika tidak ada 4 jarak
                                    final_status_text = "INVALID: Measurement error"
                            else:
                                final_status_text = "INVALID: Lines do not intersect properly"
                        
                        cv2.line(result, (lineA[0], lineA[1]), (lineA[2], lineA[3]), (0, 255, 0), 3)
                        cv2.line(result, (lineB[0], lineB[1]), (lineB[2], lineB[3]), (0, 255, 0), 3)
                        cv2.putText(result, 'Garis 1', (lineA[2] + 15, lineA[3]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 3, cv2.LINE_AA)
                        cv2.putText(result, 'Garis 1', (lineA[2] + 15, lineA[3]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2, cv2.LINE_AA)
                        cv2.putText(result, 'Garis 2', (lineB[2] + 15, lineB[3]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 3, cv2.LINE_AA)
                        cv2.putText(result, 'Garis 2', (lineB[2] + 15, lineB[3]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2, cv2.LINE_AA)
                        intersection_point_vis = ObliqueCrossChecker._get_intersection_point(lineA, lineB)
                        if intersection_point_vis:
                            cv2.circle(result, intersection_point_vis, 8, (0, 0, 255), -1)
                            cv2.circle(result, intersection_point_vis, 10, (255, 255, 255), 2)
                        
                        break

            color = (0, 255, 0) if is_fully_valid else (0, 0, 255)
            cv2.putText(result, final_status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(result, f"Contours found: {len(contours)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            if angle_line1 is not None and angle_line2 is not None:
                angle_color = (0, 255, 0) if is_fully_valid else (0, 165, 255)
                cv2.putText(result, f"Garis 1: {angle_line1:.2f} derajat", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2)
                cv2.putText(result, f"Garis 2: {angle_line2:.2f} derajat", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, angle_color, 2)

            return 1 if is_fully_valid else 0, result

        except Exception as e:
            print(f"An error occurred during detection: {str(e)}")
            return 0, np.zeros((300, 300, 3), dtype=np.uint8)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_file_path = sys.argv[1]
        score, result_img = ObliqueCrossChecker.check(image_file_path)
        
        print(f"Path: {image_file_path}")
        print(f"Result Score: {score}")
        
        if result_img is not None and result_img.size > 0:
            cv2.imshow("Result", result_img)