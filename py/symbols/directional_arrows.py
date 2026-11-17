import cv2
import numpy as np
import math
import itertools
import sys
import traceback

class DirectionalArrowsChecker:
    """
    Kelas untuk mendeteksi cross utama dan kemudian memeriksa keberadaan
    panah dan celah di setiap ujungnya.
    Menggunakan metode berbasis kontur yang kokoh untuk deteksi cross awal.
    """

    # =================================================================================
    # KONSTANTA DETEKSI (Disamakan dengan CrossChecker)
    # =================================================================================
    _MAX_DIMENSION = 1000
    _BLUR_FACTOR = 0.01
    _CLOSING_KERNEL_FACTOR = 0.02
    _PERI_APPROX_FACTOR = 0.05
    _POINT_MERGE_THRESHOLD = 80
    _MIN_CONTOUR_AREA = 500
    _ROI_WIDTH_FACTOR = 0.20
    _HOUGH_THRESHOLD = 15
    _HOUGH_MIN_LENGTH_FACTOR = 0.08
    _HOUGH_MAX_GAP = 40
    _ANGLE_DIFF_THRESHOLD = 5.0
    _MIN_ENDPOINT_DISTANCE = 20
    
    _HORIZONTAL_ANGLE_MAX = 20
    _HORIZONTAL_ANGLE_MIN = 160
    _VERTICAL_ANGLE_MIN = 70
    _VERTICAL_ANGLE_MAX = 110

    # =================================================================================
    # METODE GEOMETRI DAN VISUALISASI
    # =================================================================================
    @staticmethod
    def _draw_dashed_line(img, pt1, pt2, color, thickness=1, dash_length=10):
        dist = ((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)**0.5
        dashes = int(dist / dash_length)
        if dashes == 0: return
        for i in range(dashes):
            start = [int(pt1[0] + (pt2[0] - pt1[0]) * i / dashes), int(pt1[1] + (pt2[1] - pt1[1]) * i / dashes)]
            end = [int(pt1[0] + (pt2[0] - pt1[0]) * (i + 0.5) / dashes), int(pt1[1] + (pt2[1] - pt1[1]) * (i + 0.5) / dashes)]
            cv2.line(img, tuple(start), tuple(end), color, thickness)

    @staticmethod
    def _draw_dashed_poly(img, points, color, thickness=1):
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            DirectionalArrowsChecker._draw_dashed_line(img, tuple(p1), tuple(p2), color, thickness)

    @staticmethod
    def _get_intersection_point(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if den == 0: return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den
        if 0 < t < 1 and 0 < u < 1:
            return (int(x1 + t * (x2 - x1)), int(y1 + t * (y2 - y1)))
        return None

    @staticmethod
    def _calculate_line_angle(line):
        x1, y1, x2, y2 = line
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        return angle + 180 if angle < 0 else angle

    # =================================================================================
    # LANGKAH 1: DETEKSI CROSS TENGAH (METODE BARU YANG DIPERBAIKI)
    # =================================================================================
    @staticmethod
    def _find_central_cross(image, result_img):
        """
        Mendeteksi cross utama menggunakan metode berbasis kontur.
        Mengembalikan: (status, titik_potong, dict_endpoints)
        """
        # Pra-pemrosesan
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_size = max(3, int(min(gray.shape) * DirectionalArrowsChecker._BLUR_FACTOR))
        if blur_size % 2 == 0: blur_size += 1
        blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        closing_kernel_size = max(3, int(min(gray.shape) * DirectionalArrowsChecker._CLOSING_KERNEL_FACTOR))
        if closing_kernel_size % 2 == 0: closing_kernel_size += 1
        kernel = np.ones((closing_kernel_size, closing_kernel_size), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Cari kontur terbesar
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return False, "INVALID: No contours detected", None, None

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        full_edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

        for cnt in contours:
            if cv2.contourArea(cnt) < DirectionalArrowsChecker._MIN_CONTOUR_AREA:
                continue

            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, DirectionalArrowsChecker._PERI_APPROX_FACTOR * peri, True)
            
            # Gabungkan titik yang terlalu dekat
            if len(approx) > 0:
                merged_points = []
                for point in approx:
                    if not any(np.linalg.norm(point[0] - mp[0]) < DirectionalArrowsChecker._POINT_MERGE_THRESHOLD for mp in merged_points):
                        merged_points.append(point)
                approx = np.array(merged_points)

            if len(approx) == 4:
                points = approx.reshape(4, 2)
                groups = [(points[0], points[2]), (points[1], points[3])]
                all_roi_lines = []

                # Buat ROI dan cari garis di dalamnya
                for pt1, pt2 in groups:
                    DirectionalArrowsChecker._draw_dashed_poly(result_img, [pt1, pt2], (255, 0, 255), 2)
                    length = np.linalg.norm(pt1 - pt2)
                    center = (pt1 + pt2) / 2
                    width_roi = length * DirectionalArrowsChecker._ROI_WIDTH_FACTOR
                    angle_deg = math.degrees(math.atan2(pt2[1] - pt1[1], pt2[0] - pt1[0]))
                    rect = (tuple(center), (length, width_roi), angle_deg)
                    box = np.intp(cv2.boxPoints(rect))
                    DirectionalArrowsChecker._draw_dashed_poly(result_img, box, (255, 120, 0), 2)
                    mask = np.zeros(gray.shape, dtype=np.uint8)
                    cv2.fillConvexPoly(mask, box, 255)
                    roi_edges = cv2.bitwise_and(full_edges, full_edges, mask=mask)
                    lines = cv2.HoughLinesP(roi_edges, 1, np.pi / 180, threshold=DirectionalArrowsChecker._HOUGH_THRESHOLD, minLineLength=int(length * DirectionalArrowsChecker._HOUGH_MIN_LENGTH_FACTOR), maxLineGap=DirectionalArrowsChecker._HOUGH_MAX_GAP)
                    all_roi_lines.append(lines)
                    if lines is not None:
                        for line in lines:
                            cv2.line(result_img, tuple(line[0][:2]), tuple(line[0][2:]), (255, 255, 0), 1)

                # Cari pasangan garis utama yang berpotongan
                main_intersecting_pair = None
                max_len_in_pair = 0
                
                if len(all_roi_lines) == 2 and all_roi_lines[0] is not None and all_roi_lines[1] is not None:
                    for line1 in all_roi_lines[0]:
                        for line2 in all_roi_lines[1]:
                            if DirectionalArrowsChecker._get_intersection_point(line1[0], line2[0]):
                                # Hitung sudut untuk keperluan filter
                                angle1_check = DirectionalArrowsChecker._calculate_line_angle(line1[0])
                                angle2_check = DirectionalArrowsChecker._calculate_line_angle(line2[0])

                                if abs(angle1_check - angle2_check) > DirectionalArrowsChecker._ANGLE_DIFF_THRESHOLD:
                                    # Jika lolos filter, baru periksa panjangnya
                                    len1 = np.linalg.norm(np.array(line1[0][:2]) - np.array(line1[0][2:]))
                                    len2 = np.linalg.norm(np.array(line2[0][:2]) - np.array(line2[0][2:]))
                                    current_max = max(len1, len2)
                                    if current_max > max_len_in_pair:
                                        max_len_in_pair = current_max
                                        main_intersecting_pair = (line1[0], line2[0])
                
                if main_intersecting_pair:
                    lineA, lineB = main_intersecting_pair
                    angle1 = DirectionalArrowsChecker._calculate_line_angle(lineA)
                    angle2 = DirectionalArrowsChecker._calculate_line_angle(lineB)
                    
                    is_A_horz = (angle1 <= DirectionalArrowsChecker._HORIZONTAL_ANGLE_MAX) or (angle1 >= DirectionalArrowsChecker._HORIZONTAL_ANGLE_MIN)
                    is_A_vert = (DirectionalArrowsChecker._VERTICAL_ANGLE_MIN <= angle1 <= DirectionalArrowsChecker._VERTICAL_ANGLE_MAX)
                    is_B_horz = (angle2 <= DirectionalArrowsChecker._HORIZONTAL_ANGLE_MAX) or (angle2 >= DirectionalArrowsChecker._HORIZONTAL_ANGLE_MIN)
                    is_B_vert = (DirectionalArrowsChecker._VERTICAL_ANGLE_MIN <= angle2 <= DirectionalArrowsChecker._VERTICAL_ANGLE_MAX)

                    cv2.line(result_img, tuple(lineA[:2]), tuple(lineA[2:]), (0, 255, 0), 2)
                    cv2.line(result_img, tuple(lineB[:2]), tuple(lineB[2:]), (0, 255, 0), 2)
                    
                    if not ((is_A_horz and is_B_vert) or (is_A_vert and is_B_horz)):
                        return False, "INVALID: Incorrect cross orientation", None, None

                    intersection_point = DirectionalArrowsChecker._get_intersection_point(lineA, lineB)
                    if not intersection_point:
                        return False, "INVALID: Lines do not intersect", None, None
                    
                    cv2.circle(result_img, intersection_point, 7, (255, 0, 0), -1)

                    # Validasi jarak
                    distances = [np.linalg.norm(p - np.array(intersection_point)) for p in points]
                    if not all(d >= DirectionalArrowsChecker._MIN_ENDPOINT_DISTANCE for d in distances):
                        return False, "INVALID: Endpoint too close to center", None, None
                            
                    # Sukses, petakan endpoints
                    points_arr = np.array(points)
                    endpoints = {
                        'left': tuple(points_arr[np.argmin(points_arr[:, 0])]),
                        'right': tuple(points_arr[np.argmax(points_arr[:, 0])]),
                        'top': tuple(points_arr[np.argmin(points_arr[:, 1])]),
                        'bottom': tuple(points_arr[np.argmax(points_arr[:, 1])])
                    }
                    return True, "OK", intersection_point, endpoints
        
        return False, "INVALID: No 4-sided cross found", None, None

    # =================================================================================
    # LANGKAH 2: DETEKSI PANAH DAN CELAH (METODE LAMA, TIDAK DIUBAH)
    # =================================================================================
    @staticmethod
    def detect_arrow_lines(image, result_img, endpoint, debug=False):
        if endpoint is None: return False, [], False

        h, w = image.shape[:2]
        radius = min(h // 4, w // 4, 150)
        
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, endpoint, radius, 255, -1)
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        thresh = cv2.bitwise_and(thresh, thresh, mask=mask)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= 50]
        has_gap = len(significant_contours) > 1
        
        gap_color = (0, 0, 255) if has_gap else (0, 255, 0)
        cv2.putText(result_img, "GAP" if has_gap else "NO GAP", (endpoint[0] - 40, endpoint[1] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, gap_color, 2)
        
        for cnt in significant_contours:
            cv2.drawContours(result_img, [cnt], -1, (255, 0, 255), 1)

        connected_lines = []
        for cnt in significant_contours:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True).reshape(-1, 2)
            for i in range(len(approx)):
                pt1, pt2 = tuple(approx[i]), tuple(approx[(i + 1) % len(approx)])
                dist_to_center = min(np.hypot(pt1[0] - endpoint[0], pt1[1] - endpoint[1]),
                                     np.hypot(pt2[0] - endpoint[0], pt2[1] - endpoint[1]))
                if dist_to_center < 30 and np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1]) > 15:
                    connected_lines.append((pt1, pt2))
        
        if len(connected_lines) < 2: return False, [], has_gap

        def get_vector(line, center):
            p1, p2 = line
            vec = np.array(p2) - np.array(p1)
            return vec if np.linalg.norm(np.array(p1) - center) < np.linalg.norm(np.array(p2) - center) else -vec

        arrow_lines = set()
        for line1, line2 in itertools.combinations(connected_lines, 2):
            v1, v2 = get_vector(line1, endpoint), get_vector(line2, endpoint)
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle = np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))
                if 20 <= angle <= 90:
                    arrow_lines.add(line1)
                    arrow_lines.add(line2)
        
        return len(arrow_lines) >= 2, list(arrow_lines), has_gap

    # =================================================================================
    # FUNGSI UTAMA (CHECK)
    # =================================================================================
    @staticmethod
    def check(image_path, debug=False):
        try:
            image_color = cv2.imread(image_path)
            if image_color is None:
                error_img = np.zeros((300, 300, 3), dtype=np.uint8)
                cv2.putText(error_img, "Image not found", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                return 0, error_img
            
            original_height, original_width = image_color.shape[:2]
            if max(original_height, original_width) > DirectionalArrowsChecker._MAX_DIMENSION:
                scale = DirectionalArrowsChecker._MAX_DIMENSION / max(original_height, original_width)
                image_color = cv2.resize(image_color, (0,0), fx=scale, fy=scale)
            
            result_img = image_color.copy()

            # LANGKAH 1: Panggil detektor cross yang baru dan kokoh
            cross_detected, status_text, intersection_point, endpoints = DirectionalArrowsChecker._find_central_cross(image_color, result_img)
            
            any_gap_detected = False
            if cross_detected:
                # LANGKAH 2: Jika cross ditemukan, periksa setiap ujung untuk panah dan celah
                for direction, point in endpoints.items():
                    if point:
                        has_arrow, lines, has_gap = DirectionalArrowsChecker.detect_arrow_lines(
                            image_color, result_img, point, debug
                        )
                        if has_gap: any_gap_detected = True
                        if has_arrow:
                            for p1, p2 in lines:
                                cv2.line(result_img, p1, p2, (0, 255, 0), 2)
                            cv2.circle(result_img, point, 8, (0, 255, 255), -1)

            # LANGKAH 3: Tentukan status akhir
            if cross_detected and not any_gap_detected:
                final_valid = True
                summary_text = "VALID: Directional Arrows detected"
                summary_color = (0, 255, 0)
            elif cross_detected and any_gap_detected:
                final_valid = False
                summary_text = "INVALID: Gap detected"
                summary_color = (0, 0, 255)
            else:
                final_valid = False
                summary_text = status_text  # Gunakan status dari detektor cross
                summary_color = (0, 0, 255)
            
            cv2.putText(result_img, summary_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, summary_color, 2)
            
            return 1 if final_valid else 0, result_img

        except Exception as e:
            print(f"Detection error: {e}")
            traceback.print_exc()
            error_img = np.zeros((300, 300, 3), dtype=np.uint8)
            cv2.putText(error_img, f"Error: {str(e)}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return 0, error_img

# Test code
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_file = sys.argv[1]
        score, result_img = DirectionalArrowsChecker.check(image_file, debug=False)
        print(f"Final Result: {score}")
        if result_img is not None:
            cv2.imshow("Directional Arrows Detection", result_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Usage: python directional_arrows.py <image_path>")