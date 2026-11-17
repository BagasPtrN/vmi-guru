# Penilaian VMI — Asisten Guru (versi web)

Versi web dari aplikasi tugas akhir **VMI Test Scoring** (Bagas Petra Natalegawa, 123210178).
Guru PAUD/TK bisa memotret gambar tes (24 simbol, Form 4–30) *Visual-Motor Integration* anak langsung dari HP,
mendapat penilaian otomatis, lalu **mengoreksi** (Benar/Salah) sebelum skor disimpan.

Penilaian otomatis memakai kode Python + OpenCV (`py/symbols/*.py`) yang dijalankan langsung di browser memakai
[Pyodide](https://pyodide.org), jadi tidak perlu server — cukup GitHub Pages (gratis).

## Fitur
- Isi data anak (nama, usia tahun/bulan, kelas, tanggal, pemeriksa)
- 24 kartu simbol (Form 4–30) dengan contoh bentuk — ambil foto dari **kamera** atau **galeri**
- **Rapikan foto**: potong bagian gambar & putar 90°
- Pilih banyak foto sekaligus (diurutkan sesuai nama file 1–24)
- Hasil per gambar + gambar deteksi (garis hijau/merah) yang bisa diperbesar
- Guru bisa **mengoreksi** tiap penilaian; skor akhir mengikuti keputusan guru
- Catatan guru, riwayat per anak, pencarian
- **Cetak / simpan PDF** laporan dan **unduh rekap** (.csv, bisa dibuka di Excel)
- Data tersimpan hanya di perangkat (IndexedDB) — tidak dikirim ke internet
- Bisa di-"Add to Home Screen" seperti aplikasi; setelah dibuka sekali, mesin penilai tersimpan di cache

## Cara pasang di GitHub Pages (± 5 menit)
1. Masuk ke <https://github.com> → klik **New repository**.
   Nama misalnya `vmi-guru`, pilih **Public**, klik **Create repository**.
2. Di halaman repo, klik **uploading an existing file**.
   Seret **seluruh isi** folder ini (bukan foldernya) — termasuk folder `py/` dan `sample/`,
   serta file `.nojekyll`. Klik **Commit changes**.
   > Catatan: file berawalan titik (`.nojekyll`) kadang tersembunyi di Windows Explorer.
   > Aplikasi tetap jalan walau file itu tidak ikut.
3. Buka **Settings → Pages**. Di *Build and deployment* pilih
   **Source: Deploy from a branch**, **Branch: `main`** dan folder **`/ (root)`** → **Save**.
4. Tunggu 1–2 menit. Link aplikasi muncul di atas halaman itu, bentuknya:
   `https://<username-github>.github.io/vmi-guru/`
5. Buka link itu di HP guru. Di Chrome Android: menu ⋮ → **Tambahkan ke layar utama**.

Pembukaan pertama mengunduh mesin penilai ±27 MB (Python + OpenCV, disimpan di folder `pyodide/` repo ini), sebaiknya pakai Wi-Fi.
Setelah itu tersimpan di cache browser.

## Kriteria penilaian (versi 2 — semua dicek sistem)
Checker ditulis ulang agar mengikuti **Scoring Criteria Manual Beery VMI** (Form 4–30, hlm. 8–31 +
*Summary Scoring* hlm. 32). Setiap kriteria diperiksa satu per satu (tidak berhenti di kriteria pertama
yang gagal) dan hasilnya (✓/✗ + alasan) ditampilkan di aplikasi. Tidak ada lagi kriteria yang harus
dicek manual oleh guru — guru tetap bisa mengoreksi hasil akhirnya.

Semua checker memakai toolkit bersama `py/symbols/_vmi_geom.py`:
biner (tahan bayangan foto HP) → potong ke area tinta → skala kerja seragam (320 px) →
skeleton Zhang–Suen → graf goresan → garis lurus, kaki, titik potong, lengkung, sudut poligon.

| No | Simbol | Kriteria yang diukur |
|---|---|---|
| 1–2 | Garis tegak / mendatar | > 50% goresan dalam ±30° |
| 3 | Lingkaran | ada lengkung dengan rasio ≤ 2 : 1 |
| 4 | Tanda tambah | 2 garis berpotongan · 4 kaki ≥ ¼″ · tiap garis ≤ 20° |
| 5, 7 | Garis miring | garis tunggal · ≥ 50% dalam 110–160° / 20–70° · tanpa belokan mendadak |
| 6 | Persegi | 4 sisi jelas |
| 8 | Silang miring | 2 garis berpotongan · sudut 20–70° & 110–160° · kaki ≤ 2× |
| 9 | Segitiga | 3 sisi jelas · satu sudut tertinggi |
| 10 | Persegi terbuka + lingkaran | celah/tumpang-tindih ≤ 1/16″ · tanpa distorsi · tinggi ≤ 2 : 1 · garis bagi masuk persegi |
| 11 | Silang tiga garis | 3 garis berpotongan · celah ≤ 1/8″ · mendatar ≤ 15° · diagonal > 10° dari vertikal |
| 12 | Panah empat arah | tidak terbalik/melayang · runcing · arah jelas · kaki ≤ 2× · kriteria Form 10 |
| 13 | Cincin dua dimensi (F19) | 7 bukaan + bukaan tengah · satu lingkaran di bawah (sisi bawah ≥ 20°) |
| 14 | Segitiga enam lingkaran (F20) | 6 lingkaran · dasar + 1 sisi lurus · dasar ≤ 10° · jarak ≤ 2 : 1 |
| 15 | Lingkaran + persegi miring (F21) | 4 sudut + lingkaran · sumbu ≤ 10° · sudut tertutup menyentuh · celah ≤ 1/16″ · di ⅓ tengah · tinggi ≤ 2 : 1 |
| 16 | Belah ketupat tegak (F22) | 4 sudut baik · sumbu 170–190° · tanpa telinga anjing · sisi ≥ ⅔ · sudut lancip ≤ 60° |
| 17 | Segitiga miring (F23) | 2 segitiga · sudut dalam menyentuh ⅓ tengah · sudut kiri 60–120° · sisi kanan ≥ 100° |
| 18 | Lingkaran delapan titik (F24) | 8 titik · tidak ada 3 segaris · jarak ≤ 2× |
| 19 | Segi enam Wertheimer (F25) | semua sisi · tanpa kebingungan di sudut · tumpang-tindih jelas, tidak berlebihan |
| 20 | Belah ketupat mendatar (F26) | 4 sudut baik · sudut lancip ≤ 60° · sumbu 170–190° · sisi ≥ ⅔ |
| 21 | Cincin tiga dimensi (F27) | 3 cincin garis ganda · saling bertumpuk · ≥ 1 tumpang-tindih 3-D |
| 22 | Kubus Necker (F28) | 12 rusuk · orientasi '/' · tanpa kebingungan |
| 23 | Kotak meruncing (F29) | luar jajaran genjang · dalam persegi panjang mendatar · bergeser kanan-bawah · tanpa distorsi |
| 24 | Bintang tiga dimensi (F30) | ujung melewati sisi lawan · atas & bawah pada segitiga yang sama · tanpa distorsi berat |

Ukuran dalam inci (¼″, 1/16″, 1/8″) diubah menjadi persentase ukuran gambar karena skala foto tidak
diketahui; ambang dan asumsinya tertulis sebagai konstanta di tiap file checker.

### Hasil uji pada dataset tugas akhir (176 gambar)
| | Valid dinilai benar | Invalid dinilai salah | Kriteria yang dicek sistem |
|---|---|---|---|
| Versi 1 (checker asli, `py/legacy/`) | 91/91 | 77/85 | sebagian (beberapa kriteria tidak dicek) |
| **Versi 2 (sekarang)** | **89/91** | **77/85** | **semua (31 kriteria)** |

Dua gambar valid yang kini dinilai salah (`Valid/e/1`, `Valid/g/2`) memang garisnya di luar rentang
sudut manual (±165° / ±15°, hanya 37% garis di dalam rentang). Uji ketahanan foto: hasil tetap sama
pada bayangan/kertas abu-abu, noise, resolusi 2×, dan tepi meja gelap; sedikit berubah bila gambar
diputar 4° (wajar untuk kriteria sudut — foto sebaiknya lurus).

### Simbol 13–24 (Form 19–30)
Dataset tugas akhir hanya berisi 12 simbol pertama, jadi checker Form 19–30 **belum diuji pada gambar anak sungguhan**.
Pengujian yang sudah dilakukan:
- **136 gambar sintetis "tulisan tangan"** (garis bergoyang, tebal & tinta acak, sedikit diputar), tiap form berisi
  contoh benar dan contoh yang sengaja melanggar satu kriteria: **134/136 sesuai** (yang meleset: 1 belah ketupat
  mendatar, 1 kubus Necker yang garisnya terlalu bergelombang).
- Contoh *Score / No Score* dari halaman manual (hasil potongan scan, kecil & sebagian terpotong): gambar
  *No Score* hampir semuanya ditolak, tetapi banyak gambar *Score 1* juga ditolak — checker Form 19–30 masih **ketat**,
  terutama Form 27–30 (cincin 3-D, kubus Necker, kotak meruncing, bintang 3-D) yang garisnya rumit.

Karena itu untuk simbol 13–24 hasil otomatis sebaiknya diperlakukan sebagai **saran awal** dan guru tetap memeriksa
alasan ✓/✗ per kriteria. Bila nanti ada foto gambar anak untuk Form 19–30, ambang di konstanta tiap checker bisa
disetel ulang dengan data itu.

## Kesimpulan akhir (skor standar menurut usia)
Mengikuti Manual Beery VMI (hlm. 23–29 & 93–96) dan tabel norma Lampiran C:
1. **Skor mentah 0–30**: item 1–6 (mencoret/meniru) + 24 gambar (item 7–30), dihitung berurutan sampai
   **3 kegagalan berturut-turut**. Item 1–6 otomatis diberi poin bila anak berhasil di salah satu item 7–9; bila tidak,
   guru mencentang hasil tugas mencoret/meniru di halaman hasil.
2. **Skor standar** (rata-rata 100, SD 15) dari tabel *Raw Scores to Standard Scores* per kelompok usia 2 bulan
   (`norms_data.js`, usia 4:0–69:11; ditranskripsi dengan OCR ganda + cek visual + cek monoton).
3. **Kategori** Tabel 1 manual (90–109 = rata-rata/sesuai usia), rentang ± SEM (Tabel 7),
   persentil (kurva normal, perkiraan) dan usia perkembangan (usia saat skor mentah = skor standar 100, perkiraan).

Tabel untuk usia **2:0–3:11 belum tersedia** — anak di bawah 4 tahun hanya mendapat skor mentah.

## Struktur file
```
index.html            halaman utama
app.css / app.js      tampilan & alur (Bahasa Indonesia, ramah HP)
norms_data.js         tabel norma Lampiran C (skor mentah → skor standar)
norms.js              skor mentah (aturan ceiling/basal), skor standar, kategori, kesimpulan
worker.js             memuat Pyodide + OpenCV, menjalankan checker di latar belakang
pyodide/              Pyodide 314.0.8 + wheel numpy & opencv-python (di-host sendiri, tanpa CDN)
py/runner.py          jembatan: memanggil <Simbol>Checker.check(path) → skor + gambar hasil
py/symbols/*.py       24 checker versi 2 (kriteria manual) + toolkit _vmi_geom.py, _cross.py, _oblique.py, _diamond.py
py/legacy/*.py        12 checker asli tugas akhir (versi 1, untuk perbandingan)
sample/valid|invalid  contoh gambar (1–12 dari dataset, 13–24 sintetis) untuk "Coba dengan contoh" (campuran / semua benar / semua salah)
sw.js, manifest       agar bisa offline & dipasang di layar utama
```

## Catatan teknis
- Pyodide 314.0.8 (dijalankan sebagai *module worker*) membawa `opencv-python 4.11.0.86` (sama dengan versi yang dipakai saat uji).
  Checker **tidak cocok dengan OpenCV 5** (bentuk keluaran `HoughLinesP` berubah), jadi versi Pyodide dikunci.
- Gambar dikecilkan ke maks. 1000 px sebelum dinilai (sama dengan `_MAX_DIMENSION` di checker).
- Checker versi 2 deterministik (tanpa unsur acak) dan memberi hasil yang sama di browser (Pyodide) dan di komputer.
- Checker tetap kompatibel dengan GUI desktop (`check(path) → (skor, gambar)`); hasil per kriteria ada di
  atribut kelas `last_criteria`.
- Skor yang ditampilkan adalah **skor mentah (raw score)** = jumlah simbol yang benar (maks. 24 untuk Form 4–30). Tes lama berisi 12 simbol tetap terbuka; slot 13–24-nya dianggap kosong.
