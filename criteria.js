/* Kriteria penilaian 12 simbol pertama Beery VMI (Form 4–18),
 * diringkas dari Manual VMI hlm. 8–19 dan tabel "Summary Scoring" hlm. 32.
 *
 * Tiap kriteria:
 *   t    : teks Bahasa Indonesia
 *   en   : teks asli manual
 *   auto : true  = diperiksa otomatis oleh checker Python (py/symbols)
 *          false = belum dicek program → diperiksa guru
 * fail : pola pesan status checker → indeks kriteria yang gagal
 * extra: aturan tambahan program yang tidak ada di manual (ditampilkan apa adanya)
 * how  : ringkas cara program memeriksa (untuk halaman dokumentasi)
 */
"use strict";
const MM = { q: "¼″ ≈ 6 mm", s: "1/16″ ≈ 1,6 mm", e: "1/8″ ≈ 3 mm" };

const CRITERIA = [
  { // 1
    form: "Form 4 & 7", age: "2:0 (meniru) · 2:10 (menyalin)",
    items: [
      { t: "Lebih dari ½ garis berada dalam 30° dari arah tegak (vertikal)", en: "Over 1/2 of line(s) within 30° of vertical", auto: true },
    ],
    fail: [[/./, 0]],
    how: "Mencari garis dominan pada kontur, lalu mengukur sudutnya terhadap sumbu vertikal (batas 30°).",
  },
  { // 2
    form: "Form 5 & 8", age: "2:6 (meniru) · 3:0 (menyalin)",
    items: [
      { t: "Lebih dari ½ garis berada dalam 30° dari arah mendatar (horizontal)", en: "Over 1/2 of line(s) within 30° of horizontal", auto: true },
    ],
    fail: [[/./, 0]],
    how: "Mencari garis dominan pada kontur, lalu mengukur sudutnya terhadap sumbu horizontal (batas 30°).",
  },
  { // 3
    form: "Form 6 & 9", age: "2:9 (meniru) · 3:0 (menyalin)",
    items: [
      { t: "Ada lengkung tertutup dengan perbandingan tinggi : lebar tidak lebih dari 2 : 1", en: "Any loop with a ratio of no more than 2 to 1 between its height and width", auto: true },
    ],
    fail: [[/./, 0]],
    how: "Memeriksa kontur tertutup: rasio sisi (batas program 2,5 : 1), kebulatan, cakupan sudut, dan luas minimum.",
  },
  { // 4
    form: "Form 10", age: "4:1",
    items: [
      { t: "Dua garis saling berpotongan", en: "Two intersecting lines", auto: true },
      { t: `Keempat "kaki" minimal ${MM.q} (tidak termasuk perpanjangan)`, en: 'All 4 "legs" at least 1/4" long (not including extensions)', auto: true },
      { t: "Minimal ½ dari tiap garis berada dalam 20° dari sudut yang benar (tegak & mendatar)", en: "At least 1/2 of each line within 20° of correct angle", auto: true },
    ],
    fail: [[/Endpoint too close/i, 1], [/angles out of range|same orientation/i, 2], [/./, 0]],
    how: "Mendeteksi 2 garis (Hough), mengecek perpotongan, jarak ujung kaki dari titik potong, dan sudut 0–20°/160–180° serta 70–110°.",
  },
  { // 5
    form: "Form 11", age: "4:4",
    items: [
      { t: 'Satu garis "tunggal" (perpanjangan boleh)', en: 'A "single" line (extensions OK)', auto: true },
      { t: "Minimal ½ garis berada pada sudut 110°–160°", en: "At least 1/2 of the line within 110°–160°", auto: true },
      { t: "Tidak ada perubahan arah yang mendadak", en: "No abrupt change of direction", auto: true },
    ],
    fail: [[/Abrupt/i, 2], [/Angle out of range/i, 1], [/./, 0]],
    how: "Mengambil garis dominan, mengukur sudutnya (110°–160°), dan mengecek belokan tajam antar-segmen (> 30°).",
  },
  { // 6
    form: "Form 12", age: "4:6",
    items: [
      { t: "Empat sisi yang jelas (sudut tidak harus lancip)", en: "Four clearly defined sides (corners need not be angular)", auto: true },
    ],
    fail: [[/./, 0]],
    how: "Menyederhanakan kontur (convex hull + approxPolyDP) dan mengecek apakah tepat 4 titik sudut.",
  },
  { // 7
    form: "Form 13", age: "4:7",
    items: [
      { t: 'Satu garis "tunggal" (perpanjangan boleh)', en: 'A "single" line (extensions OK)', auto: true },
      { t: "Minimal ½ garis berada pada sudut 20°–70°", en: "At least 1/2 of the line within 20°–70°", auto: true },
      { t: "Tidak ada perubahan arah yang mendadak", en: "No abrupt change of direction", auto: true },
    ],
    fail: [[/Abrupt/i, 2], [/Angle out of range/i, 1], [/./, 0]],
    how: "Mengambil garis dominan, mengukur sudutnya (20°–70°), dan mengecek belokan tajam antar-segmen (> 30°).",
  },
  { // 8
    form: "Form 14", age: "4:11",
    items: [
      { t: "Dua garis saling berpotongan", en: "Two intersecting lines", auto: true },
      { t: "Garis membentuk sudut antara 20°–70° dan 110°–160°", en: "Lines form angles between 20° and 70° and between 110° and 160°", auto: true },
      { t: "Kaki terpanjang tidak lebih dari 2× kaki terpendek (tanpa perpanjangan)", en: "Longest of 4 unextended legs no more than twice as long as shortest", auto: true },
    ],
    fail: [[/Asymmetric/i, 2], [/angles out of range|same oblique group/i, 1], [/./, 0]],
    how: "Mendeteksi 2 garis miring (Hough), mengecek perpotongan, kelompok sudut 20–70° & 110–160°, dan rasio kaki ≤ 2 : 1.",
  },
  { // 9
    form: "Form 15", age: "5:3",
    items: [
      { t: "Tiga sisi yang jelas", en: "Three clearly defined sides", auto: true },
      { t: "Satu sudut lebih tinggi dari yang lain (tidak terbalik)", en: "One corner higher than others", auto: true },
    ],
    extra: { t: "Aturan tambahan program: tidak ada sudut tumpul (> 110°)", match: /Obtuse/i },
    fail: [[/Inverted/i, 1], [/Obtuse/i, "extra"], [/./, 0]],
    how: "Menyederhanakan kontur menjadi 3 titik sudut, mengecek jumlah sudut ±180°, tidak terbalik, dan tidak bersudut tumpul.",
  },
  { // 10
    form: "Form 16", age: "5:6",
    items: [
      { t: `Celah atau tumpang-tindih antar-bentuk tidak lebih dari ${MM.s}`, en: 'No more than 1/16" separation or overlap of forms', auto: false },
      { t: "Lingkaran dan persegi terbuka tidak terdistorsi berat", en: "No major distortions of circle or open square", auto: true },
      { t: "Tinggi lingkaran dan persegi dalam perbandingan 2 : 1", en: "Height of circle and square within a 2 to 1 ratio", auto: true },
      { t: "Garis bagi lingkaran yang melewati sudut persegi harus masuk ke dalam persegi", en: "Bisector of circle passing through corner of square must project into the square", auto: true },
    ],
    fail: [[/too small/i, 2], [/does not intersect/i, 3], [/./, 1]],
    how: "Mendeteksi tepat 1 lingkaran dan 1 persegi terbuka, rasio diameter : sisi ≥ 0,5, lalu menarik garis dari pusat lingkaran lewat sudut persegi.",
  },
  { // 11
    form: "Form 17", age: "5:9",
    items: [
      { t: "Tiga garis saling berpotongan", en: "Three intersecting lines", auto: true },
      { t: `Celah di titik potong tingginya tidak lebih dari ${MM.e}`, en: 'Intersection gap no more than 1/8" in height', auto: true },
      { t: "Lebih dari ½ garis mendatar berada dalam 15° dari horizontal", en: "Over 1/2 of horizontal line within 15° correct", auto: true },
      { t: "Lebih dari ½ kedua garis diagonal berjarak lebih dari 10° dari vertikal", en: "Over 1/2 of both diagonals more than 10° from vertical", auto: true },
    ],
    fail: [[/Gap/i, 1], [/horizontal/i, 2], [/diagonal|vertical/i, 3], [/./, 0]],
    how: "RANSAC mencari 3 garis (diulang 10×, lulus bila ≥ 50%), mengecek garis mendatar ≤ 15°, diagonal > 10° dari vertikal, dan celah di pusat.",
  },
  { // 12
    form: "Form 18", age: "6:5",
    items: [
      { t: 'Ujung panah tidak terbalik atau "melayang" (terlepas)', en: 'Absence of reversed or "floating" tips', auto: true },
      { t: "Ujung panah runcing", en: "Sharp points on tips", auto: false },
      { t: "Tidak ada arah yang membingungkan", en: "No directional confusion", auto: false },
      { t: "Kaki terpanjang tidak lebih dari 2× kaki terpendek", en: "Longest of 4 legs no more than twice as long as shortest", auto: false },
      { t: "Juga memenuhi semua kriteria Form 10 (tanda tambah)", en: "Also apply all criteria for Form 10", auto: true },
    ],
    fail: [[/Gap/i, 0], [/./, 4]],
    how: "Mendeteksi silang tegak–mendatar seperti Form 10, lalu mengecek ada-tidaknya celah antara ujung panah dan batangnya.",
  },
];

/** Bandingkan hasil checker dengan kriteria manual. */
function evaluateCriteria(i, it) {
  const C = CRITERIA[i];
  if (!C || it.empty || it.auto == null) return null;
  const status = (it.notes || []).join(" | ");
  const rows = C.items.map((c, k) => ({ ...c, n: k + 1, state: c.auto ? (it.auto ? "ok" : "na") : "guru" }));
  let failed = null;
  if (!it.auto) {
    let idx = 0;
    for (const [re, k] of C.fail) if (re.test(status)) { idx = k; break; }
    if (idx === "extra" && C.extra) {
      rows.push({ t: C.extra.t, n: "+", auto: true, state: "no" });
      failed = rows[rows.length - 1];
    } else {
      rows[idx].state = "no";
      failed = rows[idx];
    }
    if (it.error || /No contours|No significant|No edges/i.test(status)) failed.why = "gambar tidak terbaca jelas";
  }
  return { rows, failed, status };
}
