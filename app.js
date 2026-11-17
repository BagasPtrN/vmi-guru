/* Penilaian VMI — antarmuka web untuk guru.
 * Penilaian otomatis memakai kode Python asli (folder py/symbols) lewat Pyodide di worker.js.
 */
"use strict";

// ---------------------------------------------------------------------------
// 1. Data simbol (urutan sama dengan SYMBOL_MODULES di gui/app.py)
// ---------------------------------------------------------------------------
const SYMBOLS = [
  { mod: "vertical_line",      name: "Garis tegak",               icon: "M24 7V41" },
  { mod: "horizontal_line",    name: "Garis mendatar",            icon: "M7 24H41" },
  { mod: "circle",             name: "Lingkaran",                 icon: "M38 24a14 14 0 1 1-28 0a14 14 0 1 1 28 0" },
  { mod: "cross",              name: "Tanda tambah (+)",          icon: "M24 8V40M8 24H40" },
  { mod: "right_oblique",      name: "Garis miring kanan (/)",    icon: "M12 38L36 10" },
  { mod: "square",             name: "Persegi",                   icon: "M10 10H38V38H10Z" },
  { mod: "left_oblique",       name: "Garis miring kiri (\\)",    icon: "M12 10L36 38" },
  { mod: "oblique_cross",      name: "Silang miring (×)",         icon: "M11 11L37 37M37 11L11 37" },
  { mod: "triangle",           name: "Segitiga",                  icon: "M24 8L41 38H7Z" },
  { mod: "open_square_circle", name: "Persegi terbuka + lingkaran", icon: "M7 6V27H23V6M39 34a8 8 0 1 1-16 0a8 8 0 1 1 16 0" },
  { mod: "three_line_cross",   name: "Silang tiga garis",         icon: "M7 24H41M16 9L32 39M32 9L16 39" },
  { mod: "directional_arrows", name: "Panah empat arah",          icon: "M24 6V42M6 24H42M19 11L24 6L29 11M19 37L24 42L29 37M11 19L6 24L11 29M37 19L42 24L37 29" },
  { mod: "two_dimensional_rings", name: "Cincin dua dimensi",      icon: "M28 18a9 9 0 1 1-18 0a9 9 0 1 1 18 0M38 18a9 9 0 1 1-18 0a9 9 0 1 1 18 0M33 31a9 9 0 1 1-18 0a9 9 0 1 1 18 0" },
  { mod: "six_circle_triangle", name: "Segitiga enam lingkaran",   icon: "M27 9a3 3 0 1 1-6 0a3 3 0 1 1 6 0M20 22a3 3 0 1 1-6 0a3 3 0 1 1 6 0M34 22a3 3 0 1 1-6 0a3 3 0 1 1 6 0M13 36a3 3 0 1 1-6 0a3 3 0 1 1 6 0M27 36a3 3 0 1 1-6 0a3 3 0 1 1 6 0M41 36a3 3 0 1 1-6 0a3 3 0 1 1 6 0" },
  { mod: "circle_tilted_square", name: "Lingkaran + persegi miring", icon: "M22 24a8 8 0 1 1-16 0a8 8 0 1 1 16 0M22 24L32 14L42 24L32 34Z" },
  { mod: "vertical_diamond",   name: "Belah ketupat tegak",       icon: "M24 5L35 24L24 43L13 24Z" },
  { mod: "tilted_triangles",   name: "Segitiga miring",           icon: "M8 40L14 8L42 30ZM12 28L23 17L28 33Z" },
  { mod: "eight_dot_circle",   name: "Lingkaran delapan titik",   icon: "M24 8h.1M35 13h.1M40 24h.1M35 35h.1M24 40h.1M13 35h.1M8 24h.1M13 13h.1" },
  { mod: "wertheimer_hexagons", name: "Segi enam Wertheimer",     icon: "M6 18L12 10H22L26 18L22 26H12ZM22 26L26 20H36L42 28L36 36H26Z" },
  { mod: "horizontal_diamond", name: "Belah ketupat mendatar",    icon: "M5 24L24 14L43 24L24 34Z" },
  { mod: "three_dimensional_rings", name: "Cincin tiga dimensi",  icon: "M27 18a9 9 0 1 1-18 0a9 9 0 1 1 18 0M24 18a6 6 0 1 1-12 0a6 6 0 1 1 12 0M39 18a9 9 0 1 1-18 0a9 9 0 1 1 18 0M36 18a6 6 0 1 1-12 0a6 6 0 1 1 12 0M33 31a9 9 0 1 1-18 0a9 9 0 1 1 18 0M30 31a6 6 0 1 1-12 0a6 6 0 1 1 12 0" },
  { mod: "necker_cube",        name: "Kubus Necker",              icon: "M8 16H32V40H8ZM16 8H40V32H16ZM8 16L16 8M32 16L40 8M8 40L16 32M32 40L40 32" },
  { mod: "tapered_box",        name: "Kotak meruncing",           icon: "M6 10H42V38H6ZM20 20H32V28H20ZM6 10L20 20M42 10L32 20M6 38L20 28M42 38L32 28" },
  { mod: "three_dimensional_star", name: "Bintang tiga dimensi",  icon: "M24 4L42 34H6ZM24 44L6 14H42Z" },
];
const N = SYMBOLS.length;
const APP_V = "10";  // naikkan setiap rilis agar HP mengambil versi terbaru
const PROCESS_MAX = 1000;  // sama dengan _MAX_DIMENSION di checker

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const icon = (d, cls = "") => `<svg class="${cls}" viewBox="0 0 48 48" aria-hidden="true"><path d="${d}"/></svg>`;
const ui = {
  cam: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>',
  img: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 16l5-5 4 4 3-3 6 6"/><circle cx="16" cy="9" r="1.5"/></svg>',
  crop: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2v16h16M2 6h16v16"/></svg>',
  trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>',
  yes: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>',
  no: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  print: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z"/></svg>',
  dl: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>',
  upl: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20V9M7 14l5-5 5 5M5 4h14"/></svg>',
  info: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>',
  redo: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></svg>',
};

// ---------------------------------------------------------------------------
// 2. Penyimpanan (IndexedDB, hanya di HP/laptop guru — tidak dikirim ke server)
// ---------------------------------------------------------------------------
const db = (() => {
  let p;
  const open = () => p || (p = new Promise((res, rej) => {
    const r = indexedDB.open("vmi-guru", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("tests", { keyPath: "id" });
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  }));
  const tx = async (mode, fn) => {
    const d = await open();
    return new Promise((res, rej) => {
      const t = d.transaction("tests", mode);
      const out = fn(t.objectStore("tests"));
      t.oncomplete = () => res(out && out.result !== undefined ? out.result : out);
      t.onerror = () => rej(t.error);
    });
  };
  return {
    put: (v) => tx("readwrite", (s) => s.put(v)),
    get: (id) => tx("readonly", (s) => s.get(id)).then(padItems),
    del: (id) => tx("readwrite", (s) => s.delete(id)),
    all: () => tx("readonly", (s) => s.getAll()).then((a) => (a || []).map(padItems)),
  };
})();

// Tes lama (versi 12 simbol) dilengkapi slot kosong agar sama panjang dengan daftar simbol sekarang
function padItems(t) {
  if (t && Array.isArray(t.items)) while (t.items.length < N) t.items.push({ src: null, res: null, auto: 0, final: null, empty: true });
  return t;
}

// ---------------------------------------------------------------------------
// 3. Mesin penilai (Web Worker)
// ---------------------------------------------------------------------------
const engine = {
  worker: null, state: "idle", pending: new Map(), seq: 0,
  start() {
    if (this.worker) return;
    this.worker = new Worker("worker.js?v=" + APP_V, { type: "module" });
    this.setState("loading", "Menyiapkan mesin…");
    this.worker.onmessage = (e) => {
      const m = e.data;
      if (m.type === "status") this.setState(m.pct >= 100 ? "ready" : "loading", m.text, m.pct);
      else if (m.type === "ready") this.setState("ready", "Mesin siap");
      else if (m.type === "fatal") { console.error(m.message); this.setState("error", "Gagal memuat — cek internet"); }
      else if (m.type === "result" || m.type === "error") {
        const cb = this.pending.get(m.id);
        this.pending.delete(m.id);
        cb && cb(m);
      }
    };
    this.worker.onerror = (ev) => {
      ev.preventDefault && ev.preventDefault();
      this.setState("error", "Gagal memuat — cek internet");
      for (const [id, cb] of this.pending) cb({ type: "error", id, message: "worker" });
      this.pending.clear();
    };
    this.worker.postMessage({ type: "init" });
  },
  setState(state, text, pct) {
    this.state = state; this.text = text; this.pct = pct;
    const b = $("#engineBadge");
    b.dataset.state = state; b.title = text;
    $(".txt", b).textContent = { loading: "Memuat…", ready: "Siap", error: "Gagal" }[state] || "";
    document.dispatchEvent(new CustomEvent("engine"));
  },
  check(idx, mod, blob) {
    this.start();
    return blob.arrayBuffer().then((bytes) => new Promise((res) => {
      const id = ++this.seq;
      this.pending.set(id, res);
      this.worker.postMessage({ type: "check", id, idx, module: mod, bytes }, [bytes]);
    }));
  },
  restart() { if (this.worker) this.worker.terminate(); this.worker = null; this.pending.clear(); this.start(); },
};

// ---------------------------------------------------------------------------
// 4. Utilitas gambar
// ---------------------------------------------------------------------------
function loadImage(src) {
  return new Promise((res, rej) => {
    const url = src instanceof Blob ? URL.createObjectURL(src) : src;
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error("Gambar tidak bisa dibuka"));
    im.src = url;
  });
}
function canvasToBlob(c, type = "image/png", q) {
  return new Promise((r) => c.toBlob(r, type, q));
}
/** Potong + putar + kecilkan ke maks 1000 px, putih di belakang (untuk PNG transparan). */
async function prepare(img, rot = 0, crop = null) {
  const src = rotated(img, rot);
  const r = crop || { x: 0, y: 0, w: src.width, h: src.height };
  const s = Math.min(1, PROCESS_MAX / Math.max(r.w, r.h));
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(r.w * s)); c.height = Math.max(1, Math.round(r.h * s));
  const g = c.getContext("2d");
  g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height);
  g.imageSmoothingQuality = "high";
  g.drawImage(src, r.x, r.y, r.w, r.h, 0, 0, c.width, c.height);
  return canvasToBlob(c, "image/png");
}
function rotated(img, rot) {
  const w = img.naturalWidth || img.width, h = img.naturalHeight || img.height;
  const lim = Math.min(1, 2400 / Math.max(w, h));
  const W = Math.round(w * lim), H = Math.round(h * lim);
  const c = document.createElement("canvas");
  const swap = rot % 2 === 1;
  c.width = swap ? H : W; c.height = swap ? W : H;
  const g = c.getContext("2d");
  g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height);
  g.translate(c.width / 2, c.height / 2); g.rotate((rot * Math.PI) / 2);
  g.drawImage(img, -W / 2, -H / 2, W, H);
  return c;
}
const urlCache = new WeakMap();
const blobUrl = (b) => { if (!b) return ""; if (!urlCache.has(b)) urlCache.set(b, URL.createObjectURL(b)); return urlCache.get(b); };

// ---------------------------------------------------------------------------
// 5. Dialog potong foto
// ---------------------------------------------------------------------------
const cropper = {
  open(file) {
    return new Promise(async (resolve) => {
      let img;
      try { img = await loadImage(file); } catch { toast("Foto tidak bisa dibuka"); return resolve(null); }
      const dlg = $("#cropDlg"), cv = $("#cropCanvas"), rectEl = $("#cropRect"), stage = $("#cropStage");
      let rot = 0, work, sel = null, start = null;
      const draw = () => {
        work = rotated(img, rot);
        const maxW = Math.min(stage.clientWidth || 640, 900), maxH = window.innerHeight * 0.58;
        const s = Math.min(maxW / work.width, maxH / work.height, 1);
        cv.width = Math.round(work.width * s); cv.height = Math.round(work.height * s);
        cv.getContext("2d").drawImage(work, 0, 0, cv.width, cv.height);
        sel = null; rectEl.hidden = true;
      };
      const pos = (e) => {
        const b = cv.getBoundingClientRect();
        return { x: Math.max(0, Math.min(b.width, e.clientX - b.left)), y: Math.max(0, Math.min(b.height, e.clientY - b.top)), b };
      };
      const paint = () => {
        if (!sel) { rectEl.hidden = true; return; }
        const b = cv.getBoundingClientRect(), sb = stage.getBoundingClientRect();
        Object.assign(rectEl.style, { left: b.left - sb.left + sel.x + "px", top: b.top - sb.top + sel.y + "px", width: sel.w + "px", height: sel.h + "px" });
        rectEl.hidden = false;
      };
      const down = (e) => { start = pos(e); stage.setPointerCapture(e.pointerId); sel = { x: start.x, y: start.y, w: 0, h: 0 }; paint(); };
      const move = (e) => {
        if (!start) return;
        const p = pos(e);
        sel = { x: Math.min(start.x, p.x), y: Math.min(start.y, p.y), w: Math.abs(p.x - start.x), h: Math.abs(p.y - start.y) };
        paint();
      };
      const up = () => { start = null; if (sel && (sel.w < 14 || sel.h < 14)) { sel = null; paint(); } };
      stage.onpointerdown = down; stage.onpointermove = move; stage.onpointerup = up; stage.onpointercancel = up;
      $("#cropRotate").onclick = () => { rot = (rot + 1) % 4; draw(); };
      $("#cropReset").onclick = () => { sel = null; paint(); };
      const finish = async (ok) => {
        let crop = null;
        if (ok && sel) {   // hitung sebelum dialog ditutup (setelah ditutup ukurannya 0)
          const b = cv.getBoundingClientRect(), k = work.width / b.width;
          crop = { x: sel.x * k, y: sel.y * k, w: sel.w * k, h: sel.h * k };
        }
        dlg.onclose = null;
        if (dlg.open) dlg.close();
        if (!ok) return resolve(null);
        resolve(await prepare(img, rot, crop));
      };
      $("#cropOk").onclick = () => finish(true);
      dlg.onclose = () => finish(false);
      dlg.showModal();
      requestAnimationFrame(draw);
    });
  },
};

// ---------------------------------------------------------------------------
// 6. State & routing
// ---------------------------------------------------------------------------
const state = { draft: null, current: null };
function newDraft() {
  const d = new Date();
  return {
    child: { name: "", ageY: "", ageM: "", cls: localStorage.getItem("vmi-cls") || "", examiner: localStorage.getItem("vmi-examiner") || "", date: d.toISOString().slice(0, 10) },
    slots: Array.from({ length: N }, () => ({ blob: null, file: null })),
  };
}
function setHeader(title, sub, back) {
  $("#pageTitle").textContent = title;
  $("#pageSub").textContent = sub;
  $("#backBtn").hidden = !back;
  document.title = title + " — Penilaian VMI";
}
function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }
$("#backBtn").onclick = () => (history.length > 1 ? history.back() : go("#/"));
window.addEventListener("hashchange", route);

async function route() {
  const h = location.hash || "#/";
  const main = $("#main");
  document.body.classList.remove("has-bar");
  const old = $(".actionbar"); old && old.remove();
  if (h.startsWith("#/baru")) await viewNew(main);
  else if (h.startsWith("#/hasil/")) await viewResult(main, h.split("/")[2]);
  else if (h.startsWith("#/kriteria")) await viewCriteria(main);
  else await viewHome(main);
  window.scrollTo(0, 0);
  main.focus({ preventScroll: true });
}

let toastT;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 2600);
}
const fmtDate = (s) => { try { return new Date(s + "T00:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }); } catch { return s; } };
const ageText = (c) => [c.ageY ? `${c.ageY} th` : "", c.ageM ? `${c.ageM} bln` : ""].filter(Boolean).join(" ") || "–";
const finalOf = (it) => (it.final ?? it.auto);
const totalOf = (t) => t.items.reduce((a, it) => a + (finalOf(it) === 1 ? 1 : 0), 0);

// ---------------------------------------------------------------------------
// 7. Halaman: Beranda
// ---------------------------------------------------------------------------
async function viewHome(main) {
  setHeader("Penilaian VMI", "Asisten koreksi untuk guru", false);
  const tests = (await db.all()).sort((a, b) => (b.created || 0) - (a.created || 0));
  const resume = state.draft && state.draft.slots.some((s) => s.blob);
  main.innerHTML = `
    <section class="hero">
      ${icon("M7 24H41M16 9L32 39M32 9L16 39", "hero-art")}
      <h2>Nilai gambar anak dalam hitungan detik</h2>
      <p>Foto gambar tes VMI (sampai 24 simbol), aplikasi memberi penilaian awal, lalu Ibu/Bapak guru tinggal memastikan benar atau salah.</p>
      <div class="row wrap">
        <a class="btn primary lg" href="#/baru">${ui.plus}${resume ? "Lanjutkan tes" : "Mulai tes baru"}</a>
        <button class="btn ghost" id="demoBtn">Coba dengan contoh</button>
      </div>
    </section>
    <div class="steps" aria-label="Cara pakai">
      <div class="step"><b>1</b><p>Isi nama &amp; usia anak</p></div>
      <div class="step"><b>2</b><p>Foto tiap gambar (bisa dari galeri)</p></div>
      <div class="step"><b>3</b><p>Periksa hasil &amp; koreksi bila perlu</p></div>
    </div>

    <a class="card doc-link" href="#/kriteria">
      <span class="crit-ic">${icon("M12 8h24v32H12zM18 16h12M18 23h12M18 30h8")}</span>
      <span class="grow"><b>Kriteria penilaian (acuan)</b><small>Syarat lulus tiap simbol menurut Manual VMI</small></span>
      <svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg>
    </a>

    <section class="section" aria-labelledby="hTitle">
      <div class="section-title">
        <h2 id="hTitle">Riwayat penilaian</h2>
        ${tests.length ? `<button class="btn ghost" id="csvBtn">${ui.dl}Unduh rekap</button>` : ""}
      </div>
      ${tests.length ? `
        <label class="sr" for="q" hidden>Cari nama anak</label>
        <input class="search" id="q" type="search" placeholder="Cari nama anak atau kelas…" aria-label="Cari nama anak atau kelas">
        <div class="list" id="list" style="margin-top:10px"></div>` : `
        <div class="card empty">
          ${icon("M10 10H38V38H10ZM16 20H32M16 27H28")}
          <p><b>Belum ada penilaian.</b><br>Hasil tes yang sudah dinilai akan muncul di sini dan tersimpan di perangkat ini.</p>
        </div>`}
    </section>
    <p class="hint small">Data anak hanya disimpan di perangkat ini (tidak diunggah ke internet). Hasil otomatis adalah alat bantu — keputusan akhir tetap pada guru.</p>`;

  $("#demoBtn").onclick = () => {
    const dlg = $("#demoDlg");
    dlg.querySelectorAll(".demo-opt").forEach((b) => (b.onclick = () => { dlg.close(); loadDemo(b.dataset.mode); }));
    dlg.showModal();
  };
  if (!tests.length) return;
  const list = $("#list");
  const render = (q = "") => {
    const f = tests.filter((t) => (t.child.name + " " + t.child.cls).toLowerCase().includes(q.toLowerCase()));
    list.innerHTML = f.map((t) => {
      const done = t.items.filter((i) => finalOf(i) != null).length;
      return `<button class="item" data-id="${t.id}">
        <span class="avatar" aria-hidden="true">${esc((t.child.name || "?").trim().charAt(0).toUpperCase())}</span>
        <span class="who"><b>${esc(t.child.name || "Tanpa nama")}</b>
          <span>${esc(ageText(t.child))}${t.child.cls ? " · " + esc(t.child.cls) : ""} · ${fmtDate(t.child.date)}</span></span>
        ${(() => { const K = vmiConclusion(t); const ok = !K.pending && !K.st.error;
          return `<span class="pill ${ok ? "tone-" + K.st.cat.tone : ""}" aria-label="${ok ? `Skor standar ${K.st.ss}, ${K.st.cat.label}` : `Skor mentah ${K.raw}`}">${ok ? `${K.st.op}${K.st.ss}<small>${esc(K.st.cat.label)}</small>` : `${K.raw}/30${done < t.items.length ? "*" : ""}`}</span>`; })()}
      </button>`;
    }).join("") || `<p class="muted">Tidak ada yang cocok.</p>`;
    list.querySelectorAll(".item").forEach((b) => (b.onclick = () => go("#/hasil/" + b.dataset.id)));
  };
  render();
  $("#q").oninput = (e) => render(e.target.value);
  $("#csvBtn").onclick = () => exportCsv(tests);
}

const DEMO_NAMES = { mix: "Contoh Campuran", valid: "Contoh Semua Benar", invalid: "Contoh Semua Salah" };
async function loadDemo(mode = "mix") {
  // Campuran: acak, tapi minimal 3 benar & 3 salah
  let pick;
  if (mode === "mix") {
    do { pick = SYMBOLS.map(() => (Math.random() < 0.5 ? "valid" : "invalid")); }
    while (pick.filter((p) => p === "valid").length < 3 || pick.filter((p) => p === "invalid").length < 3);
  } else pick = SYMBOLS.map(() => mode);
  state.draft = newDraft();
  state.draft.child.name = DEMO_NAMES[mode] || "Contoh Anak";
  state.draft.child.ageY = "5";
  go("#/baru");
  toast(`Memuat ${N} gambar contoh…`);
  const blobs = await Promise.all(SYMBOLS.map((_, i) => fetch(`sample/${pick[i]}/${i + 1}.png`).then((r) => r.blob())));
  blobs.forEach((b, i) => (state.draft.slots[i].blob = b));
  if (location.hash.startsWith("#/baru")) route();
}

function exportCsv(tests) {
  const head = ["Nama", "Usia (th)", "Usia (bln)", "Kelas", "Tanggal", "Pemeriksa", "Skor mentah", "Skor standar", "Kategori", "Persentil", "Usia perkembangan", "Jumlah gambar benar", ...SYMBOLS.map((s, i) => `${i + 1}. ${s.name}`), "Catatan"];
  const rows = tests.map((t) => { const K = vmiConclusion(t); const ok = !K.pending && !K.st.error; return [t.child.name, t.child.ageY, t.child.ageM, t.child.cls, t.child.date, t.child.examiner,
    K.raw, ok ? K.st.op + K.st.ss : "", ok ? K.st.cat.label : "", ok ? K.st.pct ?? "" : "", K.ae.text, totalOf(t),
    ...t.items.map((it) => (finalOf(it) == null ? "" : finalOf(it))), t.notes || ""]; });
  const csv = [head, ...rows].map((r) => r.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
  a.download = `rekap-vmi-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

// ---------------------------------------------------------------------------
// 8. Halaman: Tes baru
// ---------------------------------------------------------------------------
async function viewNew(main) {
  setHeader("Tes baru", "Langkah 1–2: data anak & foto gambar", true);
  engine.start();
  if (!state.draft) state.draft = newDraft();
  const d = state.draft, c = d.child;
  main.innerHTML = `
    <section class="card" aria-labelledby="cTitle">
      <h2 id="cTitle" style="font-size:18px;font-weight:800;margin-bottom:12px">Data anak</h2>
      <div class="form-grid">
        <div class="field full"><label for="fName">Nama anak <span class="muted">(wajib)</span></label>
          <input id="fName" autocomplete="off" value="${esc(c.name)}" placeholder="mis. Aisyah Putri" required></div>
        <div class="field"><label id="ageLbl">Usia</label>
          <div class="age-row" role="group" aria-labelledby="ageLbl">
            <select id="fAgeY" aria-label="Tahun">${opt(["", "2", "3", "4", "5", "6", "7", "8"], c.ageY, (v) => (v ? v + " tahun" : "Tahun"))}</select>
            <select id="fAgeM" aria-label="Bulan">${opt(["", ...Array.from({ length: 12 }, (_, i) => String(i))], c.ageM, (v) => (v === "" ? "Bulan" : v + " bulan"))}</select>
          </div></div>
        <div class="field"><label for="fDate">Tanggal tes</label><input id="fDate" type="date" value="${esc(c.date)}"></div>
        <div class="field"><label for="fCls">Kelas / kelompok</label><input id="fCls" value="${esc(c.cls)}" placeholder="mis. TK B1"></div>
        <div class="field"><label for="fEx">Nama pemeriksa</label><input id="fEx" value="${esc(c.examiner)}" placeholder="mis. Bu Rina"></div>
      </div>
    </section>

    <section class="section" aria-labelledby="sTitle">
      <div class="section-title"><h2 id="sTitle">Foto ${N} gambar</h2><span class="muted small" id="filledTxt"></span></div>
      <div class="notice" style="margin-bottom:12px">${ui.info}<div>Satu foto untuk satu gambar. Foto tegak lurus dari atas, cahaya terang, tanpa bayangan. Setelah memotret, geser jari untuk memilih bagian gambarnya saja.</div></div>
      <div class="row wrap" style="margin-bottom:12px">
        <button class="btn ghost" id="manyBtn">${ui.upl}Pilih banyak foto sekaligus</button>
        <button class="btn ghost danger" id="clearBtn">${ui.trash}Kosongkan</button>
      </div>
      <div class="slots" id="slots"></div>
    </section>`;

  const bind = (id, key, store) => { const el = $(id); el.oninput = el.onchange = () => { c[key] = el.value; if (store) localStorage.setItem(store, el.value); }; };
  bind("#fName", "name"); bind("#fAgeY", "ageY"); bind("#fAgeM", "ageM"); bind("#fDate", "date");
  bind("#fCls", "cls", "vmi-cls"); bind("#fEx", "examiner", "vmi-examiner");

  const slotsEl = $("#slots");
  const renderSlots = () => {
    slotsEl.innerHTML = d.slots.map((s, i) => {
      const sym = SYMBOLS[i];
      return `<div class="slot ${s.blob ? "filled" : ""}" data-i="${i}">
        <div class="slot-head"><span class="num">${i + 1}</span><span class="slot-name">${esc(sym.name)}</span>${icon(sym.icon, "slot-ref")}</div>
        <button class="slot-body" data-act="${s.blob ? "view" : "cam"}" aria-label="${s.blob ? "Lihat foto " : "Ambil foto "}${esc(sym.name)}">
          ${s.blob ? `<img src="${blobUrl(s.blob)}" alt="Foto gambar ${esc(sym.name)}">` : `<span class="ph">${ui.cam}Ketuk untuk memotret</span>`}
        </button>
        <div class="slot-actions">
          ${s.blob
            ? `<button class="btn ghost" data-act="${s.file ? "recrop" : "cam"}">${s.file ? ui.crop + "Rapikan" : ui.cam + "Ulang"}</button>
               <button class="btn ghost" data-act="del" aria-label="Hapus foto ${esc(sym.name)}">${ui.trash}</button>`
            : `<button class="btn ghost" data-act="cam">${ui.cam}Kamera</button>
               <button class="btn ghost" data-act="gal">${ui.img}Galeri</button>`}
        </div></div>`;
    }).join("");
    const filled = d.slots.filter((s) => s.blob).length;
    $("#filledTxt").textContent = `${filled} dari ${N} terisi`;
    bar.querySelector(".meta").innerHTML = `<b>${filled}/${N}</b> foto siap<br><span id="engTxt">${engineLine()}</span>`;
    bar.querySelector("#scoreBtn").disabled = filled === 0;
  };
  const engineLine = () => engine.state === "ready" ? "Mesin penilai siap" : engine.state === "error" ? "Mesin gagal dimuat" : esc(engine.text || "Menyiapkan mesin…");

  const pick = (input) => new Promise((res) => {
    input.value = ""; input.onchange = () => res(input.files && input.files[0] ? input.files[0] : null); input.click();
  });
  slotsEl.onclick = async (e) => {
    const b = e.target.closest("[data-act]"); if (!b) return;
    const i = +b.closest(".slot").dataset.i, s = d.slots[i], act = b.dataset.act;
    if (act === "del") { s.blob = s.file = null; renderSlots(); return; }
    if (act === "view") { viewer.open(SYMBOLS[i].name, null, blobUrl(s.blob), "Foto yang akan dinilai."); return; }
    const file = act === "recrop" ? s.file : await pick(act === "gal" ? $("#fileOne") : $("#fileCam"));
    if (!file) return;
    const blob = await cropper.open(file);
    if (blob) { s.blob = blob; s.file = file; renderSlots(); }
  };
  $("#manyBtn").onclick = async () => {
    const inp = $("#fileMany"); inp.value = "";
    inp.onchange = async () => {
      const files = [...inp.files].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
      if (!files.length) return;
      const targets = files.length >= N ? d.slots.map((_, i) => i) : d.slots.map((s, i) => (s.blob ? -1 : i)).filter((i) => i >= 0);
      let n = 0;
      for (const f of files) {
        if (n >= targets.length) break;
        try { const im = await loadImage(f); const s = d.slots[targets[n]]; s.blob = await prepare(im); s.file = f; n++; } catch {}
      }
      renderSlots();
      toast(`${n} foto dimasukkan sesuai urutan nama file. Ketuk "Rapikan" bila perlu.`);
    };
    inp.click();
  };
  $("#clearBtn").onclick = () => { if (confirm("Hapus semua foto di tes ini?")) { d.slots.forEach((s) => (s.blob = s.file = null)); renderSlots(); } };

  const bar = document.createElement("div");
  bar.className = "actionbar";
  bar.innerHTML = `<div class="inner"><div class="meta grow"></div><button class="btn primary lg" id="scoreBtn">Nilai sekarang</button></div>`;
  document.body.appendChild(bar);
  const onEng = () => { const t = $("#engTxt"); if (t) t.innerHTML = engineLine(); };
  document.addEventListener("engine", onEng);
  renderSlots();

  $("#scoreBtn").onclick = async () => {
    if (!c.name.trim()) { toast("Isi nama anak dulu ya."); $("#fName").focus(); return; }
    const filled = d.slots.filter((s) => s.blob).length;
    if (filled < N && !confirm(`Baru ${filled} dari ${N} gambar yang difoto. Gambar yang kosong dihitung "tidak dikerjakan" (skor 0). Lanjut menilai?`)) return;
    const test = {
      id: (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()),
      created: Date.now(), child: { ...c, name: c.name.trim() }, notes: "",
      items: d.slots.map((s) => ({ src: s.blob, res: null, auto: s.blob ? null : 0, final: null, empty: !s.blob })),
    };
    await db.put(test);
    state.draft = null;
    document.removeEventListener("engine", onEng);
    state.current = test;
    go("#/hasil/" + test.id);
    runScoring(test);
  };
}
function opt(vals, cur, label) { return vals.map((v) => `<option value="${v}" ${String(cur) === v ? "selected" : ""}>${label(v)}</option>`).join(""); }

// ---------------------------------------------------------------------------
// 9. Proses penilaian
// ---------------------------------------------------------------------------
const running = new Set();
const live = new Map();   // tes yang sedang/baru dinilai (objek yang sama dipakai UI)
async function runScoring(test, only = null) {
  if (running.has(test.id)) return;
  if (engine.state === "error") engine.restart();
  running.add(test.id);
  live.set(test.id, test);
  const t0 = performance.now();
  let failed = false;
  for (let i = 0; i < N; i++) {
    const it = test.items[i];
    if (it.empty || (only != null && only !== i)) continue;
    it.auto = null; it.res = null; it.error = null; it.busy = true;
    refreshItem(test, i);
    const r = await engine.check(i, SYMBOLS[i].mod, it.src);
    it.busy = false;
    if (r.type === "error" && engine.state !== "ready") {
      // mesin gagal dimuat (biasanya karena internet) — jangan anggap anak salah
      failed = true;
      refreshItem(test, i);
      toast("Mesin penilai gagal dimuat. Periksa internet lalu tekan \"Nilai ulang otomatis\".");
      break;
    }
    if (r.type === "error") { it.auto = 0; it.error = r.message; }
    else { it.auto = r.score ? 1 : 0; it.res = r.image; it.notes = r.notes || []; it.criteria = r.criteria || null; it.error = r.error; it.ms = r.ms; }
    await db.put(stripBusy(test));
    refreshItem(test, i);
  }
  test.lastRunMs = Math.round(performance.now() - t0);
  await db.put(stripBusy(test));
  running.delete(test.id);
  refreshSummary(test);
  if (!failed && location.hash === "#/hasil/" + test.id) toast("Selesai! Silakan periksa tiap gambar — kesimpulan ada di atas.");
}
const stripBusy = (t) => ({ ...t, items: t.items.map(({ busy, ...r }) => r) });

// ---------------------------------------------------------------------------
// 10. Halaman: Hasil
// ---------------------------------------------------------------------------
async function viewResult(main, id) {
  let test = live.get(id) || (state.current && state.current.id === id ? state.current : await db.get(id));
  if (!test) { main.innerHTML = `<div class="card empty"><p>Data tidak ditemukan.</p><a class="btn primary" href="#/">Ke beranda</a></div>`; return; }
  state.current = test;
  setHeader(test.child.name || "Hasil", "Langkah 3: periksa & koreksi", true);
  const c = test.child;
  main.innerHTML = `
    <div class="print-only"><h2>Laporan Tes Visual-Motor Integration (VMI)</h2><br></div>
    <section class="card" aria-labelledby="sumTitle">
      <div class="score-hero">
        <div class="ring" id="ring" role="img"><div><span><b id="ringNum">0</b></span><span>skor mentah<br>dari 30</span></div></div>
        <div>
          <h2 id="sumTitle">${esc(c.name)}</h2>
          <dl class="kv" style="margin-top:6px">
            <dt>Usia</dt><dd>${esc(ageText(c))}</dd>
            <dt>Tanggal</dt><dd>${fmtDate(c.date)}</dd>
            ${c.cls ? `<dt>Kelas</dt><dd>${esc(c.cls)}</dd>` : ""}
            ${c.examiner ? `<dt>Pemeriksa</dt><dd>${esc(c.examiner)}</dd>` : ""}
          </dl>
          <div class="chips" id="chips"></div>
        </div>
      </div>
      <div class="progress no-print" id="prog" style="margin-top:14px" hidden>
        <div class="bar"><i id="progBar"></i></div><span class="small muted" id="progTxt"></span>
      </div>
    </section>

    <section class="card section concl" id="concl" aria-labelledby="cTitle"></section>

    <section class="section" aria-labelledby="lTitle">
      <div class="section-title"><h2 id="lTitle">Hasil per gambar</h2></div>
      <p class="hint no-print" style="margin:-4px 0 12px">Garis <b style="color:var(--ok)">hijau</b> = bentuk dikenali, <b style="color:var(--no)">merah</b> = tidak memenuhi syarat. Ketuk gambar untuk memperbesar, lalu tekan <b>Benar</b> atau <b>Salah</b> bila Ibu/Bapak tidak setuju.</p>
      <div class="results" id="results"></div>
    </section>

    <section class="card section" aria-labelledby="nTitle">
      <div class="field"><label id="nTitle" for="notes">Catatan guru</label>
        <textarea id="notes" placeholder="mis. Anak memegang pensil terlalu kuat, cepat lelah di gambar 9…">${esc(test.notes || "")}</textarea></div>
      <p class="print-only" id="notesPrint"></p>
    </section>

    <div class="row wrap no-print">
      <button class="btn primary" id="printBtn">${ui.print}Cetak / simpan PDF</button>
      <button class="btn ghost" id="rerunBtn">${ui.redo}Nilai ulang otomatis</button>
      <span class="grow"></span>
      <button class="btn danger" id="delBtn">${ui.trash}Hapus</button>
    </div>
    <details class="section no-print small muted"><summary>Info teknis</summary><div id="tech"></div></details>`;

  $("#concl").onclick = async (e) => {
    const b = e.target.closest("[data-early],[data-early-mode]"); if (!b) return;
    if (b.dataset.earlyMode === "manual") test.early = vmiRawScore({ ...test, early: null }).earlyVals.slice();
    else if (b.dataset.earlyMode === "auto") test.early = null;
    else { const k = +b.dataset.early; test.early = (test.early || [0, 0, 0, 0, 0, 0]).slice(); test.early[k] = test.early[k] ? 0 : 1; }
    await db.put(stripBusy(test)); refreshSummary(test);
  };
  const resEl = $("#results");
  resEl.innerHTML = test.items.map((_, i) => `<article class="res" id="res${i}" aria-labelledby="rt${i}"></article>`).join("");
  test.items.forEach((_, i) => refreshItem(test, i));
  refreshSummary(test);

  resEl.onclick = async (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const i = +b.closest(".res").id.slice(3), it = test.items[i];
    if (b.dataset.act === "view") {
      viewer.open(`${i + 1}. ${SYMBOLS[i].name}`, it.res, blobUrl(it.src), it.error ? "Catatan sistem: " + it.error : "", i, it);
      return;
    }
    if (b.dataset.v != null) {
      const v = +b.dataset.v;
      it.final = v === it.auto ? null : v;   // sama dengan otomatis → bukan koreksi
      if (it.empty) it.final = v === 0 ? null : v;
      await db.put(stripBusy(test));
      refreshItem(test, i); refreshSummary(test);
    }
  };
  let nt;
  $("#notes").oninput = (e) => { test.notes = e.target.value; clearTimeout(nt); nt = setTimeout(() => db.put(stripBusy(test)), 400); };
  $("#printBtn").onclick = () => { $("#notesPrint").textContent = test.notes ? "Catatan: " + test.notes : ""; window.print(); };
  $("#rerunBtn").onclick = () => { if (!running.has(test.id)) { test.items.forEach((it) => (it.final = null)); runScoring(test); } };
  $("#delBtn").onclick = async () => { if (confirm(`Hapus hasil tes ${c.name}? Tindakan ini tidak bisa dibatalkan.`)) { await db.del(test.id); state.current = null; go("#/"); toast("Hasil tes dihapus."); } };

  // Tes yang tersimpan tapi belum selesai dinilai (mis. aplikasi ditutup) → lanjutkan
  // atau hasil dari versi lama (belum ada hasil per kriteria) → nilai ulang otomatis; koreksi guru tetap
  if (!running.has(test.id) && test.items.some((it) => !it.empty && (it.auto == null || (it.res && !it.criteria)))) runScoring(test);
}

function refreshItem(test, i) {
  const el = document.getElementById("res" + i);
  if (!el || state.current !== test) return;
  const it = test.items[i], sym = SYMBOLS[i], f = finalOf(it);
  el.className = "res " + (it.busy || f == null ? "pending" : f ? "pass" : "fail");
  const thumb = it.res || (it.src ? blobUrl(it.src) : "");
  let autoTxt;
  if (it.empty) autoTxt = "Tidak difoto — dihitung tidak dikerjakan";
  else if (it.busy) autoTxt = "Sedang dinilai…";
  else if (it.auto == null) autoTxt = "Menunggu giliran…";
  else {
    const ev = evaluateCriteria(i, it);
    autoTxt = `Penilaian otomatis: <b style="color:${it.auto ? "var(--ok)" : "var(--no)"}">${it.auto ? "Benar" : "Salah"}</b>`;
    if (ev && ev.failed) {
      const nf = ev.rows.filter((r) => r.state === "no").length;
      autoTxt += `<span class="why no">✗ Kriteria ${ev.failed.n}: ${esc(ev.failed.t)}${nf > 1 ? ` (+${nf - 1} kriteria lain)` : ""}</span>`;
    } else if (ev) {
      autoTxt += `<span class="why ok">✓ Memenuhi ${ev.rows.length === 1 ? "kriteria" : `semua ${ev.rows.length} kriteria`} manual</span>`;
    }
  }
  el.innerHTML = `
    <button class="thumb" data-act="view" ${thumb ? "" : "disabled"} aria-label="Perbesar gambar ${esc(sym.name)}">
      ${it.busy ? '<span class="spinner" aria-hidden="true"></span>' : thumb ? `<img src="${thumb}" alt="">` : icon(sym.icon, "slot-ref")}
    </button>
    <div>
      <h3 id="rt${i}"><span class="num">${i + 1}</span>${esc(sym.name)} ${it.final != null ? '<span class="edited">dikoreksi guru</span>' : ""}</h3>
      <p class="auto">${autoTxt}</p>
      <div class="verdict" role="group" aria-label="Keputusan guru untuk ${esc(sym.name)}">
        <button class="yes" data-v="1" aria-pressed="${f === 1}" ${it.busy || (f == null && !it.empty) ? "disabled" : ""}>${ui.yes}Benar</button>
        <button class="no" data-v="0" aria-pressed="${f === 0}" ${it.busy || (f == null && !it.empty) ? "disabled" : ""}>${ui.no}Salah</button>
      </div>
    </div>`;
  refreshSummary(test);
}

function refreshSummary(test) {
  if (state.current !== test || !$("#ring")) return;
  const done = test.items.filter((it) => !it.busy && finalOf(it) != null).length;
  const edited = test.items.filter((it) => it.final != null).length;
  const K = vmiConclusion(test);
  $("#ring").style.setProperty("--p", (K.raw / 30) * 100);
  $("#ring").setAttribute("aria-label", `Skor mentah ${K.raw} dari 30`);
  $("#ringNum").textContent = K.raw;
  const pass = test.items.filter((it) => finalOf(it) === 1).length;
  $("#chips").innerHTML = `
    <span class="chip ok">${pass} gambar benar</span>
    <span class="chip no">${test.items.filter((it) => finalOf(it) === 0).length} salah</span>
    ${edited ? `<span class="chip warn">${edited} dikoreksi guru</span>` : ""}`;
  $("#concl").innerHTML = conclusionHtml(test, K);
  test.items.forEach((_, i) => {
    const el = document.getElementById("res" + i);
    if (el) el.classList.toggle("past-ceil", K.ceiling != null && i + 7 > K.ceiling);
  });
  const busy = done < N;
  $("#prog").hidden = !busy;
  if (busy) {
    $("#progBar").style.width = (done / N) * 100 + "%";
    $("#progTxt").textContent = engine.state === "ready" ? `Menilai ${done}/${N}…` : engine.text || "Menyiapkan…";
  }
  const ms = test.items.filter((i) => i.ms).map((i) => i.ms);
  $("#tech").innerHTML = `<p>Penilaian otomatis memakai checker Python + OpenCV (versi 2, mengikuti kriteria Manual VMI) yang dijalankan di browser lewat Pyodide.
    ${ms.length ? `Rata-rata ${Math.round(ms.reduce((a, b) => a + b, 0) / ms.length)} ms per simbol di perangkat ini.` : ""}</p>`;
}
document.addEventListener("engine", () => { if (state.current) refreshSummary(state.current); });

function conclusionHtml(test, K) {
  const st = K.st;
  let main;
  if (K.pending) main = `<p class="muted">Kesimpulan muncul setelah semua gambar selesai dinilai.</p>`;
  else if (st.error === "usia") main = `<p class="warn-box">Usia anak belum diisi, jadi skor standar belum bisa dihitung.</p>`;
  else if (st.error === "muda") main = `<p class="warn-box">Tabel norma untuk usia di bawah 4 tahun (2:0–3:11) belum dimasukkan ke aplikasi, jadi skor standar belum tersedia. Skor mentah tetap bisa dicatat.</p>`;
  else if (st.error === "tua") main = `<p class="warn-box">Usia di luar tabel norma (maks. 69:11).</p>`;
  else main = `
      <div class="concl-grid">
        <div class="big tone-${st.cat.tone}"><span>Skor standar</span><b>${st.op}${st.ss}</b>
          <small>${st.op ? "di luar batas tabel" : `kemungkinan ${st.ss - st.sem}–${st.ss + st.sem} (±${st.sem})`}</small></div>
        <div class="big tone-${st.cat.tone}"><span>Kategori</span><b class="cat">${esc(st.cat.label)}</b><small>${esc(st.cat.en)}</small></div>
        <div class="big"><span>Persentil</span><b>${st.pct ?? "–"}</b><small>${st.pct ? `lebih baik dari ±${st.pct}% anak seusianya` : ""}</small></div>
        <div class="big"><span>Usia perkembangan</span><b class="cat">≈ ${esc(K.ae.text)}</b><small>usia saat skor ini = rata-rata</small></div>
      </div>
      <p class="verdict-line tone-${K.verdict.tone}">${esc(K.verdict.text)}</p>`;
  const early = K.earlyMode === "basal"
    ? `<p class="small muted">Item 1–6 (mencoret & meniru) otomatis diberi poin karena anak berhasil di salah satu item 7–9.
        <button class="linkbtn" data-early-mode="manual">Isi manual</button></p>`
    : `<div class="early ${K.earlyMode === "perlu" && !K.pending ? "need" : ""}">
        <p class="small">${K.earlyMode === "perlu"
          ? "<b>Anak belum berhasil di gambar 1–3 (item 7–9).</b> Menurut manual, berikan tugas mencoret & meniru (item 1–6), lalu centang yang berhasil:"
          : "Item 1–6 diisi guru:"}</p>
        <div class="early-list">${EARLY_ITEMS.map((t, k) => `<button class="${K.earlyVals[k] ? "on" : ""}" data-early="${k}" aria-pressed="${!!K.earlyVals[k]}">
          <span class="mk">${K.earlyVals[k] ? "✓" : ""}</span>${k + 1}. ${esc(t)} <small>(${EARLY_AGE[k]})</small></button>`).join("")}</div>
        ${Array.isArray(test.early) ? `<button class="linkbtn" data-early-mode="auto">Kembalikan ke otomatis</button>` : ""}
      </div>`;
  const ceil = K.ceiling
    ? `Penghitungan berhenti di item ${K.ceiling} (3 gagal berturut-turut)${K.passedAfter ? `; ${K.passedAfter} gambar benar sesudahnya tidak dihitung sesuai aturan manual` : ""}.`
    : "Tidak ada 3 kegagalan berturut-turut — semua item dihitung.";
  return `
    <div class="section-title" style="margin:0 0 8px"><h2 id="cTitle">Kesimpulan akhir</h2>
      <span class="small muted">usia ${esc(ageText(test.child))}${st.band ? ` · tabel ${fmtAge(st.band[0])}–${fmtAge(st.band[1])}` : ""}</span></div>
    ${main}
    <p class="small muted" style="margin-top:10px"><b>Skor mentah ${K.raw}/30</b> = item 1–6 (${K.earlyVals.reduce((a, b) => a + b, 0)}) + gambar yang benar sebelum berhenti. ${ceil}</p>
    ${early}
    <p class="hint small" style="margin-top:8px">Skrining, bukan diagnosis. Skor standar dari tabel norma Manual Beery VMI (Lampiran C); persentil & usia perkembangan adalah perkiraan.</p>`;
}

// ---------------------------------------------------------------------------
// 10b. Kriteria Manual VMI (tampilan)
// ---------------------------------------------------------------------------
const STATE_LABEL = { ok: ["✓", "Terpenuhi"], no: ["✗", "Tidak terpenuhi"], na: ["–", "Belum dinilai"], guru: ["?", "Dicek guru"] };
function criteriaHtml(i, it, ev) {
  const C = CRITERIA[i];
  const verdict = it.auto ? '<b class="ok">VALID — memenuhi kriteria</b>' : '<b class="no">INVALID — tidak memenuhi kriteria</b>';
  const rows = ev.rows.map((r) => `<li class="crit ${r.state}" title="${STATE_LABEL[r.state][1]}">
      <span class="mk" aria-label="${STATE_LABEL[r.state][1]}">${STATE_LABEL[r.state][0]}</span>
      <span>${r.n}. ${esc(r.t)}${r.detail ? `<small class="crit-det">${esc(r.detail)}</small>` : ""}</span></li>`).join("");
  const meas = (it.notes || []).filter((t) => !/\bVALID\b|\bINVALID\b|^Status|^Reason|^K\d+:/i.test(t));
  return `<div class="cap-head">${verdict}<span class="cap-form">${esc(C.form)}</span></div>
    <ul class="crit-list">${rows}</ul>
    ${ev.rows.some((r) => r.state === "na") ? '<p class="na-note">– = hasil versi lama, tekan "Nilai ulang otomatis" untuk penilaian per kriteria</p>' : ""}
    ${meas.length ? `<details class="meas"><summary>Detail pengukuran program</summary>
      <div>${meas.map((t) => `<span>${esc(t)}</span>`).join("")}</div></details>` : ""}`;
}

async function viewCriteria(main) {
  setHeader("Kriteria penilaian", "Acuan: Manual Beery VMI", true);
  main.innerHTML = `
    <section class="card">
      <h2 style="font-size:20px;font-weight:800">Kriteria penilaian ${N} simbol</h2>
      <p class="muted" style="margin:8px 0 0">Diringkas dari Manual Beery VMI (Scoring Criteria, Form 4–18, dan tabel
        <i>Summary Scoring</i>). Skor tiap simbol <b>1</b> bila semua kriteria terpenuhi, <b>0</b> bila ada yang tidak.
        Aturan umum manual: <b>"Jangan menilai terlalu ketat — jika ragu, beri skor lulus."</b></p>
      <div class="legend">
        <span><span class="tag auto">Dicek program</span> semua kriteria diperiksa otomatis; guru tetap bisa mengoreksi hasil akhirnya</span>
      </div>
    </section>
    <section class="card section" id="hitung">
      <h2 style="font-size:18px;font-weight:800">Cara menghitung kesimpulan akhir</h2>
      <ol class="calc-steps">
        <li><b>Skor mentah (0–30).</b> Tes lengkap punya 30 item: item 1–6 mencoret & meniru, item 7–30 = 24 gambar di aplikasi ini.
          Poin dihitung berurutan sampai anak <b>gagal 3 item berturut-turut</b>; item sesudahnya tidak dihitung.
          Item 1–6 otomatis diberi poin bila anak berhasil di salah satu gambar 1–3 (item 7–9); bila tidak, guru memberikan tugas mencoret/meniru dan mencentangnya.</li>
        <li><b>Skor standar.</b> Skor mentah dicocokkan dengan usia anak pada tabel norma Manual Beery VMI (Lampiran C, kelompok usia per 2 bulan).
          Rata-rata anak seusianya = 100.</li>
        <li><b>Kategori</b> (Tabel 1 manual):
          <table class="cat-table"><tr><th>Skor standar</th><th>Kategori</th><th>% anak</th></tr>
          <tr><td>&gt; 129</td><td>Sangat tinggi</td><td>2</td></tr><tr><td>120–129</td><td>Tinggi</td><td>7</td></tr>
          <tr><td>110–119</td><td>Di atas rata-rata</td><td>16</td></tr><tr><td>90–109</td><td><b>Rata-rata (sesuai usia)</b></td><td>50</td></tr>
          <tr><td>80–89</td><td>Di bawah rata-rata</td><td>16</td></tr><tr><td>70–79</td><td>Rendah</td><td>7</td></tr>
          <tr><td>&lt; 70</td><td>Sangat rendah</td><td>2</td></tr></table></li>
        <li><b>Rentang ± SEM.</b> Skor sebenarnya kira-kira ±4–6 poin dari skor yang didapat (Tabel 7 manual).</li>
      </ol>
      <p class="small muted">Persentil dihitung dari kurva normal dan usia perkembangan diperkirakan dari tabel yang sama (perkiraan).
        Tabel untuk usia 2:0–3:11 belum tersedia di aplikasi.</p>
    </section>
    <div class="crit-docs">
      ${SYMBOLS.map((s, i) => { const C = CRITERIA[i]; return `
      <article class="card crit-card" id="k${i + 1}">
        <header class="crit-card-head">
          <span class="crit-ic">${icon(s.icon)}</span>
          <div><h3>${i + 1}. ${esc(s.name)}</h3>
            <p class="small muted">${esc(C.form)} · norma usia ${esc(C.age)}</p></div>
        </header>
        <ol class="crit-ol">
          ${C.items.map((c) => `<li><span>${esc(c.t)}</span>
            <span class="tag ${c.auto ? "auto" : "guru"}">${c.auto ? "Dicek program" : "Dicek guru"}</span>
            <small class="en">${esc(c.en)}</small></li>`).join("")}
        </ol>
        <p class="how small"><b>Cara program memeriksa:</b> ${esc(C.how)}</p>
      </article>`; }).join("")}
    </div>
    <p class="hint small">Ukuran dalam inci dari manual dikonversi ke mm sebagai perkiraan. Norma usia ditulis tahun:bulan.</p>`;
}

// ---------------------------------------------------------------------------
// 11. Penampil gambar besar
// ---------------------------------------------------------------------------
const viewer = {
  open(title, res, orig, hint, idx, it) {
    const dlg = $("#viewDlg"), img = $("#viewImg"), a = $("#segRes"), b = $("#segOrig"), cap = $("#viewCap");
    $("#viewTitle").textContent = title; $("#viewHint").textContent = hint || "";
    // Keterangan akhir: perbandingan dengan kriteria Manual VMI (sama untuk semua simbol)
    const ev = idx != null && it ? evaluateCriteria(idx, it) : null;
    cap.innerHTML = ev ? criteriaHtml(idx, it, ev) : "";
    const hasCap = !!ev;
    const show = (which) => {
      const useRes = which === "res" && res;
      img.src = useRes ? res : orig; img.alt = (useRes ? "Hasil deteksi " : "Foto asli ") + title;
      a.setAttribute("aria-selected", !!useRes); b.setAttribute("aria-selected", !useRes);
      cap.hidden = !hasCap;
    };
    a.disabled = !res; a.onclick = () => show("res"); b.onclick = () => show("orig");
    $(".seg", dlg).hidden = !res;
    show(res ? "res" : "orig");
    dlg.showModal();
  },
};

// ---------------------------------------------------------------------------
// 12. Mulai
// ---------------------------------------------------------------------------
window.addEventListener("beforeunload", (e) => {
  if (state.draft && state.draft.slots.some((s) => s.blob)) { e.preventDefault(); e.returnValue = ""; }
});
if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("sw.js").catch(() => {});
route();
