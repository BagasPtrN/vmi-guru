import cv2
import numpy as np
import math
import random
import sys
from itertools import combinations

class ThreeLineCrossChecker:
    """
    Kelas untuk mendeteksi dan memvalidasi konfigurasi 'cross' yang terbentuk dari tiga garis,
    menggunakan RANSAC untuk deteksi garis yang kokoh dan serangkaian aturan validasi geometris.
    """
    # =================================================================================
    # 1. KONSTANTA UNTUK PARAMETER DETEKSI
    # =================================================================================
    # Parameter RANSAC
    _RANSAC_MAX_ITERS_DIAG = 2000
    _RANSAC_MAX_ITERS_ORTHO = 1000
    _RANSAC_DIST_THRESHOLD = 2.5
    _RANSAC_MIN_INLIERS = 25
    _RANSAC_MIN_LINE_LENGTH = 50.0
    _RANSAC_MAX_GAP = 8.0
    _RANSAC_MAX_POINTS = 5000

    # Parameter Pra-pemrosesan
    _PROCESS_HEIGHT = 145
    _DISPLAY_HEIGHT = 500
    _CLAHE_CLIP_LIMIT = 3.0
    _CLAHE_GRID_SIZE = (12, 12)
    _BILATERAL_D = 7
    _BILATERAL_SIGMA = 100
    _CANNY_APERTURE_SIZE = 5
    _MORPH_KERNEL_SIZE = (5, 5)
    _DILATE_ITERATIONS = 1
    _CLOSE_ITERATIONS = 3

    # Parameter Pra-pemrosesan Khusus untuk Deteksi Celah (Gap)
    _GAP_CLAHE_CLIP_LIMIT = 2.0
    _GAP_CLAHE_GRID_SIZE = (8, 8)
    _GAP_BILATERAL_D = 5
    _GAP_BILATERAL_SIGMA = 75
    _GAP_CANNY_APERTURE_SIZE = 3
    _GAP_MORPH_KERNEL = (3, 3)
    _GAP_CLOSE_ITERATIONS = 2
    _GAP_MIN_CONTOUR_AREA = 50

    # Parameter Validasi Geometris
    _INTERSECTION_TOLERANCE = 1e-10
    _MAX_GAP_BETWEEN_INTERSECTIONS = 100.0
    _ORTHO_DOMINANCE_THRESHOLD = 15.0 # Sudut deviasi maks untuk dianggap dominan H/V
    _DIAG_MIN_V_DEVIATION = 10.0   # Deviasi minimum diagonal dari vertikal (90 deg)

    # Rentang Sudut (derajat)
    _DIAG_1_ANGLE = (25, 65)
    _DIAG_2_ANGLE = (115, 155)
    _HORIZ_ANGLE_1 = (0, 15)
    _HORIZ_ANGLE_2 = (165, 180)
    _VERT_ANGLE = (75, 105)

    # Parameter untuk Multi-Run Validation
    _N_RUNS = 10
    _VALIDATION_THRESHOLD_PERCENT = 50.0

    # =================================================================================
    # 2. ALGORITMA INTI: RANSAC
    # =================================================================================
    @staticmethod
    def ransac_fit_line(points, max_iters, distance_threshold, angle_constraint, min_line_length, max_gap):
        """Mendeteksi garis secara kokoh dari sekumpulan titik menggunakan RANSAC dengan berbagai batasan."""
        best_inliers, best_line = [], None
        n_points = len(points)
        if n_points < 2:
            return None, np.empty((0,2), dtype=int)

        for _ in range(max_iters):
            idx1, idx2 = random.sample(range(n_points), 2)
            pt1, pt2 = points[idx1], points[idx2]
            
            if math.hypot(pt2[0]-pt1[0], pt2[1]-pt1[1]) < 1e-5: continue

            a, b, c = pt2[1] - pt1[1], pt1[0] - pt2[0], pt2[0]*pt1[1] - pt1[0]*pt2[1]
            if abs(a) + abs(b) < 1e-5: continue

            if angle_constraint:
                angle = math.degrees(math.atan2(-a, b)) % 180
                min_ang, max_ang = angle_constraint
                is_angle_ok = (min_ang <= angle <= max_ang) if min_ang <= max_ang else (angle >= min_ang or angle <= max_ang)
                if not is_angle_ok: continue

            denom = math.hypot(a, b)
            dists = np.abs(a*points[:,0] + b*points[:,1] + c) / denom
            inliers = points[dists < distance_threshold]
            if len(inliers) < ThreeLineCrossChecker._RANSAC_MIN_INLIERS: continue

            if len(inliers) > 2:
                dx, dy = -b, a
                mag = math.hypot(dx, dy)
                if mag < 1e-5: continue
                projs = inliers[:,0]*(dx/mag) + inliers[:,1]*(dy/mag)
                sorted_inliers = inliers[np.argsort(projs)]
                consecutive_dists = np.hypot(np.diff(sorted_inliers[:,0]), np.diff(sorted_inliers[:,1]))
                if np.max(consecutive_dists) > max_gap: continue
            
            if min_line_length:
                dx, dy = -b, a
                mag = math.hypot(dx, dy)
                if mag < 1e-5: continue
                projs = inliers[:,0]*(dx/mag) + inliers[:,1]*(dy/mag)
                p_start, p_end = inliers[np.argmin(projs)], inliers[np.argmax(projs)]
                if math.hypot(p_end[0]-p_start[0], p_end[1]-p_start[1]) < min_line_length: continue
            
            if len(inliers) > len(best_inliers):
                best_inliers, best_line = inliers, (a, b, c)
        
        return best_line, np.array(best_inliers)

    # =================================================================================
    # 3. FUNGSI BANTU GEOMETRI
    # =================================================================================
    @staticmethod
    def compute_angle(a, b):
        """Menghitung sudut garis (dari model ax+by+c=0) dalam rentang [0, 180)."""
        return math.degrees(math.atan2(-a, b)) % 180

    @staticmethod
    def segment_intersection(seg1, seg2):
        """Memeriksa apakah dua segmen garis berpotongan dan mengembalikan titik potongnya."""
        p1, p2 = seg1; p3, p4 = seg2
        x1,y1=float(p1[0]),float(p1[1]); x2,y2=float(p2[0]),float(p2[1])
        x3,y3=float(p3[0]),float(p3[1]); x4,y4=float(p4[0]),float(p4[1])
        dx1, dy1 = x2 - x1, y2 - y1
        dx2, dy2 = x4 - x3, y4 - y3
        
        det = (-dx2 * dy1 + dx1 * dy2)
        if abs(det) < ThreeLineCrossChecker._INTERSECTION_TOLERANCE: return None
        
        s = (-dy1 * (x1 - x3) + dx1 * (y1 - y3)) / det
        t = ( dx2 * (y1 - y3) - dy2 * (x1 - x3)) / det
        
        if 0 <= s <= 1 and 0 <= t <= 1:
            return (x1 + (t * dx1), y1 + (t * dy1))
        return None

    # =================================================================================
    # 4. ALUR KERJA UTAMA
    # =================================================================================
    @classmethod
    def run_detection(cls, image_path, significant_contours, has_gap, contour_count):
        """Menjalankan satu iterasi deteksi dan visualisasi."""
        # --- 4.1 Pra-pemrosesan & Ekstraksi Titik Tepi ---
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None: raise FileNotFoundError(f"Gambar tidak ditemukan: {image_path}")
        
        original_h, original_w = img.shape
        scale = cls._PROCESS_HEIGHT / original_h
        resized = cv2.resize(img, (int(original_w * scale), cls._PROCESS_HEIGHT), interpolation=cv2.INTER_AREA)

        clahe = cv2.createCLAHE(clipLimit=cls._CLAHE_CLIP_LIMIT, tileGridSize=cls._CLAHE_GRID_SIZE)
        enhanced = clahe.apply(resized)
        blurred = cv2.bilateralFilter(enhanced, cls._BILATERAL_D, cls._BILATERAL_SIGMA, cls._BILATERAL_SIGMA)
        v = np.median(blurred)
        edges = cv2.Canny(blurred, int(max(0, 0.5*v)), int(min(255, 1.5*v)), apertureSize=cls._CANNY_APERTURE_SIZE)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, cls._MORPH_KERNEL_SIZE)
        dilated = cv2.dilate(edges, kernel, iterations=cls._DILATE_ITERATIONS)
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=cls._CLOSE_ITERATIONS)
        
        pts = np.argwhere(closed > 0)
        if pts.size == 0:
            result = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
            cv2.putText(result, "No edges detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
            return False, result

        pts_xy = pts[:, ::-1].astype(np.float32)
        if len(pts_xy) > cls._RANSAC_MAX_POINTS:
            pts_xy = pts_xy[np.random.choice(len(pts_xy), cls._RANSAC_MAX_POINTS, replace=False)]

        # --- 4.2 Deteksi Garis Bertahap dengan RANSAC ---
        remaining, lines, inliers_list, segments, line_types = pts_xy.copy(), [], [], [], []
        
        # Tahap 1: Cari 2 garis diagonal
        for stage in [{"angle": cls._DIAG_1_ANGLE}, {"angle": cls._DIAG_2_ANGLE}]:
            if len(remaining) < cls._RANSAC_MIN_INLIERS or len(lines) >= 2: break
            line, inl = cls.ransac_fit_line(remaining, cls._RANSAC_MAX_ITERS_DIAG, cls._RANSAC_DIST_THRESHOLD, stage["angle"], cls._RANSAC_MIN_LINE_LENGTH, cls._RANSAC_MAX_GAP)
            if line:
                lines.append(line); inliers_list.append(inl); line_types.append('diagonal')
                mask = np.ones(len(remaining), dtype=bool)
                for inlier in inl: mask &= ~np.all(np.isclose(remaining, inlier, atol=0.5), axis=1)
                remaining = remaining[mask]
                if len(inl) >= 2:
                    a,b,_ = line; dx,dy = -b,a; mag = math.hypot(dx,dy)
                    if mag > 1e-5:
                        projs = inl[:,0]*(dx/mag) + inl[:,1]*(dy/mag)
                        segments.append( (tuple(inl[np.argmin(projs)]), tuple(inl[np.argmax(projs)])) )
                    else: segments.append(((0,0),(0,0)))
                else: segments.append(((0,0),(0,0)))

        # Tahap 2: Cari 1 garis horizontal (prioritas) atau vertikal
        candidate_lines, candidate_inliers, candidate_types, candidate_segments = [],[],[],[]
        horiz_angle = cls._HORIZ_ANGLE_1 if random.random() > 0.5 else cls._HORIZ_ANGLE_2
        h_line, h_inl = cls.ransac_fit_line(remaining, cls._RANSAC_MAX_ITERS_ORTHO, cls._RANSAC_DIST_THRESHOLD, horiz_angle, cls._RANSAC_MIN_LINE_LENGTH, cls._RANSAC_MAX_GAP)
        if h_line:
            candidate_lines.append(h_line); candidate_inliers.append(h_inl); candidate_types.append('horizontal')
            if len(h_inl) >= 2:
                a,b,_=h_line; dx,dy=-b,a; mag=math.hypot(dx,dy)
                if mag > 1e-5:
                    projs=h_inl[:,0]*(dx/mag)+h_inl[:,1]*(dy/mag)
                    candidate_segments.append((tuple(h_inl[np.argmin(projs)]), tuple(h_inl[np.argmax(projs)])))
                else: candidate_segments.append(((0,0),(0,0)))
            else: candidate_segments.append(((0,0),(0,0)))

        v_line, v_inl = cls.ransac_fit_line(remaining, cls._RANSAC_MAX_ITERS_ORTHO, cls._RANSAC_DIST_THRESHOLD, cls._VERT_ANGLE, cls._RANSAC_MIN_LINE_LENGTH, cls._RANSAC_MAX_GAP)
        if v_line:
            candidate_lines.append(v_line); candidate_inliers.append(v_inl); candidate_types.append('vertical')
            if len(v_inl) >= 2:
                a,b,_=v_line; dx,dy=-b,a; mag=math.hypot(dx,dy)
                if mag > 1e-5:
                    projs=v_inl[:,0]*(dx/mag)+v_inl[:,1]*(dy/mag)
                    candidate_segments.append((tuple(v_inl[np.argmin(projs)]), tuple(v_inl[np.argmax(projs)])))
                else: candidate_segments.append(((0,0),(0,0)))
            else: candidate_segments.append(((0,0),(0,0)))
        
        if candidate_lines:
            best_idx = np.argmax([len(inl) for inl in candidate_inliers])
            lines.append(candidate_lines[best_idx]); inliers_list.append(candidate_inliers[best_idx])
            line_types.append(candidate_types[best_idx]); segments.append(candidate_segments[best_idx])
            mask = np.ones(len(remaining), dtype=bool)
            for inlier in candidate_inliers[best_idx]: mask &= ~np.all(np.isclose(remaining, inlier, atol=0.5), axis=1)
            remaining = remaining[mask]

        # Tahap 3: Jika kurang dari 3, cari garis apa saja
        if len(remaining) >= cls._RANSAC_MIN_INLIERS and len(lines) < 3:
            line, inl = cls.ransac_fit_line(remaining, cls._RANSAC_MAX_ITERS_ORTHO, cls._RANSAC_DIST_THRESHOLD, None, cls._RANSAC_MIN_LINE_LENGTH, cls._RANSAC_MAX_GAP)
            if line:
                lines.append(line); inliers_list.append(inl); line_types.append('unknown')
                if len(inl) >= 2:
                    a,b,_ = line; dx,dy = -b,a; mag = math.hypot(dx,dy)
                    if mag > 1e-5:
                        projs = inl[:,0]*(dx/mag) + inl[:,1]*(dy/mag)
                        segments.append((tuple(inl[np.argmin(projs)]), tuple(inl[np.argmax(projs)])))
                    else: segments.append(((0,0),(0,0)))
                else: segments.append(((0,0),(0,0)))
        
        # --- 4.3 Validasi Konfigurasi Garis ---
        valid_config, status_reason = False, f"Lines found: {len(lines)} (need 3)"
        intersection_points, angles = [], [cls.compute_angle(a,b) for a,b,_ in lines]

        if len(lines) == 3 and len(segments) == 3:
            h_devs = [min(a, 180-a) for a in angles]; v_devs = [abs(a-90) for a in angles]
            min_h, min_v = min(h_devs), min(v_devs)
            
            if min_h <= cls._ORTHO_DOMINANCE_THRESHOLD or min_v <= cls._ORTHO_DOMINANCE_THRESHOLD:
                if min_h < min_v: # Horizontal dominan
                    main_idx = np.argmin(h_devs)
                    line_types[main_idx] = 'horizontal'
                else: # Vertikal dominan
                    main_idx = np.argmin(v_devs)
                    line_types[main_idx] = 'vertical'
                
                if line_types[main_idx] == 'vertical':
                    status_reason = "Third line is vertical (invalid)"
                else:
                    diag_angles = [angles[i] for i in range(3) if i != main_idx]
                    if all(abs(da - 90) >= cls._DIAG_MIN_V_DEVIATION for da in diag_angles):
                        intersections = [cls.segment_intersection(segments[i], segments[j]) for i, j in combinations(range(3), 2)]
                        intersection_points = [p for p in intersections if p is not None]
                        if len(intersection_points) == 3:
                            dists = [math.hypot(p1[0]-p2[0], p1[1]-p2[1]) for p1,p2 in combinations(intersection_points,2)]
                            if max(dists) <= cls._MAX_GAP_BETWEEN_INTERSECTIONS:
                                valid_config, status_reason = True, "VALID"
                            else: status_reason = f"Large gap: {max(dists):.1f}"
                        else: status_reason = f"Intersections: {len(intersection_points)} (need 3)"
                    else: status_reason = "Invalid diagonal angles"
            else: status_reason = "No dominant horizontal line"

        if has_gap: valid_config, status_reason = False, "Gap detected (invalid)"

        # --- 4.4 Visualisasi ---
        display_h, display_w = cls._DISPLAY_HEIGHT, int(cls._DISPLAY_HEIGHT * original_w / original_h)
        display_img = cv2.cvtColor(cv2.resize(img, (display_w, display_h)), cv2.COLOR_GRAY2BGR)
        scale_factor = display_h / cls._PROCESS_HEIGHT
        def scale_pt(p): return (int(p[0] * scale_factor), int(p[1] * scale_factor))

        if significant_contours:
            scaled_contours = [(cnt.astype(np.float32) * scale_factor).astype(np.int32) for cnt in significant_contours]
            cv2.drawContours(display_img, scaled_contours, -1, (255, 0, 255), 1)

        colors = {'diagonal':(0,0,255), 'horizontal':(0,255,0), 'vertical':(255,255,0), 'unknown':(128,128,128)}
        for i, (p1, p2) in enumerate(segments):
            color = colors.get(line_types[i] if i<len(line_types) else 'unknown', (128,128,128))
            cv2.line(display_img, scale_pt(p1), scale_pt(p2), color, 3, cv2.LINE_AA)
            if i < len(angles): cv2.putText(display_img, f"L{i+1}:{angles[i]:.1f}", (10, 40+40*i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        
        for pt in intersection_points: cv2.circle(display_img, scale_pt(pt), 12, (0, 255, 255), -1)
        if len(intersection_points) == 3:
            scaled_pts = [scale_pt(p) for p in intersection_points]
            for i in range(3): cv2.line(display_img, scaled_pts[i], scaled_pts[(i+1)%3], (200,0,200), 3, cv2.LINE_AA)

        status_color = (0, 255, 0) if valid_config else (0, 0, 255)
        cv2.putText(display_img, f"Status: {'VALID' if valid_config else 'INVALID'}", (20, display_h-80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)
        cv2.putText(display_img, f"Reason: {status_reason}", (20, display_h-40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, status_color, 2)
        gap_color = (0, 0, 255) if has_gap else (0, 255, 0)
        cv2.putText(display_img, f"Gap: {'Yes' if has_gap else 'No'} (Contours: {contour_count})", (20, display_h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, gap_color, 2)

        return valid_config, display_img

    @classmethod
    def check(cls, image_path):
        """Menjalankan beberapa iterasi deteksi untuk hasil yang lebih stabil."""
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None: raise FileNotFoundError(f"Image not found: {image_path}")
            
            h, w = img.shape
            scale = cls._PROCESS_HEIGHT / h
            resized = cv2.resize(img, (int(w*scale), cls._PROCESS_HEIGHT), interpolation=cv2.INTER_AREA)
            
            # Pra-pemrosesan untuk deteksi celah (gap)
            clahe = cv2.createCLAHE(clipLimit=cls._GAP_CLAHE_CLIP_LIMIT, tileGridSize=cls._GAP_CLAHE_GRID_SIZE)
            enhanced = clahe.apply(resized)
            blurred = cv2.bilateralFilter(enhanced, cls._GAP_BILATERAL_D, cls._GAP_BILATERAL_SIGMA, cls._GAP_BILATERAL_SIGMA)
            v = np.median(blurred)
            edges = cv2.Canny(blurred, int(max(0, 0.6*v)), int(min(255, 1.4*v)), apertureSize=cls._GAP_CANNY_APERTURE_SIZE)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, cls._GAP_MORPH_KERNEL)
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=cls._GAP_CLOSE_ITERATIONS)
            
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= cls._GAP_MIN_CONTOUR_AREA]
            has_gap = len(significant_contours) > 1
            
            # Lakukan multi-run RANSAC
            valid_count, last_valid, last_invalid = 0, None, None
            for _ in range(cls._N_RUNS):
                valid, result_img = cls.run_detection(image_path, significant_contours, has_gap, len(significant_contours))
                if valid:
                    valid_count += 1
                    last_valid = result_img
                else:
                    last_invalid = result_img
            
            validation_percentage = (valid_count / cls._N_RUNS) * 100
            final_valid = validation_percentage > cls._VALIDATION_THRESHOLD_PERCENT
            final_result = last_valid if final_valid else last_invalid
            
            if final_result is None:
                final_result = cv2.cvtColor(cv2.resize(img, (500, int(500 * h / w))), cv2.COLOR_GRAY2BGR)

            cv2.putText(final_result, f"Validation: {validation_percentage:.0f}% ({valid_count}/{cls._N_RUNS})", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            
            return 1 if final_valid else 0, final_result

        except Exception as e:
            print(f"Error in ThreeLineCrossChecker.check: {e}")
            error_img = np.zeros((300, 500, 3), dtype=np.uint8)
            cv2.putText(error_img, "An error occurred", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 1)
            cv2.putText(error_img, str(e)[:60], (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
            return 0, error_img

# --- Bagian Eksekusi Kode ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        score, result_img = ThreeLineCrossChecker.check(sys.argv[1])
        print(f"Final Score: {score}")
        if result_img is not None:
            cv2.imshow("Three Line Cross Detection", result_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    else:
        print("Usage: python your_script_name.py <image_path>")