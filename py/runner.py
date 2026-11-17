# Jembatan antara web app dan checker simbol asli (folder symbols/ tidak diubah).
import sys, io, json, base64, importlib, contextlib, traceback
import cv2

if "/app" not in sys.path:
    sys.path.insert(0, "/app")

DISPLAY_MAX = 720


def _encode(img):
    h, w = img.shape[:2]
    s = min(1.0, DISPLAY_MAX / max(h, w))
    if s < 1.0:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return "data:image/jpeg;base64," + base64.b64encode(enc.tobytes()).decode()


def run(module_name, image_path):
    log = io.StringIO()
    err = None
    score, result = 0, None
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            mod = importlib.import_module(f"symbols.{module_name}")
            cls = getattr(mod, module_name.title().replace("_", "") + "Checker")
            score, result = cls.check(image_path)
        except Exception as e:  # sama seperti GUI desktop: error -> skor 0
            err = repr(e)
            traceback.print_exc()
    if result is None:
        result = cv2.imread(image_path)
    return json.dumps({
        "score": int(score),
        "image": _encode(result) if result is not None else None,
        "error": err,
        "log": log.getvalue()[-1500:],
    })
