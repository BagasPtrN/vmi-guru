/* Kesimpulan akhir Beery VMI: skor mentah (aturan manual) → skor standar menurut usia.
 *
 * Langkah (Manual Beery VMI edisi 6, hlm. 23–29 & 93–96):
 *  1. Skor mentah: 1 poin per item (1–30) sampai 3 kegagalan berturut-turut (ceiling).
 *     Item sebelum keberhasilan pertama yang tidak diujikan tetap diberi poin (basal):
 *     anak yang mulai di item 7 dan berhasil di salah satu item 7–9 otomatis mendapat item 1–6.
 *     Bila item 7–9 semuanya gagal, guru perlu memberikan tugas mencoret/meniru (item 1–6) dan mengisinya.
 *  2. Skor mentah + usia kronologis → skor standar (rata-rata 100, SD 15) dari tabel Lampiran C (norms_data.js).
 *  3. Skor standar dibaca dengan Tabel 1 (kategori) dan diberi rentang ± SEM (Tabel 7).
 *  Persentil dihitung dari kurva normal (perkiraan; tabel konversi hlm. 208 tidak tersedia).
 *  Usia perkembangan = usia saat skor mentah anak setara skor standar 100 (perkiraan dari tabel yang sama).
 */
"use strict";

// Item 1–6 (tugas untuk anak yang belum bisa menyalin)
const EARLY_ITEMS = [
  "Mencoret meniru orang dewasa",
  "Mencoret spontan (diminta tanpa dicontohkan)",
  "Coretan tidak keluar dari kertas",
  "Meniru garis tegak",
  "Meniru garis mendatar",
  "Meniru lingkaran",
];
const EARLY_AGE = ["1:1", "1:4", "1:9", "2:0", "2:6", "2:9"];

// SEM skor standar menurut usia (Tabel 7; dewasa ±5 dari Tabel 6)
const VMI_SEM = { 2: 4, 3: 4, 4: 4, 5: 5, 6: 6, 7: 6, 8: 5, 9: 6, 10: 6, 11: 5, 12: 5, 13: 5, 14: 5, 15: 6, 16: 6, 17: 5 };

const VMI_CATEGORIES = [
  { min: 130, label: "Sangat tinggi", en: "Very High", tone: "ok" },
  { min: 120, label: "Tinggi", en: "High", tone: "ok" },
  { min: 110, label: "Di atas rata-rata", en: "Above Average", tone: "ok" },
  { min: 90, label: "Rata-rata", en: "Average", tone: "ok" },
  { min: 80, label: "Di bawah rata-rata", en: "Below Average", tone: "warn" },
  { min: 70, label: "Rendah", en: "Low", tone: "no" },
  { min: -Infinity, label: "Sangat rendah", en: "Very Low", tone: "no" },
];
const vmiCategory = (ss) => VMI_CATEGORIES.find((c) => ss >= c.min);

function ageMonthsOf(child) {
  const y = parseInt(child && child.ageY, 10);
  if (!Number.isFinite(y)) return null;
  const m = parseInt(child.ageM, 10);
  return y * 12 + (Number.isFinite(m) ? m : 0);
}
const fmtAge = (m) => `${Math.floor(m / 12)}:${m % 12}`;

/** Skor mentah menurut aturan manual. items = 24 item salinan (item 7–30), early = null | [0/1 × 6]. */
function vmiRawScore(test) {
  const copy = test.items.slice(0, 24).map((it) => (it.busy ? null : finalOf(it)));
  const pending = copy.some((v) => v == null);
  const firstPass = copy.findIndex((v) => v === 1);
  const early = Array.isArray(test.early) ? test.early : null;
  let earlyVals, earlyMode;
  if (early) { earlyVals = early.map((v) => (v ? 1 : 0)); earlyMode = "guru"; }
  else if (firstPass >= 0 && firstPass <= 2) { earlyVals = [1, 1, 1, 1, 1, 1]; earlyMode = "basal"; }
  else { earlyVals = [0, 0, 0, 0, 0, 0]; earlyMode = "perlu"; }
  const seq = [...earlyVals, ...copy.map((v) => (v === 1 ? 1 : 0))];
  let raw = 0, fails = 0, ceiling = null;
  for (let i = 0; i < seq.length; i++) {
    if (seq[i]) { raw += 1; fails = 0; }
    else if (++fails === 3) { ceiling = i + 1; break; }   // nomor item (1–30) kegagalan ke-3
  }
  const passedAfter = ceiling == null ? 0 : seq.slice(ceiling).reduce((a, b) => a + b, 0);
  return { raw, ceiling, earlyMode, earlyVals, pending, passedAfter, simple: copy.filter((v) => v === 1).length };
}

/** Skor standar dari tabel norma. */
function vmiStandard(raw, months) {
  if (months == null) return { error: "usia" };
  const band = VMI_NORMS.find(([a, b]) => months >= a && months <= b);
  if (!band) return { error: months < VMI_NORMS[0][0] ? "muda" : "tua" };
  const col = band[2];
  const nums = col.map((v, r) => [r, v]).filter(([, v]) => v != null);
  const lo = nums[0], hi = nums[nums.length - 1];
  let ss, op = "";
  if (col[raw] != null) ss = col[raw];
  else if (raw > hi[0]) { ss = hi[1]; op = "≥"; }
  else { ss = lo[1]; op = "<"; }
  const yrs = Math.floor(months / 12);
  const sem = VMI_SEM[yrs] || 5;
  const eff = op === "<" ? ss - 1 : ss;
  return { ss, op, band: [band[0], band[1]], sem, cat: vmiCategory(eff), pct: op ? null : pctOf(ss) };
}

function pctOf(ss) {
  // CDF normal (Abramowitz–Stegun 7.1.26)
  const z = (ss - 100) / 15, t = 1 / (1 + 0.3275911 * Math.abs(z) / Math.SQRT2);
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-(z * z) / 2);
  const p = 0.5 * (1 + Math.sign(z) * y) * 100;
  return p < 1 ? "<1" : p > 99 ? ">99" : String(Math.round(p));
}

/** Usia perkembangan (perkiraan): kelompok usia anak (≤ 18 th) saat skor mentah ini = skor standar 100. */
function vmiAgeEquivalent(raw) {
  const kids = VMI_NORMS.filter(([a]) => a < 19 * 12);
  const val = (col) => (col[raw] != null ? col[raw] : raw > col.findLastIndex((v) => v != null) ? 156 : 44);
  if (val(kids[0][2]) < 100) return { text: `< ${fmtAge(kids[0][0])}`, below: true };
  let last = null;
  for (const band of kids) if (val(band[2]) >= 100) last = band;
  if (last === kids[kids.length - 1]) return { text: `> ${Math.floor(last[1] / 12)} th` };
  return { text: `${fmtAge(last[0])}–${fmtAge(last[1])}`, from: last[0] };
}

/** Ringkasan lengkap untuk satu tes. */
function vmiConclusion(test) {
  const r = vmiRawScore(test);
  const months = ageMonthsOf(test.child);
  const st = vmiStandard(r.raw, months);
  const ae = vmiAgeEquivalent(r.raw);
  let verdict = null;
  if (!st.error) {
    const s = st.op === "<" ? st.ss - 1 : st.ss;
    if (s >= 110) verdict = { tone: "ok", text: "Kemampuan visual-motor anak di atas rata-rata anak seusianya." };
    else if (s >= 90) verdict = { tone: "ok", text: "Kemampuan visual-motor anak sesuai usianya (rata-rata)." };
    else if (s >= 80) verdict = { tone: "warn", text: "Sedikit di bawah rata-rata anak seusianya — sebaiknya dipantau dan diberi latihan." };
    else verdict = { tone: "no", text: "Jauh di bawah rata-rata anak seusianya — disarankan pemeriksaan lanjutan oleh tenaga profesional." };
  }
  return { ...r, months, st, ae, verdict };
}
