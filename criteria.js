/* Kriteria penilaian 24 simbol Beery VMI (Form 4–30),
 * diringkas dari Manual VMI hlm. 8–31 dan tabel "Summary Scoring" hlm. 32.
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
  },  { // 13
    form: "Form 19", age: "6:8",
    items: [
      { t: "Tiga lingkaran bertumpuk membentuk 7 bukaan; bukaan segitiga di tengah terlihat", en: "Three overlapping circles forming seven openings; central triangular opening must be visible", auto: true },
      { t: "Satu lingkaran jelas di bawah dua lainnya (sisi terbawah segitiga pusat-pusat lingkaran miring ≥ 20°)", en: "One circle clearly below the others (lowest side of triangle joining circle centers at least 20° from horizontal)", auto: true },
    ],
    how: "Menghitung bukaan (ruang tertutup) — harus 7 dan bukaan tengah menyentuh ≥ 3 bukaan lain; bila garis tak rapat, dicocokkan 3 lingkaran (RANSAC) dan wilayah irisannya dihitung. Titik pusat ketiga lingkaran dihubungkan; sisi segitiga terbawah harus miring ≥ 20°.",
  },
  { // 14
    form: "Form 20", age: "7:5",
    items: [
      { t: "Enam lingkaran", en: "Six circles", auto: true },
      { t: "Garis dasar dan minimal satu sisi lain lurus (garis antara dua lingkaran ujung menyentuh lingkaran tengahnya)", en: "Base and at least one other side straight (line between end circles touches the middle circle)", auto: true },
      { t: "Garis dasar dalam 10° dari horizontal", en: "Base within 10° of horizontal", auto: true },
      { t: "Jarak antar-lingkaran pada satu sisi tidak lebih dari 2 : 1", en: "Spacing of circles on a side no more than 2:1", auto: true },
    ],
    how: "Setiap komponen bulat (berlubang atau terisi) dihitung sebagai lingkaran. Tiga lingkaran terluar = sudut segitiga; lingkaran tengah dipasangkan ke sisinya. Sisi 'lurus' bila jarak lingkaran tengah ke garis ≤ jari-jarinya; kemiringan dasar ≤ 10°; perbandingan jarak pusat ke pusat ≤ 2.",
  },
  { // 15
    form: "Form 21", age: "7:11",
    items: [
      { t: "Persegi bersudut empat dan sebuah lingkaran", en: "Four-cornered square and a circle", auto: true },
      { t: "Sudut-sudut berhadapan dalam 10° dari vertikal dan horizontal", en: "Opposite corners within 10° of vertical and horizontal", auto: true },
      { t: "Persegi menyentuh lingkaran dengan sudut yang tertutup", en: "Square touches circle with closed corner", auto: true },
      { t: `Celah atau tumpang-tindih tidak lebih dari ${MM.s}`, en: "Gap or overlap no more than 1/16″", auto: true },
      { t: "Titik sentuh berada di 1/3 tengah lingkaran", en: "Touching point in middle third of circle", auto: true },
      { t: "Tinggi lingkaran dan persegi tidak lebih dari 2 : 1", en: "Heights of circle and square no more than 2:1", auto: true },
    ],
    how: "Lingkaran = bukaan paling bulat; persegi = bukaan 4 sudut. Sumbu diagonal persegi dibandingkan dengan tegak/mendatar (≤ 10°). Sudut persegi yang paling dekat lingkaran harus tertutup, berjarak ≤ 8% tinggi persegi dari tepi lingkaran, dan jatuh di sepertiga tengah tinggi lingkaran; perbandingan tinggi ≤ 2.",
  },
  { // 16
    form: "Form 22", age: "8:1",
    items: [
      { t: `Empat sudut yang baik (bukaan < ${MM.s})`, en: "Four good corners (openings under 1/16″)", auto: true },
      { t: "Sumbu mendatar dalam 170°–190°", en: "Horizontal axis within 170° to 190°", auto: true },
      { t: 'Tidak ada "telinga anjing" (garis/sudut tambahan di pojok)', en: 'No "dog ears"', auto: true },
      { t: "Sisi terpendek minimal 2/3 sisi terpanjang", en: "Shortest side at least 2/3 of longest side", auto: true },
      { t: "Kedua sudut lancip 60° atau kurang", en: "Both acute angles 60° or less", auto: true },
    ],
    how: "Bentuk tertutup diringkas jadi poligon 4 sudut (celah ujung garis ≤ 5% ukuran). Sumbu mendatar = garis antara dua sudut samping (≤ 10° dari horizontal); sudut kecil tambahan di pojok = telinga anjing; sisi terpendek/terpanjang ≥ 2/3; sudut atas & bawah ≤ 60° (+2° toleransi).",
  },
  { // 17
    form: "Form 23", age: "8:11",
    items: [
      { t: "Dua segitiga", en: "Two triangles", auto: true },
      { t: `Dua sudut segitiga dalam menyentuh rapi 1/3 tengah sisi luar; sudut ketiga dalam ${MM.s} dari menyentuh`, en: "Two inner corners touch middle thirds of outer sides; third within 1/16″", auto: true },
      { t: "Sudut kiri segitiga luar 60°–120°", en: "Left angle of outer triangle 60°–120°", auto: true },
      { t: "Sisi kanan segitiga luar miring 100° atau lebih", en: "Right side of outer triangle 100° or more", auto: true },
    ],
    how: "Kontur luar diringkas jadi segitiga; segitiga dalam diambil dari bukaan yang terbentuk. Tiap sudut segitiga dalam diukur jaraknya ke sisi luar (≤ 3,5% = menyentuh, ≤ 6% = hampir) dan posisinya harus di sepertiga tengah sisi; sudut kiri & kemiringan sisi kanan diukur dari titik sudut.",
  },
  { // 18
    form: "Form 24", age: "9:6",
    items: [
      { t: "Delapan titik, lingkaran kecil, atau garis pendek", en: "Eight dots, circles or dashes", auto: true },
      { t: "Bulat: tidak ada tiga titik berurutan yang segaris", en: "Roundness: no three consecutive dots in a straight line", auto: true },
      { t: "Jarak terbesar antar-titik bersebelahan ≤ 2× jarak terkecil", en: "Largest gap no more than twice the smallest", auto: true },
    ],
    how: "Menghitung komponen terpisah (titik/coretan kecil) — harus 8. Diurutkan melingkar dari pusatnya; tiga titik berurutan dianggap segaris bila titik tengah menyimpang < 5% panjang talinya; perbandingan jarak bersebelahan ≤ 2.",
  },
  { // 19
    form: "Form 25", age: "10:2",
    items: [
      { t: "Semua sisi tergambar (satu sudut paling tumpul boleh membulat)", en: "All sides present (one most obtuse angle may be rounded)", auto: true },
      { t: "Tidak ada tanda kebingungan arah di sudut", en: "No directional confusion at corners", auto: true },
      { t: "Tumpang-tindih terlihat jelas, tetapi tidak berlebihan", en: "Overlap clearly evident but not excessive", auto: true },
    ],
    how: "Bukaan tumpang-tindih = bukaan yang bersebelahan dengan dua bukaan besar; tiap segi enam = bukaan besar ∪ tumpang-tindih, diringkas jadi poligon (5–6 sudut). Ujung garis yang kebablasan > 7% ukuran = kebingungan arah. Luas tumpang-tindih 4%–60% dari segi enam terkecil.",
  },
  { // 20
    form: "Form 26", age: "10:11",
    items: [
      { t: `Empat sudut yang baik (bukaan < ${MM.s})`, en: "Four good corners (openings under 1/16″)", auto: true },
      { t: "Kedua sudut lancip 60° atau kurang", en: "Both acute angles 60° or less", auto: true },
      { t: "Sumbu mendatar dalam 170°–190°", en: "Horizontal axis within 170° to 190°", auto: true },
      { t: "Sisi terpendek minimal 2/3 sisi terpanjang", en: "Shortest side at least 2/3 of longest side", auto: true },
    ],
    how: "Sama seperti Form 22 tanpa pemeriksaan telinga anjing: poligon 4 sudut, sudut kiri & kanan ≤ 60° (+2°), sumbu mendatar ≤ 10° dari horizontal, sisi terpendek ≥ 2/3 terpanjang. (Usia norma diambil dari tabel tren manual.)",
  },
  { // 21
    form: "Form 27", age: "11:2",
    items: [
      { t: "Tiga lingkaran bergaris ganda yang lengkap", en: "Three complete double-lined circles", auto: true },
      { t: "Semua lingkaran saling bertumpuk", en: "All circles overlapping", auto: true },
      { t: "Minimal satu tumpang-tindih 3-D yang bersih", en: "At least one clean 3-D overlap", auto: true },
    ],
    how: "Celah sempit di antara garis ganda (pita) dikumpulkan lalu dicocokkan 3 lingkaran (RANSAC) pada garis tengah pita; lengkap bila pita menutupi ≥ 60% keliling. Tiap pasang lingkaran harus berpotongan. Di titik silang, cincin yang pitanya tetap menyambung berarti lewat di atas — minimal satu persilangan begitu.",
  },
  { // 22
    form: "Form 28", age: "12:8",
    items: [
      { t: "Jumlah bagian benar (12 rusuk)", en: "Correct number of parts", auto: true },
      { t: "Orientasi benar (rusuk penghubung miring ke kanan-atas)", en: "Correct orientation", auto: true },
      { t: "Tidak ada tanda kebingungan", en: "No confusion", auto: true },
    ],
    how: "Kerangka garis dipecah menjadi ruas lurus di setiap sudut tajam: harus 12 ruas — 4 mendatar, 4 tegak, 4 miring. Rusuk miring harus '/' (105°–165°). Coretan pendek, ujung rusuk menggantung, atau rusuk miring yang tidak menyambung ke sudut = kebingungan.",
  },
  { // 23
    form: "Form 29", age: "13:2",
    items: [
      { t: "Bentuk luar jajaran genjang (boleh persegi)", en: "Outer form a parallelogram (square OK)", auto: true },
      { t: "Bentuk dalam persegi panjang mendatar", en: "Inner form a horizontal rectangle", auto: true },
      { t: "Bentuk dalam jelas bergeser ke kanan-bawah (diagonal kanan-bawah paling pendek)", en: "Inner form clearly shifted right and down", auto: true },
      { t: "Tidak ada kebingungan atau distorsi", en: "No confusion or distortion", auto: true },
    ],
    how: "Kontur luar diringkas jadi 4 sudut; sisi berhadapan sejajar ≤ 12°. Bentuk dalam = bukaan yang tidak menyentuh tepi luar, harus 4 sudut, mendatar (lebar ≥ 1,15× tinggi). Diagonal dari sudut kanan-bawah paling pendek dan pusat dalam bergeser ≥ 3%. Harus ada 5 bukaan (4 trapesium + persegi) tanpa garis kebablasan.",
  },
  { // 24
    form: "Form 30", age: "13:8",
    items: [
      { t: "Semua sudut segitiga melewati sisi segitiga lawan", en: "All corners of triangles extend beyond opposing sides", auto: true },
      { t: "Satu segitiga yang sama ada bagian di atas dan di bawah segitiga lain", en: "One over- and one underlapping of the same triangle", auto: true },
      { t: "Tidak ada distorsi berat", en: "No extreme distortion", auto: true },
    ],
    how: "Kontur luar harus punya 6 ujung lancip yang melewati sisi segitiga lawan. Garis tengah pita (garis ganda) dicocokkan menjadi 6 garis lalu dibagi ke dua segitiga. Di tiap persilangan, sisi yang pitanya menyambung = lewat di atas; satu segitiga harus punya keduanya. Sudut tiap segitiga 30°–90° dan perbandingan luas ≤ 2,2.",
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
