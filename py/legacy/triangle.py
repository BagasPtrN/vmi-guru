import cv2
import numpy as np
import math
import sys

class TriangleChecker:
    """
    Kelas statis untuk mendeteksi dan memvalidasi keberadaan segitiga dalam sebuah gambar.
    Validasi mencakup bentuk, sudut (tidak tumpul), dan orientasi (tidak terbalik).
    """
    # =================================================================================
    # 1. KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    # Parameter Umum
    _MAX_DIMENSION = 1000
    _MIN_CONTOUR_AREA = 500

    # Parameter Pra-pemrosesan Adaptif
    _ADAPTIVE_BLUR_FACTOR = 0.01
    _ADAPTIVE_KERNEL_FACTOR = 0.02
    
    # Parameter Analisis Kontur
    _PERI_APPROX_FACTOR = 0.055

    # Parameter Aturan Validasi
    _OBTUSE_ANGLE_THRESHOLD = 110.0  # Sudut di atas ini dianggap tumpul
    _INVERTED_ANGLE_TOLERANCE = 10.0  # Toleransi sudut untuk dianggap horizontal
    _SUM_ANGLES_MIN = 170.0
    _SUM_ANGLES_MAX = 190.0

    # =================================================================================
    # 2. FUNGSI VALIDASI GEOMETRIS
    # =================================================================================
    @staticmethod
    def is_triangle(approx):
        """
        Memeriksa apakah kontur adalah segitiga secara geometris dan mengembalikan sudut-sudutnya.
        """
        if len(approx) != 3:
            return False, []

        def angle(p1, p2, p3):
            v1, v2 = p1 - p2, p3 - p2
            cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            return np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))

        points = approx.reshape(3, 2)
        angles = [angle(points[i], points[(i + 1) % 3], points[(i + 2) % 3]) for i in range(3)]

        # Segitiga yang valid harus memiliki jumlah sudut mendekati 180 derajat
        if TriangleChecker._SUM_ANGLES_MIN <= sum(angles) <= TriangleChecker._SUM_ANGLES_MAX:
            return True, angles
        
        return False, angles

    @staticmethod
    def has_obtuse_angle(angles):
        """Memeriksa apakah ada sudut tumpul dalam daftar sudut."""
        return any(angle > TriangleChecker._OBTUSE_ANGLE_THRESHOLD for angle in angles)

    @staticmethod
    def is_inverted(approx):
        """Memeriksa apakah 'dasar' segitiga (sisi teratas) hampir horizontal."""
        points = sorted([tuple(pt[0]) for pt in approx], key=lambda p: (p[1], p[0]))
        if len(points) < 2: return False

        p1, p2 = points[0], points[1]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        if dx == 0 and dy == 0: return False

        angle_deg = abs(math.degrees(math.atan2(dy, dx)))
        acute_angle = angle_deg if angle_deg <= 90 else 180 - angle_deg
        
        return acute_angle <= TriangleChecker._INVERTED_ANGLE_TOLERANCE

    # =================================================================================
    # 3. FUNGSI UTAMA (CHECK)
    # =================================================================================
    @staticmethod
    def check(image_path):
        """Fungsi utama untuk memproses gambar dan mendeteksi segitiga yang valid."""
        try:
            image = cv2.imread(image_path)
            if image is None: raise FileNotFoundError(f"Gambar tidak ditemukan: {image_path}")

            # --- Tahap 1: Pra-pemrosesan Gambar ---
            if max(image.shape) > TriangleChecker._MAX_DIMENSION:
                scale = TriangleChecker._MAX_DIMENSION / max(image.shape)
                image = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            blur_size = max(3, int(min(h, w) * TriangleChecker._ADAPTIVE_BLUR_FACTOR))
            if blur_size % 2 == 0: blur_size += 1
            blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            closing_kernel_size = max(3, int(min(h, w) * TriangleChecker._ADAPTIVE_KERNEL_FACTOR))
            if closing_kernel_size % 2 == 0: closing_kernel_size += 1
            kernel = np.ones((closing_kernel_size, closing_kernel_size), np.uint8)
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            # --- Tahap 2: Deteksi dan Analisis Kontur ---
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            result = image.copy()
            is_any_triangle_valid = False
            valid_triangle_count, invalid_triangle_count = 0, 0
            status_message = "INVALID: No valid triangle detected"

            for cnt in contours:
                if cv2.contourArea(cnt) < TriangleChecker._MIN_CONTOUR_AREA:
                    continue

                hull = cv2.convexHull(cnt)
                peri = cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, TriangleChecker._PERI_APPROX_FACTOR * peri, True)

                is_geo_triangle, angles = TriangleChecker.is_triangle(approx)

                if is_geo_triangle:
                    # Kontur adalah segitiga, periksa aturan tambahan
                    is_obt = TriangleChecker.has_obtuse_angle(angles)
                    is_inv = TriangleChecker.is_inverted(approx)
                    
                    if not is_obt and not is_inv:
                        # KONDISI VALID: Tidak tumpul dan tidak terbalik
                        cv2.polylines(result, [approx], True, (0, 255, 0), 3)
                        is_any_triangle_valid = True
                        valid_triangle_count += 1
                    else:
                        # KONDISI INVALID: Tumpul atau terbalik
                        cv2.polylines(result, [approx], True, (0, 0, 255), 3)
                        invalid_triangle_count += 1
                        # Update pesan error spesifik jika ini yang pertama ditemukan
                        if status_message == "INVALID: No valid triangle detected":
                            if is_obt:
                                status_message = f"INVALID: Obtuse triangle detected"
                            elif is_inv:
                                status_message = f"INVALID: Inverted triangle detected"
                else:
                    # Bukan segitiga (misal, 4 sisi)
                    if len(approx) > 0:
                        cv2.polylines(result, [approx], True, (0, 0, 255), 3)

            # --- Tahap 3: Menampilkan Hasil Akhir ---
            if is_any_triangle_valid:
                text, color = f"VALID: Triangle detected ({valid_triangle_count})", (0, 255, 0)
            else:
                text, color = status_message, (0, 0, 255)
            
            cv2.putText(result, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            info_text = f"Contours: {len(contours)} | Valid/Invalid Triangles: {valid_triangle_count}/{invalid_triangle_count}"
            cv2.putText(result, info_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            return 1 if is_any_triangle_valid else 0, result

        except Exception as e:
            print(f"Error during triangle detection: {str(e)}")
            error_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(error_img, "An error occurred", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)
            cv2.putText(error_img, str(e)[:60], (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return 0, error_img

# --- Bagian Eksekusi Kode ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        score, result_img = TriangleChecker.check(image_path)
        print(f"Path: {image_path}")
        print(f"Result Score: {score} (1=Valid, 0=Invalid)")
        if result_img is not None:
            cv2.imshow("Triangle Detection Result", result_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Penggunaan: python <nama_script.py> <path_ke_gambar>")