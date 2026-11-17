import cv2
import numpy as np
import math
import sys

class CircleChecker:
    """
    Kelas statis untuk mendeteksi dan memvalidasi objek berbentuk lingkaran
    dalam sebuah gambar menggunakan serangkaian metrik geometris.
    """
    # =================================================================================
    # KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    _MAX_DIMENSION = 1000
    _MIN_ABS_CONTOUR_AREA = 300

    # Threshold ukuran relatif terhadap gambar
    _MIN_REL_AREA_PERCENT = 0.03  # 3% dari total area gambar
    _MIN_REL_DIM_PERCENT = 0.02   # 2% dari lebar/tinggi gambar

    # Parameter validasi bentuk
    _MAX_ASPECT_RATIO = 2.5
    _MIN_CIRCULARITY = 0.35
    _MIN_ANGULAR_COVERAGE = 0.65
    _MIN_ABS_DIMENSION = 20

    # Parameter pra-pemrosesan
    _CANNY_LOW_THRESH = 30
    _CANNY_HIGH_THRESH = 100
    _KERNEL_SIZE = (7, 7)
    _MORPH_ITERATIONS = 3
    _DILATE_ITERATIONS = 1

    # =================================================================================
    # FUNGSI METRIK UNTUK ANALISIS BENTUK
    # =================================================================================
    @staticmethod
    def calculate_aspect_ratio(w, h):
        """Menghitung rasio aspek dari bounding box (lebar, tinggi)."""
        return max(w, h) / min(w, h) if min(w, h) > 0 else 0

    @staticmethod
    def calculate_circularity(contour):
        """Menghitung sirkularitas berdasarkan perbandingan area dan perimeter."""
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return 0
        return (4 * np.pi * area) / (perimeter ** 2)

    @staticmethod
    def calculate_ellipse_circularity(contour):
        """Menghitung sirkularitas berdasarkan seberapa baik kontur cocok dengan elips."""
        if len(contour) < 5:
            return 0
        try:
            ellipse = cv2.fitEllipse(contour)
            (cx, cy), (d1, d2), angle = ellipse
            
            ellipse_aspect = max(d1, d2) / min(d1, d2) if min(d1, d2) > 0 else 0
            
            # Hitung rata-rata penyimpangan titik kontur dari elips yang dipasang
            mean_dist = 0
            a, b = d1 / 2, d2 / 2
            if a == 0 or b == 0: return 0
            
            angle_rad = np.radians(angle)
            cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)

            for point in contour:
                dx, dy = point[0][0] - cx, point[0][1] - cy
                x_rot = dx * cos_a + dy * sin_a
                y_rot = -dx * sin_a + dy * cos_a
                dist = (x_rot**2) / (a**2) + (y_rot**2) / (b**2)
                mean_dist += abs(1 - dist)
                
            mean_dist /= len(contour)
            # Semakin kecil penyimpangan dan rasio aspek, semakin tinggi skornya
            return 1 / (1 + mean_dist + ellipse_aspect) if ellipse_aspect > 0 else 0
        except:
            # cv2.fitEllipse dapat gagal pada beberapa bentuk
            return 0

    @staticmethod
    def calculate_angular_coverage(contour):
        """Menghitung seberapa merata titik-titik kontur mengelilingi pusatnya."""
        if len(contour) < 5:
            return 0
        try:
            (cx, cy), _ = cv2.minEnclosingCircle(contour)
            
            angles = [math.degrees(math.atan2(p[0][1] - cy, p[0][0] - cx)) % 360 for p in contour]
            angles.sort()
            
            # Hitung celah (gap) sudut terbesar antara titik-titik
            max_gap = 0
            for i in range(1, len(angles)):
                max_gap = max(max_gap, angles[i] - angles[i-1])
            
            # Periksa juga celah yang melintasi 360 -> 0 derajat
            circular_gap = (360 - angles[-1]) + angles[0]
            max_gap = max(max_gap, circular_gap)
            
            # Skor cakupan adalah 1 dikurangi proporsi celah terbesar
            return max(0, 1 - max_gap / 360)
        except:
            return 0
            
    # =================================================================================
    # LOGIKA UTAMA
    # =================================================================================
    @staticmethod
    def check(image_path):
        """
        Memproses gambar untuk mendeteksi dan memvalidasi objek lingkaran.
        Mengembalikan skor (1 jika valid, 0 jika tidak) dan gambar hasil.
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                print(f"Error: Gambar tidak ditemukan di {image_path}")
                return 0, None

            # --- Pra-pemrosesan Gambar ---
            h, w = image.shape[:2]
            if max(h, w) > CircleChecker._MAX_DIMENSION:
                scale = CircleChecker._MAX_DIMENSION / max(h, w)
                image = cv2.resize(image, (int(w * scale), int(h * scale)))
            
            new_h, new_w = image.shape[:2]
            total_image_area = new_h * new_w

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.bilateralFilter(gray, 11, 75, 75)
            edges = cv2.Canny(blurred, CircleChecker._CANNY_LOW_THRESH, CircleChecker._CANNY_HIGH_THRESH)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, CircleChecker._KERNEL_SIZE)
            processed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=CircleChecker._MORPH_ITERATIONS)
            processed = cv2.morphologyEx(processed, cv2.MORPH_DILATE, kernel, iterations=CircleChecker._DILATE_ITERATIONS)
            
            # --- Analisis Kontur ---
            contours, _ = cv2.findContours(processed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            filtered_contours = [c for c in contours if cv2.contourArea(c) >= CircleChecker._MIN_ABS_CONTOUR_AREA]
            
            result = image.copy()
            final_score = 0
            
            if not filtered_contours:
                summary_text = "INVALID: No significant contours found"
                cv2.putText(result, summary_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                return 0, result

            # --- Iterasi dan Validasi Setiap Kontur ---
            for i, cnt in enumerate(filtered_contours):
                # 1. Hitung semua metrik
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = CircleChecker.calculate_aspect_ratio(w, h)
                contour_circ = CircleChecker.calculate_circularity(cnt)
                ellipse_circ = CircleChecker.calculate_ellipse_circularity(cnt)
                angular_coverage = CircleChecker.calculate_angular_coverage(cnt)
                circularity = max(contour_circ, ellipse_circ)
                contour_area = cv2.contourArea(cnt)
                
                # 2. Periksa semua kondisi validasi
                is_aspect_ratio_ok = aspect_ratio <= CircleChecker._MAX_ASPECT_RATIO
                is_circularity_ok = circularity >= CircleChecker._MIN_CIRCULARITY
                is_coverage_ok = angular_coverage > CircleChecker._MIN_ANGULAR_COVERAGE
                is_abs_size_ok = w > CircleChecker._MIN_ABS_DIMENSION and h > CircleChecker._MIN_ABS_DIMENSION
                is_rel_size_ok = (
                    contour_area >= CircleChecker._MIN_REL_AREA_PERCENT * total_image_area and
                    w >= CircleChecker._MIN_REL_DIM_PERCENT * new_w and
                    h >= CircleChecker._MIN_REL_DIM_PERCENT * new_h
                )
                
                is_valid = all([is_aspect_ratio_ok, is_circularity_ok, is_coverage_ok, is_abs_size_ok, is_rel_size_ok])

                # 3. Visualisasi berdasarkan hasil validasi
                color = (0, 255, 0) if is_valid else (0, 0, 255)
                thickness = 2 if is_valid else 1
                
                cv2.rectangle(result, (x, y), (x + w, y + h), color, thickness)
                cv2.drawContours(result, [cnt], -1, (255, 0, 255), 1)
                
                if len(cnt) >= 5:
                    try:
                        ellipse = cv2.fitEllipse(cnt)
                        cv2.ellipse(result, ellipse, (0, 200, 255), 1)
                    except:
                        pass  # Abaikan jika fitEllipse gagal
                
                if is_valid:
                    final_score = 1
                    center = (int(x + w / 2), int(y + h / 2))
                    cv2.circle(result, center, 5, (255, 0, 0), -1)
                
                label = f"{chr(65 + i)}: {contour_area / total_image_area * 100:.1f}%"
                cv2.putText(result, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)

            # --- Tampilkan Ringkasan Akhir ---
            summary_text = "VALID: Circle detected" if final_score else "INVALID: Circle not detected or too small"
            summary_color = (0, 255, 0) if final_score else (0, 0, 255)
            cv2.putText(result, summary_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, summary_color, 2)
            cv2.putText(result, f"Min Area: {CircleChecker._MIN_REL_AREA_PERCENT*100:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 1)

            return final_score, result

        except Exception as e:
            print(f"An error occurred: {e}")
            return 0, None

if __name__ == '__main__':
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        score, result_image = CircleChecker.check(image_path)
        
        print(f"Path: {image_path}")
        print(f"Score: {score}")

        if result_image is not None:
            cv2.imshow("Circle Detection Result", result_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Penggunaan: python <nama_script.py> <path_ke_gambar>")