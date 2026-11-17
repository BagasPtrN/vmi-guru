/* Mesin penilai: Pyodide + OpenCV menjalankan kode Python asli di browser.
 * Dijalankan sebagai module worker (Pyodide 314 tidak mendukung classic worker). */
import { loadPyodide } from "./pyodide/pyodide.mjs";
// Pyodide 314.0.8 (Python 3.14 + numpy + OpenCV 4.11) disimpan di repo ini sendiri (folder pyodide/),
// jadi tidak bergantung pada CDN luar yang kadang diblokir jaringan sekolah.
const PYODIDE_BASE = new URL("pyodide/", self.location.href).href;
const SYMBOL_FILES = [
  "__init__", "vertical_line", "horizontal_line", "circle", "cross",
  "right_oblique", "square", "left_oblique", "oblique_cross", "triangle",
  "open_square_circle", "three_line_cross", "directional_arrows",
];



let ready = null;
let runFn = null;

function status(text, pct) {
  self.postMessage({ type: "status", text, pct });
}

async function init() {
  status("Memuat Python…", 10);
  const py = await loadPyodide({ indexURL: PYODIDE_BASE });
  status("Memuat OpenCV (±25 MB, hanya pertama kali)…", 35);
  await py.loadPackage(["numpy", "opencv-python"]);
  status("Memuat kode penilai…", 85);
  py.FS.mkdirTree("/app/symbols");
  const base = new URL("py/", self.location.href);
  const fetchText = async (p) => {
    const r = await fetch(new URL(p, base));
    if (!r.ok) throw new Error("Gagal memuat " + p);
    return r.text();
  };
  await Promise.all(
    SYMBOL_FILES.map(async (n) =>
      py.FS.writeFile(`/app/symbols/${n}.py`, await fetchText(`symbols/${n}.py`))
    )
  );
  py.FS.writeFile("/app/runner.py", await fetchText("runner.py"));
  await py.runPythonAsync(
    "import sys, warnings\nwarnings.filterwarnings('ignore')\nsys.path.insert(0,'/app')\nimport runner"
  );
  runFn = py.pyimport("runner").run;
  self.py = py;
  status("Siap", 100);
  self.postMessage({ type: "ready" });
}

function start() {
  if (!ready) ready = init().catch((err) => {
    self.postMessage({ type: "fatal", message: String((err && err.message) || err) });
    throw err;
  });
}

self.onmessage = async (e) => {
  const msg = e.data;
  try {
    if (msg.type === "init") {
      start();
      await ready;
      return;
    }
    if (msg.type === "check") {
      start();
      await ready;
      const path = `/tmp/in_${msg.idx}.png`;
      self.py.FS.writeFile(path, new Uint8Array(msg.bytes));
      const t0 = performance.now();
      const out = JSON.parse(runFn(msg.module, path));
      out.ms = Math.round(performance.now() - t0);
      self.postMessage({ type: "result", id: msg.id, idx: msg.idx, ...out });
    }
  } catch (err) {
    self.postMessage({ type: "error", id: msg.id, idx: msg.idx, message: String(err && err.message || err) });
  }
};
