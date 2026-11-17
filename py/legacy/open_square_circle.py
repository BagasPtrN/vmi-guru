import cv2
import numpy as np
import math
import sys

class OpenSquareCircleChecker:
    """
    Kelas statis untuk mendeteksi dan memvalidasi keberadaan kombinasi
    objek "lingkaran" dan "kotak terbuka" (bentuk U) dalam sebuah gambar.
    """
    # =================================================================================
    # 1. KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    # Parameter Umum
    _MAX_DIMENSION = 1000

    # Parameter Deteksi Lingkaran
    _CIRCLE_MIN_ABS_CONTOUR_AREA = 300
    _CIRCLE_MIN_ABS_DIMENSION = 20
    _CIRCLE_MAX_ASPECT_RATIO = 2.5
    _CIRCLE_MIN_CIRCULARITY = 0.35
    _CIRCLE_MIN_ANGULAR_COVERAGE = 0.65
    _CIRCLE_PREPROC_KERNEL = (7, 7)

    # Parameter Deteksi Kotak Terbuka
    _SQUARE_APPROX_FACTOR = 0.015

    # =================================================================================
    # 2. FUNGSI METRIK UNTUK ANALISIS BENTUK
    # =================================================================================
    @staticmethod
    def calculate_aspect_ratio(width, height):
        """Menghitung rasio aspek dari bounding box."""
        if min(width, height) == 0: return 0
        return max(width, height) / min(width, height)

    @staticmethod
    def calculate_circularity(contour):
        """Menghitung sirkularitas berdasarkan perbandingan area dan perimeter."""
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0: return 0
        return (4 * np.pi * area) / (perimeter ** 2)

    @staticmethod
    def calculate_ellipse_circularity(contour):
        """Menghitung sirkularitas berdasarkan seberapa baik kontur cocok dengan elips."""
        if len(contour) < 5: return 0
        try:
            ellipse = cv2.fitEllipse(contour)
            (cx, cy), (d1, d2), angle = ellipse
            if min(d1, d2) == 0: return 0
            
            ellipse_aspect = max(d1, d2) / min(d1, d2)
            cos_a = math.cos(math.radians(angle))
            sin_a = math.sin(math.radians(angle))
            mean_dist = 0
            
            for pt in contour:
                dx, dy = pt[0][0] - cx, pt[0][1] - cy
                x_rot = dx * cos_a + dy * sin_a
                y_rot = -dx * sin_a + dy * cos_a
                # Menghindari pembagian dengan nol jika d1 atau d2 sangat kecil
                term1 = (x_rot ** 2) / ((d1 / 2) ** 2) if d1 > 1e-6 else 0
                term2 = (y_rot ** 2) / ((d2 / 2) ** 2) if d2 > 1e-6 else 0
                mean_dist += abs(1 - (term1 + term2))
                
            mean_dist /= len(contour)
            return 1 / (1 + mean_dist + ellipse_aspect)
        except cv2.error:
            return 0

    @staticmethod
    def calculate_angular_coverage(contour):
        """Menghitung seberapa merata titik-titik kontur mengelilingi pusatnya."""
        if len(contour) < 5: return 0
        try:
            (cx, cy), _, _ = cv2.fitEllipse(contour)
            angles = sorted(math.degrees(math.atan2(pt[0][1]-cy, pt[0][0]-cx)) % 360 for pt in contour)
            gaps = [angles[i] - angles[i-1] for i in range(1, len(angles))]
            gaps.append(360 - angles[-1] + angles[0]) # Celah melingkar
            return max(0, 1 - max(gaps) / 360)
        except cv2.error:
            return 0

    # =================================================================================
    # 3. FUNGSI DETEKTOR BENTUK DASAR
    # =================================================================================
    @staticmethod
    def detect_circles(image, output_draw):
        """Mendeteksi semua kontur yang memenuhi kriteria lingkaran."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.bilateralFilter(gray, 11, 75, 75)
        edges = cv2.Canny(blurred, 30, 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, OpenSquareCircleChecker._CIRCLE_PREPROC_KERNEL)
        processed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
        processed = cv2.morphologyEx(processed, cv2.MORPH_DILATE, kernel, iterations=1)
        contours, _ = cv2.findContours(processed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_circles = []
        for cnt in [c for c in contours if cv2.contourArea(c) >= OpenSquareCircleChecker._CIRCLE_MIN_ABS_CONTOUR_AREA]:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < OpenSquareCircleChecker._CIRCLE_MIN_ABS_DIMENSION or h < OpenSquareCircleChecker._CIRCLE_MIN_ABS_DIMENSION:
                continue

            aspect = OpenSquareCircleChecker.calculate_aspect_ratio(w, h)
            circ = max(OpenSquareCircleChecker.calculate_circularity(cnt), OpenSquareCircleChecker.calculate_ellipse_circularity(cnt))
            coverage = OpenSquareCircleChecker.calculate_angular_coverage(cnt)
            
            # Tentukan warna visualisasi berdasarkan apakah lingkaran ini valid atau tidak
            is_valid_circle = aspect <= OpenSquareCircleChecker._CIRCLE_MAX_ASPECT_RATIO and \
                              circ > OpenSquareCircleChecker._CIRCLE_MIN_CIRCULARITY and \
                              coverage > OpenSquareCircleChecker._CIRCLE_MIN_ANGULAR_COVERAGE

            if is_valid_circle:
                center = (int(x + w / 2), int(y + h / 2))
                diameter = max(w, h)
                valid_circles.append((center, diameter))
                
                # Visualisasi untuk lingkaran yang valid
                cv2.circle(output_draw, center, 7, (255, 0, 0), -1) # Titik tengah biru
                cv2.rectangle(output_draw, (x, y), (x + w, y + h), (0, 255, 0), 2) # BBox hijau
                cv2.putText(output_draw, "Circle", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                if len(cnt) >= 5:
                    try:
                        cv2.ellipse(output_draw, cv2.fitEllipse(cnt), (0, 200, 255), 2)
                    except cv2.error: pass
            else:
                 # Visualisasi untuk kontur yang terdeteksi tapi tidak lolos sebagai lingkaran
                cv2.rectangle(output_draw, (x, y), (x + w, y + h), (0, 165, 255), 1) # BBox oranye tipis
                cv2.putText(output_draw, "Not Circle", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

        return valid_circles

    @staticmethod
    def detect_open_square(image, output_draw):
        """Mendeteksi kontur terbesar dan mencoba mengekstrak bentuk 'kotak terbuka' darinya."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None

        main_contour = max(contours, key=cv2.contourArea)
        approx = cv2.approxPolyDP(main_contour, OpenSquareCircleChecker._SQUARE_APPROX_FACTOR * cv2.arcLength(main_contour, True), True)
        pts = [tuple(pt[0]) for pt in approx]
        if len(pts) < 4: return None

        sorted_pts = sorted(pts, key=lambda p: (p[1], p[0]))
        tl, tr = (sorted_pts[0], sorted_pts[1]) if sorted_pts[0][0] < sorted_pts[1][0] else (sorted_pts[1], sorted_pts[0])
        index_map = {pt: i for i, pt in enumerate(pts)}
        
        def neighbor(pt, offset): return pts[(index_map[pt] + offset) % len(pts)]

        bl_candidates = [neighbor(tl, d) for d in (-1, 1) if neighbor(tl, d)[1] > tl[1]]
        if not bl_candidates: return None
        bl = max(bl_candidates, key=lambda p: p[1])

        br_candidates = [neighbor(tr, d) for d in (-1, 1) if neighbor(tr, d)[1] > tr[1]]
        if not br_candidates: return None
        br = max(br_candidates, key=lambda p: p[1])
        
        cv2.line(output_draw, tr, br, (0, 255, 0), 2)
        cv2.line(output_draw, br, bl, (0, 0, 255), 2)
        cv2.line(output_draw, bl, tl, (255, 255, 0), 2)
        cv2.putText(output_draw, "Open Square", (tr[0], tr[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return (tl, tr, br, bl)

    # =================================================================================
    # 4. FUNGSI BANTU GEOMETRI
    # =================================================================================
    @staticmethod
    def draw_extended_line(output_draw, pt1, pt2, color=(255, 0, 255), thickness=2):
        """Menggambar garis yang diperpanjang jauh melewati kedua titiknya."""
        dx, dy = pt2[0] - pt1[0], pt2[1] - pt1[1]
        p_start = (int(pt1[0] - dx * 1000), int(pt1[1] - dy * 1000))
        p_end = (int(pt1[0] + dx * 1000), int(pt1[1] + dy * 1000))
        cv2.line(output_draw, p_start, p_end, color, thickness)

    @staticmethod
    def line_segment_intersect(A, B, C, D):
        """Memeriksa apakah segmen garis AB berpotongan dengan segmen CD."""
        x1, y1 = A; x2, y2 = B; x3, y3 = C; x4, y4 = D
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if abs(denom) < 1e-10: return None
        
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        
        if not (0 <= ub <= 1): return None 
        
        return (x1 + ua * (x2 - x1), y1 + ua * (y2 - y1))

    # =================================================================================
    # 5. FUNGSI UTAMA (CHECK)
    # =================================================================================
    @staticmethod
    def check(image_path, min_circle_ratio=0.5):
        """Fungsi utama untuk menjalankan seluruh alur deteksi dan validasi."""
        try:
            image = cv2.imread(image_path)
            if image is None: raise FileNotFoundError(f"Gambar tidak ditemukan: {image_path}")

            if max(image.shape) > OpenSquareCircleChecker._MAX_DIMENSION:
                scale = OpenSquareCircleChecker._MAX_DIMENSION / max(image.shape)
                image = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))

            canvas = image.copy()
            circles = OpenSquareCircleChecker.detect_circles(image, canvas)
            square = OpenSquareCircleChecker.detect_open_square(image, canvas)

            is_valid, status_text, color = False, "INVALID: Combination not found", (0, 0, 255)
            
            # --- PERUBAHAN LOGIKA VALIDASI DIMULAI DI SINI ---
            
            if len(circles) > 1:
                # ATURAN BARU: Jika terdeteksi lebih dari satu lingkaran, langsung invalid.
                status_text = f"INVALID: More than one circle detected ({len(circles)})"
            
            elif len(circles) == 1 and square:
                # Logika asli hanya berjalan jika ada TEPAT SATU lingkaran dan satu kotak.
                circle_center, circle_diameter = circles[0]
                tl, tr, br, bl = square
                # Menghindari pembagian dengan nol jika kotak sangat kecil
                square_side = math.hypot(tr[0] - tl[0], tr[1] - tl[1])
                
                ratio = circle_diameter / square_side if square_side > 0 else 0
                cv2.putText(canvas, f"Circle Dia: {circle_diameter:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                cv2.putText(canvas, f"Square Side: {square_side:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                cv2.putText(canvas, f"Ratio: {ratio:.2f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

                if ratio >= min_circle_ratio:
                    OpenSquareCircleChecker.draw_extended_line(canvas, circle_center, br)
                    for side_p1, side_p2 in [(bl, tl), (tl, tr)]:
                        intersect_pt = OpenSquareCircleChecker.line_segment_intersect(circle_center, br, side_p1, side_p2)
                        if intersect_pt:
                            is_valid, status_text, color = True, "VALID: Open Square-Circle detected", (0, 255, 0)
                            cv2.circle(canvas, (int(intersect_pt[0]), int(intersect_pt[1])), 8, (0, 255, 255), -1)
                            break # Hentikan pencarian setelah perpotongan ditemukan
                    
                    if not is_valid:
                        status_text = "INVALID: Line does not intersect square"
                else:
                    status_text = "INVALID: Circle too small for square"
            
            elif not circles:
                status_text = "INVALID: No circle detected"
            
            elif not square:
                status_text = "INVALID: No open square detected"

            # --- AKHIR PERUBAHAN LOGIKA VALIDASI ---
            
            cv2.putText(canvas, status_text, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            return 1 if is_valid else 0, canvas

        except Exception as e:
            print(f"Error during check: {str(e)}")
            error_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(error_img, "An error occurred", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)
            cv2.putText(error_img, str(e)[:60], (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return 0, error_img

# --- Bagian Eksekusi Kode ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        score, result_img = OpenSquareCircleChecker.check(image_path)
        print(f"Path: {image_path}")
        print(f"Score: {score}")
        if result_img is not None:
            cv2.imshow("Open Square Circle Checker Result", result_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Penggunaan: python <nama_script.py> <path_ke_gambar>")