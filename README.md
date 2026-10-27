# SIPKEL

SIPKEL adalah aplikasi peminjaman kelas untuk mahasiswa yang dibuat dengan Flask dan SQLite.

## Fitur utama
- Login dan registrasi mahasiswa
- Pengajuan peminjaman kelas
- Validasi jadwal agar ruangan tidak bentrok
- Status peminjaman: pending, approved, rejected
- Dashboard admin untuk menyetujui atau menolak permohonan
- Riwayat peminjaman mahasiswa

## Cara menjalankan
1. Buat virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   # .venv\Scripts\activate    # Windows
   ```
2. Install dependency
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi
   ```bash
   python app.py
   ```
4. Buka browser ke
   ```bash
   http://localhost:5000
   ```

## Akun default
- Admin:
  - NIM: `admin`
  - Password: `admin123`

## Struktur aplikasi
- `app.py`: logika aplikasi
- `templates/`: HTML halaman
- `static/style.css`: style tampilan
- `sipkel.db`: database SQLite otomatis dibuat saat pertama kali dijalankan

## Catatan
Aplikasi ini dibuat untuk kebutuhan demo dan pengembangan awal sistem peminjaman kelas.

