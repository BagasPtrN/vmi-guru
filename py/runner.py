# Jembatan antara web app dan checker simbol asli (folder symbols/ tidak diubah).
#
# Tampilan rapi: selama checker berjalan, cv2.putText diganti sementara sehingga
# tulisan TIDAK digambar di atas gambar (hanya garis korektor yang tersisa).
# Teks yang seharusnya ditulis dikumpulkan dan dikirim ke aplikasi sebagai
# "keterangan", lalu ditampilkan rapi di pojok kiri bawah saat gambar diperbesar.
import sys, io, json, base64, importlib, contextlib, traceback
import cv2

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

DISPLAY_MAX = 720
_real_putText = cv2.putText


def _encode(img):
    h, w = img.shape[:2]
    s = min(1.0, DISPLAY_MAX / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(enc.tobytes()).decode()


def _clean_notes(drawn, result):
    """Ambil teks yang ditulis ke gambar hasil, buang label posisi (mis. 'Garis 1', 'NO GAP'),
    urutkan: status VALID/INVALID dulu, lalu angka-angka pengukuran."""
    on_result = [t for img, t in drawn if img is result]
    texts = on_result or [t for _, t in drawn]
    out = []
    for t in texts:
        if t in out:
            continue
        if ":" not in t and "VALID" not in t.upper():
            continue  # label penunjuk posisi tidak berarti tanpa letaknya
        out.append(t)
    status = [t for t in out if "VALID" in t.upper()]
    rest = [t for t in out if t not in status]
    return (status + rest)[:10]


def run(module_name, image_path):
    log = io.StringIO()

    drawn = []  # (gambar tujuan, teks)

    def _capture_text(img, text, *args, **kwargs):
        t = str(text).strip()
        if t:
            drawn.append((img, t))
        return img

    err = None
    score, result = 0, None
    cv2.putText = _capture_text
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            try:
                mod = importlib.import_module(f"symbols.{module_name}")
                cls = getattr(mod, module_name.title().replace("_", "") + "Checker")
                score, result = cls.check(image_path)
            except Exception as e:  # sama seperti GUI desktop: error -> skor 0
                err = repr(e)
                traceback.print_exc()
    finally:
        cv2.putText = _real_putText

    notes = _clean_notes(drawn, result)

    # Checker yang gagal membuat kanvas hitam berisi pesan error → tampilkan foto aslinya saja
    if result is None or (err is None and score == 0 and result.max() == 0):
        result = cv2.imread(image_path)
    return json.dumps({
        "score": int(score),
        "image": _encode(result) if result is not None else None,
        "notes": notes[:12],
        "error": err,
        "log": log.getvalue()[-1500:],
    })
