import cv2
import numpy as np
import math
from itertools import combinations
import sys

class HorizontalLineChecker:
    """
    Sebuah kelas statis untuk mendeteksi dan memvalidasi keberadaan garis horizontal 
    dalam sebuah gambar dengan menganalisis kontur dominan.
    """
    # =================================================================================
    # KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    _MAX_DIMENSION = 1000
    _MIN_CONTOUR_AREA = 100
    
    # Parameter Pra-pemrosesan
    _GAUSSIAN_BLUR_KERNEL = (5, 5)
    _MORPH_KERNEL_SIZE = (5, 5)

    # Parameter Analisis Kontur
    _PERI_APPROX_FACTOR = 0.00824
    _POINT_MERGE_REL_THRESHOLD = 0.05  # 5% dari panjang perimeter
    _MAIN_LINE_ANGLE_TOLERANCE = 18.7 # Toleransi sudut untuk menggabungkan segmen
    
    # Parameter Validasi
    _HORIZONTAL_ANGLE_THRESHOLD = 30 # Batas toleransi sudut dari sumbu horizontal

    # =================================================================================
    # FUNGSI BANTU UNTUK ANALISIS GEOMETRI
    # =================================================================================
    @staticmethod
    def find_farthest_points(points):
        """Mencari pasangan titik dengan jarak terjauh dalam sebuah kontur."""
        if len(points) < 2: return None, None
        
        points_list = points.reshape(-1, 2)
        max_dist = -1
        endpoints = (None, None)

        # Iterasi semua kombinasi pasangan titik untuk menemukan yang terjauh
        for p1, p2 in combinations(points_list, 2):
            dist = np.linalg.norm(p1 - p2)
            if dist > max_dist:
                max_dist = dist
                endpoints = (tuple(p1), tuple(p2))
        return endpoints

    @staticmethod
    def reorder_contour(points, endpoint1, endpoint2):
        """Menyusun ulang urutan titik kontur berdasarkan dua endpoint terjauh."""
        points_list = [tuple(p[0]) for p in points]
        try:
            idx1 = points_list.index(endpoint1)
            idx2 = points_list.index(endpoint2)
        except ValueError:
            return points # Jika endpoint tidak ditemukan, kembalikan kontur asli
        
        # "Unroll" kontur sehingga menjadi path lurus antara dua endpoint
        rolled_list = points_list[idx1:] + points_list[:idx1]
        new_idx2 = rolled_list.index(endpoint2)
        
        path1 = rolled_list[:new_idx2 + 1]
        path2_remaining = rolled_list[new_idx2 + 1:]
        final_path_tuples = path1 + path2_remaining[::-1]
        
        return np.array(final_path_tuples, dtype=np.int32).reshape(-1, 1, 2)

    @staticmethod
    def calculate_angle(p1, p2):
        """Menghitung sudut sebuah segmen garis dalam derajat (-180 hingga 180)."""
        return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))

    @staticmethod
    def find_main_line(points):
        """Menganalisis polyline untuk menemukan segmen lurus dominan (terpanjang)."""
        if len(points) < 2: return None
        
        points_list = [tuple(p[0]) for p in points]
        
        # 1. Pecah polyline menjadi segmen-segmen kecil dan hitung sudutnya
        segments = [{'p1': points_list[i], 'p2': points_list[i+1], 'angle': HorizontalLineChecker.calculate_angle(points_list[i], points_list[i+1])} for i in range(len(points_list) - 1)]
        if not segments: return None
        
        # 2. Kelompokkan segmen yang memiliki sudut serupa
        groups = []
        current_group = [segments[0]]
        for i in range(1, len(segments)):
            prev_angle = current_group[-1]['angle']
            current_angle = segments[i]['angle']
            angle_diff = min(abs(prev_angle - current_angle), 360 - abs(prev_angle - current_angle))
            
            if angle_diff <= HorizontalLineChecker._MAIN_LINE_ANGLE_TOLERANCE:
                current_group.append(segments[i])
            else:
                groups.append(current_group)
                current_group = [segments[i]]
        groups.append(current_group)

        # 3. Cari grup yang membentuk garis terpanjang
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
        """Fungsi utama untuk memeriksa keberadaan garis horizontal dalam sebuah gambar."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError(f"Gambar tidak ditemukan di path: {image_path}")

            # --- 1. Pra-pemrosesan ---
            if max(image.shape) > HorizontalLineChecker._MAX_DIMENSION:
                scale = HorizontalLineChecker._MAX_DIMENSION / max(image.shape)
                image = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, HorizontalLineChecker._GAUSSIAN_BLUR_KERNEL, 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = np.ones(HorizontalLineChecker._MORPH_KERNEL_SIZE, np.uint8)
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # --- 2. Analisis Kontur ---
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            result = image.copy()
            found_horizontal_line = False
            main_line_angle = None

            if not contours:
                status_text = "INVALID: No contours detected"
            else:
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                cnt = contours[0]

                if cv2.contourArea(cnt) < HorizontalLineChecker._MIN_CONTOUR_AREA:
                    status_text = "INVALID: Contour too small"
                else:
                    peri = cv2.arcLength(cnt, True)
                    approx = cv2.approxPolyDP(cnt, HorizontalLineChecker._PERI_APPROX_FACTOR * peri, True)

                    # Gabungkan titik-titik yang terlalu berdekatan pada kontur
                    if len(approx) > 1:
                        dist_thresh = HorizontalLineChecker._POINT_MERGE_REL_THRESHOLD * peri
                        merged = [approx[0]]
                        for pt in approx[1:]:
                            if not any(np.linalg.norm(pt[0] - mp[0]) < dist_thresh for mp in merged):
                                merged.append(pt)
                        approx = np.array(merged, dtype=np.int32)

                    # --- 3. Ekstraksi dan Validasi Garis Dominan ---
                    if len(approx) >= 2:
                        ep1, ep2 = HorizontalLineChecker.find_farthest_points(approx)
                        if ep1 and ep2:
                            ordered_approx = HorizontalLineChecker.reorder_contour(approx, ep1, ep2)
                            dominant_line = HorizontalLineChecker.find_main_line(ordered_approx)
                            
                            # Visualisasi
                            cv2.polylines(result, [ordered_approx], False, (0, 255, 0), 2)
                            cv2.circle(result, ep1, 7, (255, 0, 255), -1)
                            cv2.circle(result, ep2, 7, (0, 255, 255), -1)

                            if dominant_line:
                                p1, p2 = dominant_line
                                cv2.line(result, p1, p2, (0, 0, 255), 6)
                                main_line_angle = HorizontalLineChecker.calculate_angle(p1, p2)
                                
                                # Validasi sudut horizontal
                                angle = abs(main_line_angle)
                                if angle <= HorizontalLineChecker._HORIZONTAL_ANGLE_THRESHOLD or \
                                   angle >= (180 - HorizontalLineChecker._HORIZONTAL_ANGLE_THRESHOLD):
                                    found_horizontal_line = True

            # --- 4. Menampilkan Hasil ---
            if 'status_text' not in locals(): # Jika status belum ditentukan
                status_text = "VALID: Horizontal Line detected" if found_horizontal_line else "INVALID: No horizontal line"
            
            color = (0, 255, 0) if found_horizontal_line else (0, 0, 255)
            cv2.putText(result, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(result, f"Contours found: {len(contours)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            
            angle_text = f"Angle: {main_line_angle:.2f} deg" if main_line_angle is not None else "Angle: N/A"
            cv2.putText(result, angle_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            
            return 1 if found_horizontal_line else 0, result

        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            error_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(error_img, "An error occurred.", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)
            cv2.putText(error_img, str(e), (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return 0, error_img

# --- Bagian Eksekusi Kode ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Menganalisis gambar: {image_path}")

        score, result_img = HorizontalLineChecker.check(image_path)
        
        print(f"Skor Hasil: {score} (1=Valid, 0=Invalid)")
        
        if result_img is not None:
            cv2.imshow("Horizontal Line Detection Result", result_img)
            print("Tekan tombol apa saja untuk menutup jendela gambar.")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Penggunaan: python <nama_file.py> <path_ke_gambar_anda>")
        print("Contoh: python horizontal_checker.py 'C:/Users/User/Pictures/garis_horizontal.jpg'")