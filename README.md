# Penilaian VMI — Asisten Guru (versi web)

Versi web dari aplikasi tugas akhir **VMI Test Scoring** (Bagas Petra Natalegawa, 123210178).
Guru PAUD/TK bisa memotret 12 gambar tes *Visual-Motor Integration* anak langsung dari HP,
mendapat penilaian otomatis, lalu **mengoreksi** (Benar/Salah) sebelum skor disimpan.

**Penilaian otomatis memakai kode Python + OpenCV yang sama persis** dengan aplikasi desktop
(`py/symbols/*.py`, tidak diubah). Kode itu dijalankan langsung di browser memakai
[Pyodide](https://pyodide.org), jadi tidak perlu server — cukup GitHub Pages (gratis).

## Fitur
- Isi data anak (nama, usia tahun/bulan, kelas, tanggal, pemeriksa)
- 12 kartu simbol dengan contoh bentuk — ambil foto dari **kamera** atau **galeri**
- **Rapikan foto**: potong bagian gambar & putar 90°
- Pilih banyak foto sekaligus (diurutkan sesuai nama file 1–12)
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

## Struktur file
```
index.html            halaman utama
app.css / app.js      tampilan & alur (Bahasa Indonesia, ramah HP)
worker.js             memuat Pyodide + OpenCV, menjalankan checker di latar belakang
pyodide/              Pyodide 314.0.8 + wheel numpy & opencv-python (di-host sendiri, tanpa CDN)
py/runner.py          jembatan: memanggil <Simbol>Checker.check(path) → skor + gambar hasil
py/symbols/*.py       12 checker asli dari tugas akhir (tidak diubah)
sample/1..12.png      contoh gambar (dari dataset Valid) untuk tombol "Coba dengan contoh"
sw.js, manifest       agar bisa offline & dipasang di layar utama
```

## Catatan teknis
- Pyodide v314.0.8 membawa `opencv-python 4.11.0.86` (sama dengan versi yang dipakai saat uji).
  Checker **tidak cocok dengan OpenCV 5** (bentuk keluaran `HoughLinesP` berubah), jadi versi Pyodide dikunci.
- Gambar dikecilkan ke maks. 1000 px sebelum dinilai (sama dengan `_MAX_DIMENSION` di checker).
- Uji ulang dataset dengan OpenCV 4.11: `Valid` 91/91 dinilai benar; `Invalid` 83/91 dinilai salah
  (8 lolos: cross 2, oblique cross 1, open square circle 2, three line cross 3) — karena itu guru tetap memeriksa.
- Skor yang ditampilkan adalah **skor mentah (raw score) 0–12**, sama seperti aplikasi asli.
