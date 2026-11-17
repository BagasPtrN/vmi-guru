import cv2
import numpy as np
import sys

class SquareChecker:
    """
    Kelas statis untuk mendeteksi dan memvalidasi keberadaan segi empat
    (quadrilateral) dalam sebuah gambar.
    """
    # =================================================================================
    # KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    _MAX_DIMENSION = 1000
    _MIN_CONTOUR_AREA = 500
    
    # Parameter Pra-pemrosesan Adaptif
    _ADAPTIVE_BLUR_FACTOR = 0.01
    _ADAPTIVE_KERNEL_FACTOR = 0.02
    
    # Parameter Analisis Kontur
    _PERI_APPROX_FACTOR = 0.028
    _POINT_MERGE_THRESHOLD = 80

    # =================================================================================
    # METODE UTAMA
    # =================================================================================
    @staticmethod
    def is_square(approx):
        """
        Memeriksa apakah sebuah kontur adalah segi empat (memiliki 4 sudut).
        Metode ini hanya memeriksa jumlah titik, bukan sudut atau panjang sisi.
        """
        return len(approx) == 4

    @staticmethod
    def check(image_path):
        """Fungsi utama untuk memproses gambar dan mendeteksi keberadaan segi empat."""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError(f"Gambar tidak ditemukan di path: {image_path}")

            # --- 1. Pra-pemrosesan Gambar ---
            if max(image.shape) > SquareChecker._MAX_DIMENSION:
                scale = SquareChecker._MAX_DIMENSION / max(image.shape)
                image = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            blur_size = max(3, int(min(h, w) * SquareChecker._ADAPTIVE_BLUR_FACTOR))
            if blur_size % 2 == 0: blur_size += 1
            blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            closing_kernel_size = max(3, int(min(h, w) * SquareChecker._ADAPTIVE_KERNEL_FACTOR))
            if closing_kernel_size % 2 == 0: closing_kernel_size += 1
            kernel = np.ones((closing_kernel_size, closing_kernel_size), np.uint8)
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            # --- 2. Analisis Kontur ---
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            result = image.copy()
            found_square = False

            if not contours:
                cv2.putText(result, "No contours detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                return 0, result

            for cnt in contours:
                if cv2.contourArea(cnt) < SquareChecker._MIN_CONTOUR_AREA:
                    continue

                # Gunakan convex hull untuk menangani bentuk yang sedikit cekung atau tidak sempurna
                hull = cv2.convexHull(cnt)
                peri = cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, SquareChecker._PERI_APPROX_FACTOR * peri, True)

                # --- 3. Penggabungan Titik Sudut yang Berdekatan ---
                # Logika ini berguna untuk kasus di mana deteksi sudut menghasilkan
                # beberapa titik yang sangat dekat satu sama lain.
                if len(approx) > 0:
                    merged_points = []
                    for point in approx:
                        is_close = False
                        # Periksa apakah titik saat ini dekat dengan titik lain yang sudah ada di 'merged_points'
                        for merged_point in merged_points:
                            if np.linalg.norm(point[0] - merged_point[0]) < SquareChecker._POINT_MERGE_THRESHOLD:
                                is_close = True
                                break
                        # Jika tidak ada titik yang berdekatan, tambahkan sebagai titik baru
                        if not is_close:
                            merged_points.append(point)
                    
                    # Perbarui aproksimasi dengan titik-titik yang sudah digabungkan
                    approx = np.array(merged_points)

                # --- 4. Validasi dan Visualisasi ---
                # Gambar semua kontur yang diproses (setelah digabung) dengan warna merah
                # Ini membantu memvisualisasikan bentuk apa saja yang dipertimbangkan
                cv2.polylines(result, [approx], True, (0, 0, 255), 3)

                # Panggil metode is_square untuk validasi akhir
                if SquareChecker.is_square(approx):
                    # Jika valid, gambar ulang dengan warna hijau dan set status
                    cv2.polylines(result, [approx], True, (0, 255, 0), 3)
                    found_square = True
            
            # --- 5. Tampilkan Hasil Akhir ---
            text = "VALID: Square detected" if found_square else "INVALID: No valid Square"
            color = (0, 255, 0) if found_square else (0, 0, 255)
            cv2.putText(result, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(result, f"Contours found: {len(contours)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            return 1 if found_square else 0, result

        except Exception as e:
            print(f"An error occurred during detection: {str(e)}")
            error_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(error_img, "An error occurred.", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)
            cv2.putText(error_img, str(e)[:60], (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return 0, error_img

# --- Bagian Eksekusi Kode ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        score, result_img = SquareChecker.check(image_path)
        
        print(f"Path: {image_path}")
        print(f"Score: {score}")

        if result_img is not None:
            cv2.imshow("Square Detection Result", result_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Penggunaan: python <nama_script.py> <path_ke_gambar>")