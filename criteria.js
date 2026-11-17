/* Kriteria penilaian 12 simbol pertama Beery VMI (Form 4–18),
 * diringkas dari Manual VMI hlm. 8–19 dan tabel "Summary Scoring" hlm. 32.
 *
 * Tiap kriteria:
 *   t    : teks Bahasa Indonesia
 *   en   : teks asli manual
 *   auto : true = diperiksa otomatis oleh checker Python (py/symbols) — sejak versi 2 semuanya
 * how  : ringkas cara program memeriksa (untuk halaman dokumentasi)
 * Hasil per kriteria dikirim checker lewat `last_criteria` (id, ok, detail).
 */
"use strict";
const MM = { q: "¼″ ≈ 6 mm", s: "1/16″ ≈ 1,6 mm", e: "1/8″ ≈ 3 mm" };

const CRITERIA = [
  { // 1
    form: "Form 4 & 7", age: "2:0 (meniru) · 2:10 (menyalin)",
    items: [
      { t: "Lebih dari ½ garis berada dalam 30° dari arah tegak (vertikal)", en: "Over 1/2 of line(s) within 30° of vertical", auto: true },
    ],
    how: "Skeleton goresan diukur arahnya per ruas pendek; lulus bila > 50% panjang goresan berada dalam ±30° dari vertikal.",
  },
  { // 2
    form: "Form 5 & 8", age: "2:6 (meniru) · 3:0 (menyalin)",
    items: [
      { t: "Lebih dari ½ garis berada dalam 30° dari arah mendatar (horizontal)", en: "Over 1/2 of line(s) within 30° of horizontal", auto: true },
    ],
    how: "Skeleton goresan diukur arahnya per ruas pendek; lulus bila > 50% panjang goresan berada dalam ±30° dari horizontal.",
  },
  { // 3
    form: "Form 6 & 9", age: "2:9 (meniru) · 3:0 (menyalin)",
    items: [
      { t: "Ada lengkung tertutup dengan perbandingan tinggi : lebar tidak lebih dari 2 : 1", en: "Any loop with a ratio of no more than 2 to 1 between its height and width", auto: true },
    ],
    how: "Mencari lengkung: lubang tertutup pada goresan, atau goresan yang berputar ≥ 300°. Rasio panjang : lebar lengkung (kotak terkecil yang memuatnya) harus ≤ 2 : 1.",
  },
  { // 4
    form: "Form 10", age: "4:1",
    items: [
      { t: "Dua garis saling berpotongan", en: "Two intersecting lines", auto: true },
      { t: `Keempat "kaki" minimal ${MM.q} (tidak termasuk perpanjangan)`, en: 'All 4 "legs" at least 1/4" long (not including extensions)', auto: true },
      { t: "Minimal ½ dari tiap garis berada dalam 20° dari sudut yang benar (tegak & mendatar)", en: "At least 1/2 of each line within 20° of correct angle", auto: true },
    ],
    how: "Goresan disusun menjadi garis-garis lurus: harus tepat 2 garis yang berpotongan (goresan lain ≤ 15%), keempat kaki ≥ 6% ukuran gambar, dan garis mendatar/tegak menyimpang ≤ 20° (+3° toleransi ukur).",
  },
  { // 5
    form: "Form 11", age: "4:4",
    items: [
      { t: 'Satu garis "tunggal" (perpanjangan boleh)', en: 'A "single" line (extensions OK)', auto: true },
      { t: "Minimal ½ garis berada pada sudut 110°–160°", en: "At least 1/2 of the line within 110°–160°", auto: true },
      { t: "Tidak ada perubahan arah yang mendadak", en: "No abrupt change of direction", auto: true },
    ],
    how: "Garis utama + perpanjangan segaris harus ≥ 80% seluruh goresan dan tanpa coretan melingkar; ≥ 50% garis dalam 110°–160°; tidak ada belokan > 30°.",
  },
  { // 6
    form: "Form 12", age: "4:6",
    items: [
      { t: "Empat sisi yang jelas (sudut tidak harus lancip)", en: "Four clearly defined sides (corners need not be angular)", auto: true },
    ],
    how: "Keliling tertutup (celah kecil di sudut disambung) disederhanakan menjadi sudut-sudut; harus tepat 4 sisi dan tiap sisi cukup lurus (sudut boleh membulat).",
  },
  { // 7
    form: "Form 13", age: "4:7",
    items: [
      { t: 'Satu garis "tunggal" (perpanjangan boleh)', en: 'A "single" line (extensions OK)', auto: true },
      { t: "Minimal ½ garis berada pada sudut 20°–70°", en: "At least 1/2 of the line within 20°–70°", auto: true },
      { t: "Tidak ada perubahan arah yang mendadak", en: "No abrupt change of direction", auto: true },
    ],
    how: "Garis utama + perpanjangan segaris harus ≥ 80% seluruh goresan dan tanpa coretan melingkar; ≥ 50% garis dalam 20°–70°; tidak ada belokan > 30°.",
  },
  { // 8
    form: "Form 14", age: "4:11",
    items: [
      { t: "Dua garis saling berpotongan", en: "Two intersecting lines", auto: true },
      { t: "Garis membentuk sudut antara 20°–70° dan 110°–160°", en: "Lines form angles between 20° and 70° and between 110° and 160°", auto: true },
      { t: "Kaki terpanjang tidak lebih dari 2× kaki terpendek (tanpa perpanjangan)", en: "Longest of 4 unextended legs no more than twice as long as shortest", auto: true },
    ],
    how: "Tepat 2 garis berpotongan; arah garis (hasil fitting) satu di 20°–70° dan satu di 110°–160°; kaki terpanjang ≤ 2× kaki terpendek.",
  },
  { // 9
    form: "Form 15", age: "5:3",
    items: [
      { t: "Tiga sisi yang jelas", en: "Three clearly defined sides", auto: true },
      { t: "Satu sudut lebih tinggi dari yang lain (tidak terbalik)", en: "One corner higher than others", auto: true },
    ],
    how: "Keliling disederhanakan menjadi 3 sudut yang benar-benar berbelok (≥ 75°) dengan sisi cukup lurus; sudut tertinggi minimal 15% tinggi bentuk di atas sudut lainnya.",
  },
  { // 10
    form: "Form 16", age: "5:6",
    items: [
      { t: `Celah atau tumpang-tindih antar-bentuk tidak lebih dari ${MM.s}`, en: 'No more than 1/16" separation or overlap of forms', auto: true },
      { t: "Lingkaran dan persegi terbuka tidak terdistorsi berat", en: "No major distortions of circle or open square", auto: true },
      { t: "Tinggi lingkaran dan persegi dalam perbandingan 2 : 1", en: "Height of circle and square within a 2 to 1 ratio", auto: true },
      { t: "Garis bagi lingkaran yang melewati sudut persegi harus masuk ke dalam persegi", en: "Bisector of circle passing through corner of square must project into the square", auto: true },
    ],
    how: "Lingkaran = lengkung tertutup; persegi = ruas goresan di luar lingkaran (2 sisi tegak + 1 sisi bawah, ±25°). Celah/tumpang-tindih di sudut ≤ 6% sisi persegi; tinggi 1 : 2 s.d. 2 : 1; garis dari pusat lingkaran melewati sudut harus masuk ke bagian dalam persegi.",
  },
  { // 11
    form: "Form 17", age: "5:9",
    items: [
      { t: "Tiga garis saling berpotongan", en: "Three intersecting lines", auto: true },
      { t: `Celah di titik potong tingginya tidak lebih dari ${MM.e}`, en: 'Intersection gap no more than 1/8" in height', auto: true },
      { t: "Lebih dari ½ garis mendatar berada dalam 15° dari horizontal", en: "Over 1/2 of horizontal line within 15° correct", auto: true },
      { t: "Lebih dari ½ kedua garis diagonal berjarak lebih dari 10° dari vertikal", en: "Over 1/2 of both diagonals more than 10° from vertical", auto: true },
    ],
    how: "Tepat 3 garis lurus yang saling berpotongan (tidak bengkok > 35°); selisih tinggi titik-titik potong ≤ 7,5% lebar gambar; garis mendatar ≤ 15° (+3°); > 50% tiap diagonal lebih dari 10° dari vertikal.",
  },
  { // 12
    form: "Form 18", age: "6:5",
    items: [
      { t: 'Ujung panah tidak terbalik atau "melayang" (terlepas)', en: 'Absence of reversed or "floating" tips', auto: true },
      { t: "Ujung panah runcing", en: "Sharp points on tips", auto: true },
      { t: "Tidak ada arah yang membingungkan", en: "No directional confusion", auto: true },
      { t: "Kaki terpanjang tidak lebih dari 2× kaki terpendek", en: "Longest of 4 legs no more than twice as long as shortest", auto: true },
      { t: "Juga memenuhi semua kriteria Form 10 (tanda tambah)", en: "Also apply all criteria for Form 10", auto: true },
    ],
    how: "Dua batang terpanjang diperiksa dengan kriteria Form 10. Di tiap ujung: sayap panah harus menyambung ke batang (tidak melayang), mengarah balik ke pusat (tidak terbalik), berangkat dari titik ujung dengan sudut (runcing, bukan membulat), kepala panah searah kakinya, tidak ada goresan lepas; kaki terpanjang ≤ 2× terpendek.",
  },
];

/** Hasil per kriteria untuk satu gambar (dari checker; fallback untuk hasil versi lama). */
function evaluateCriteria(i, it) {
  const C = CRITERIA[i];
  if (!C || it.empty || it.auto == null) return null;
  const got = Array.isArray(it.criteria) ? it.criteria : null;
  const rows = C.items.map((c, k) => {
    const r = got && got.find((g) => g.id === k + 1);
    return { ...c, n: k + 1, state: r ? (r.ok ? "ok" : "no") : (it.auto ? "ok" : "na"), detail: r ? r.detail : "" };
  });
  const failed = rows.find((r) => r.state === "no") || (!it.auto ? rows[0] : null);
  return { rows, failed, status: (it.notes || []).join(" | ") };
}
