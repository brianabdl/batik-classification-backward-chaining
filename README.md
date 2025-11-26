# Sistem Klasifikasi Batik - Expert System

Sistem pakar untuk mengklasifikasikan teknik pembuatan dan kualitas batik menggunakan metode **Backward Chaining**.

## Fitur

- **Klasifikasi Teknik Batik**: Batik Tulis, Batik Cap, Batik Print
- **Klasifikasi Kualitas**: Premium, Standard, Reject
- **Upload Gambar**: Support drag & drop dan preview dengan zoom
- **Quick Presets**: Template cepat untuk jenis batik umum
- **Riwayat Klasifikasi**: Menyimpan semua hasil klasifikasi
- **Manajemen Rules**: Tambah, edit, dan hapus aturan klasifikasi
- **Toggle Interface**: UI modern dengan toggle switches

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Cara Menjalankan

### 1. Clone atau Download Repository

```bash
cd ~/batik-classification-backward-chaining
```

### 2. Buat Virtual Environment (Opsional tapi Disarankan)

```bash
python -m venv venv
```

### 3. Aktifkan Virtual Environment

**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Jalankan Aplikasi

```bash
python app.py
```

### 6. Buka Browser

Aplikasi akan berjalan di: **http://localhost:5000** atau **http://0.0.0.0:5000**

## Dependencies

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.1
```

## Struktur Proyek

```
batik-classification-backward-chaining/
├── app.py                  # Main application file
├── requirements.txt        # Python dependencies
├── batik.db               # SQLite database (auto-generated)
├── static/
│   └── uploads/           # Uploaded images storage
└── templates/
    ├── base.html          # Base template dengan styling
    ├── index.html         # Halaman utama klasifikasi
    ├── history.html       # Halaman riwayat
    └── rules.html         # Halaman manajemen rules
```

## Cara Menggunakan

### Klasifikasi Batik

1. **Upload Gambar** (Opsional)
   - Klik area upload atau drag & drop gambar
   - Hover pada gambar untuk melihat detail dengan zoom
   - Format: PNG, JPG, JPEG, GIF

2. **Input Informasi**
   - Masukkan nama motif (opsional)
   - Gunakan Quick Presets atau toggle manual untuk karakteristik batik

3. **Karakteristik Pola & Teknik**
   - Pola berulang sangat teratur?
   - Goresan tidak simetris / bervariasi?
   - Malam (wax) terlihat jelas?
   - Pola seragam seperti cetakan mesin?

4. **Karakteristik Kualitas**
   - Warna tajam / cerah?
   - Warna pudar?
   - Kain terasa halus saat diraba?
   - Jumlah cacat motif

5. **Klasifikasi**
   - Klik tombol "Klasifikasi Sekarang"
   - Lihat hasil teknik dan kualitas beserta penjelasannya

### Quick Presets

- **Batik Tulis**: Otomatis mengisi karakteristik batik tulis
- **Batik Cap**: Otomatis mengisi karakteristik batik cap
- **Batik Print**: Otomatis mengisi karakteristik batik print
- **Reset**: Menghapus semua input

### Manajemen Rules

1. Akses halaman **Rules** dari menu
2. Lihat daftar rules untuk Technique dan Quality
3. Tambah rule baru dengan format JSON:
   - Tentukan tipe (technique/quality)
   - Set priority (angka kecil = prioritas tinggi)
   - Input conditions dalam format JSON
   - Masukkan conclusion dan explanation

**Contoh Conditions:**
```json
{
  "strokes_irregular": true,
  "wax_visible": true,
  "pattern_repeated": false
}
```

**Contoh Explanation:**
```json
["Goresan tidak simetris menunjukkan pembuatan manual", "Jejak lilin terlihat jelas"]
```

## Backward Chaining Logic

Sistem menggunakan backward chaining untuk:
1. Mengecek rules berdasarkan priority (ascending)
2. Matching conditions dengan facts yang diinput
3. Mengembalikan conclusion dari rule pertama yang match
4. Memberikan explanation untuk keputusan

## Database

- **SQLite** untuk penyimpanan data
- **Tables**:
  - `rule`: Menyimpan aturan klasifikasi
  - `batik_record`: Menyimpan hasil klasifikasi

Database akan dibuat otomatis saat aplikasi pertama kali dijalankan.

## Fitur UI

- **Modern Gradient Design**: Purple gradient theme
- **Toggle Switches**: Intuitive input controls
- **Image Zoom**: Hover untuk zoom detail gambar
- **Responsive Layout**: Mobile-friendly design
- **Smooth Animations**: Slide-in effects untuk hasil
- **Icon Integration**: Font Awesome icons

## Troubleshooting

### Port sudah digunakan
```bash
# Gunakan port berbeda
flask run --port 5001
```

### Database error
```bash
# Hapus database dan restart
rm batik.db
python app.py
```

### Module not found
```bash
# Install ulang dependencies
pip install -r requirements.txt
```

## Catatan

- Default rules sudah disediakan saat aplikasi pertama kali dijalankan
- Gambar yang diupload disimpan di folder `static/uploads/`
- Debug mode aktif secara default (ubah di `app.py` untuk production)

## Pengembangan

Untuk pengembangan lebih lanjut:
- Rules dapat ditambah/edit melalui halaman Rules
- Database dapat di-backup dengan copy file `batik.db`
- Styling dapat dimodifikasi di `templates/base.html`
