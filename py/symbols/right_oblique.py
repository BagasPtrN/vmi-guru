import cv2
import numpy as np
import math
from itertools import combinations
import sys

class RightObliqueChecker:
    """
    Sebuah kelas statis untuk mendeteksi keberadaan garis miring ke kanan (\)
    dengan menganalisis kontur dominan, sudut, dan kelurusan garis.
    """
    # =================================================================================
    # KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    # Parameter Umum
    _MAX_DIMENSION = 1000
    _MIN_CONTOUR_AREA = 100

    # Parameter Pra-pemrosesan
    _GAUSSIAN_BLUR_KERNEL = (5, 5)
    _MORPH_KERNEL_SIZE = (5, 5)

    # Parameter Analisis Kontur
    _PERI_APPROX_FACTOR = 0.00824
    _POINT_MERGE_REL_THRESHOLD = 0.08  # 8% dari panjang perimeter

    # Parameter Aturan Validasi
    _MIN_ANGLE_DEGREES = 110
    _MAX_ANGLE_DEGREES = 160
    _ABRUPT_CHANGE_THRESHOLD_DEGREES = 30
    _MAIN_LINE_ANGLE_TOLERANCE = 18.7

    # =================================================================================
    # FUNGSI BANTU UNTUK ANALISIS GEOMETRI
    # =================================================================================
    @staticmethod
    def find_farthest_points(points):
        """Mencari pasangan titik dengan jarak terjauh dalam sebuah kontur."""
        if len(points) < 2: return None, None
        points_list = points.reshape(-1, 2)
        max_dist, endpoints = -1, (None, None)
        for p1, p2 in combinations(points_list, 2):
            dist = np.linalg.norm(p1 - p2)
            if dist > max_dist:
                max_dist, endpoints = dist, (tuple(p1), tuple(p2))
        return endpoints

    @staticmethod
    def reorder_contour(points, endpoint1, endpoint2):
        """Menyusun ulang urutan titik kontur berdasarkan dua endpoint terjauh."""
        points_list = [tuple(p[0]) for p in points]
        try:
            idx1, idx2 = points_list.index(endpoint1), points_list.index(endpoint2)
        except ValueError:
            return points
        rolled = points_list[idx1:] + points_list[:idx1]
        new_idx2 = rolled.index(endpoint2)
        return np.array(rolled[:new_idx2+1] + rolled[new_idx2+1:][::-1], dtype=np.int32).reshape(-1, 1, 2)

    @staticmethod
    def calculate_angle(p1, p2):
        """Menghitung sudut sebuah segmen garis dalam derajat (-180 hingga 180)."""
        return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))

    @staticmethod
    def detect_abrupt_change(polyline_points):
        """Mendeteksi perubahan arah yang tajam dalam sebuah polyline."""
        if len(polyline_points) < 3:
            return False, None

        points_list = [tuple(p[0]) for p in polyline_points]
        angles = []
        for i in range(len(points_list) - 1):
            angle = RightObliqueChecker.calculate_angle(points_list[i], points_list[i+1])
            # Normalisasi sudut ke rentang [0, 180) untuk perbandingan yang konsisten
            if angle < 0:
                angle += 180
            angles.append(angle)

        for i in range(len(angles) - 1):
            diff = abs(angles[i] - angles[i+1])
            # Perbedaan sudut terkecil antara dua garis
            angle_diff = min(diff, 180 - diff)
            if angle_diff > RightObliqueChecker._ABRUPT_CHANGE_THRESHOLD_DEGREES:
                return True, points_list[i+1] # Perubahan tajam terdeteksi

        return False, None

    @staticmethod
    def find_main_line(points):
        """Menganalisis polyline untuk menemukan segmen lurus dominan (terpanjang)."""
        if len(points) < 2: return None
        points_list = [tuple(p[0]) for p in points]
        segments = [{'p1': points_list[i], 'p2': points_list[i+1], 'angle': RightObliqueChecker.calculate_angle(points_list[i], points_list[i+1])} for i in range(len(points_list) - 1)]
        if not segments: return None
        
        groups, current_group = [], [segments[0]]
        for i in range(1, len(segments)):
            prev_angle, current_angle = current_group[-1]['angle'], segments[i]['angle']
            angle_diff = min(abs(prev_angle - current_angle), 360 - abs(prev_angle - current_angle))
            if angle_diff <= RightObliqueChecker._MAIN_LINE_ANGLE_TOLERANCE:
                current_group.append(segments[i])
            else:
                groups.append(current_group)
                current_group = [segments[i]]
        groups.append(current_group)

        longest_line, max_length = None, -1
        for group in groups:
            start_point, end_point = group[0]['p1'], group[-1]['p2']
            length = np.linalg.norm(np.array(start_point) - np.array(end_point))
            if length > max_length:
                max_length, longest_line = length, (start_point, end_point)
        return longest_line

    # =================================================================================
    # FUNGSI UTAMA
    # =================================================================================
    @staticmethod
    def check(image_path):
        """Fungsi utama untuk memproses gambar dan melakukan deteksi garis."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError(f"Gambar tidak ditemukan di path: {image_path}")

            # --- 1. Pra-pemrosesan ---
            if max(image.shape) > RightObliqueChecker._MAX_DIMENSION:
                scale = RightObliqueChecker._MAX_DIMENSION / max(image.shape)
                image = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, RightObliqueChecker._GAUSSIAN_BLUR_KERNEL, 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = np.ones(RightObliqueChecker._MORPH_KERNEL_SIZE, np.uint8)
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # --- 2. Analisis Kontur ---
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            result = image.copy()
            found_line, is_angle_valid, has_abrupt_change = False, False, False
            main_line_angle, abrupt_point = None, None

            if contours:
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                # Hanya proses kontur terbesar
                cnt = contours[0]

                if cv2.contourArea(cnt) > RightObliqueChecker._MIN_CONTOUR_AREA:
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, RightObliqueChecker._PERI_APPROX_FACTOR * peri, True)
                    
                    if len(approx) > 1:
                        dist_thresh = RightObliqueChecker._POINT_MERGE_REL_THRESHOLD * peri
                        merged = [approx[0]]
                        for pt in approx[1:]:
                            if not any(np.linalg.norm(pt[0] - mp[0]) < dist_thresh for mp in merged):
                                merged.append(pt)
                        approx = np.array(merged, dtype=np.int32)

                    if len(approx) >= 2:
                        ep1, ep2 = RightObliqueChecker.find_farthest_points(approx)
                        if ep1 and ep2:
                            ordered_approx = RightObliqueChecker.reorder_contour(approx, ep1, ep2)
                            dominant_line = RightObliqueChecker.find_main_line(ordered_approx)
                            
                            if dominant_line:
                                # --- 3. Validasi Logis ---
                                p1, p2 = dominant_line
                                found_line = True
                                main_line_angle = RightObliqueChecker.calculate_angle(p1, p2)
                                
                                # Validasi 1: Sudut Garis Dominan
                                norm_angle = main_line_angle if main_line_angle >= 0 else main_line_angle + 180
                                is_angle_valid = RightObliqueChecker._MIN_ANGLE_DEGREES <= norm_angle <= RightObliqueChecker._MAX_ANGLE_DEGREES

                                # Validasi 2: Kelurusan (Tidak ada belokan tajam)
                                has_abrupt_change, abrupt_point = RightObliqueChecker.detect_abrupt_change(ordered_approx)
                                
                                # --- 4. Visualisasi ---
                                cv2.line(result, p1, p2, (0, 0, 255), 6)
                                cv2.polylines(result, [ordered_approx], False, (0, 255, 0), 2)
                                cv2.circle(result, ep1, 7, (255, 0, 255), -1)
                                cv2.circle(result, ep2, 7, (0, 255, 255), -1)

            # --- 5. Menampilkan Hasil ---
            is_final_valid = found_line and is_angle_valid and not has_abrupt_change
            
            if is_final_valid:
                status_text, color = "VALID: Right Oblique Line detected", (0, 255, 0)
            elif has_abrupt_change:
                status_text, color = "INVALID: Abrupt direction change", (0, 165, 255)
                if abrupt_point:
                    cv2.circle(result, abrupt_point, 12, color, 2)
                    cv2.circle(result, abrupt_point, 5, color, -1)
            elif found_line and not is_angle_valid:
                status_text, color = "INVALID: Angle out of range", (0, 0, 255)
            else:
                status_text, color = "INVALID: No valid line found", (0, 0, 255)
            
            cv2.putText(result, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(result, f"Contours found: {len(contours) if contours else 0}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            angle_text = f"Angle: {main_line_angle:.2f} deg" if main_line_angle is not None else "Angle: N/A"
            cv2.putText(result, angle_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            
            return 1 if is_final_valid else 0, result

        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            error_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(error_img, "An error occurred.", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)
            cv2.putText(error_img, str(e)[:60], (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return 0, error_img

# --- Bagian Eksekusi Kode ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Processing image: {image_path}")
        print(f"Angle rule: [{RightObliqueChecker._MIN_ANGLE_DEGREES}, {RightObliqueChecker._MAX_ANGLE_DEGREES}] degrees.")
        print(f"Abrupt change rule: Segment angle diff <= {RightObliqueChecker._ABRUPT_CHANGE_THRESHOLD_DEGREES} degrees.")
        
        score, result_img = RightObliqueChecker.check(image_path)
        
        print(f"Result Score: {score} (1=Valid, 0=Invalid)")
        
        if result_img is not None:
            cv2.imshow("Line Detection Result", result_img)
            print("Press any key to close the window.")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Penggunaan: python <nama_file_anda.py> <path_ke_gambar_anda>")