## Fitur

- 📊 Laporan Harian, Mingguan, Bulanan
- 💰 Analisis Laba Kotor & Laba Bersih
- 🏢 Support Multi-Cabang
- 💳 Multi Metode Pembayaran
- 👤 Manajemen Capster
- 👑 Dashboard Owner

## Tech Stack

- Python 3.11+
- python-telegram-bot
- Google Sheets API
- pandas

## Instalasi dan Menjalankan Bot

```bash
# Buat virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
copy .env.example .env
# Edit .env dengan credentials Anda sesuai kebutuhan (lihat bagian Setup)

# Jalankan bot
# Untuk pengembangan lokal dengan validasi lingkungan:
python run.py

# Untuk deployment di platform seperti Render.com:
python main.py
```

## 🔐 Setup

Ikuti langkah-langkah berikut untuk menyiapkan bot Anda:

1.  **Bot Telegram**: Buat bot di [@BotFather](https://t.me/BotFather) dan dapatkan `TELEGRAM_BOT_TOKEN`.
2.  **Google Cloud**: Siapkan Proyek Google Cloud dan Akun Layanan, lalu unduh `credentials.json`.
3.  **Google Sheets**: Buat Google Sheets baru untuk data transaksi dan catat `GOOGLE_SHEET_ID` dari URL-nya.
4.  **Konfigurasi Lingkungan (`.env`)**:
    *   Salin `.env.example` ke `.env`.
    *   Isi variabel berikut di file `.env` Anda:
        *   `TELEGRAM_BOT_TOKEN`: Token bot Telegram Anda.
        *   `GOOGLE_SHEET_ID`: ID Google Sheet Anda (ini wajib dan tidak memiliki nilai *default*).
        *   `AUTHORIZED_CAPSTERS`: Daftar ID pengguna Telegram capster yang diizinkan (dipisahkan koma, cth: `12345,67890`).
        *   `OWNER_IDS`: Daftar ID pengguna Telegram owner (dipisahkan koma).
        *   `ADMIN_IDS`: Daftar ID pengguna Telegram admin (dipisahkan koma).
        *   `LOG_LEVEL`: Tingkat *logging* (cth: `INFO`, `DEBUG`).
        *   `CURRENCY`: Simbol mata uang (cth: `Rp`).
        *   `TIMEZONE`: Zona waktu (cth: `Asia/Jakarta`).
5.  **File Kredensial**: Pastikan `credentials.json` berada di direktori *root* proyek.

## ✨ Optimalisasi Performa Bot

Kami telah mengimplementasikan optimasi berikut untuk memastikan bot berjalan lebih cepat dan lebih efisien:

*   **Akses Google Sheets Cepat**: Sistem sekarang menggunakan *caching* untuk *worksheet* Google Sheets. Ini berarti bot tidak perlu meminta daftar *worksheet* berulang kali dari Google API, sehingga mempercepat operasi data.
*   **Bot Responsif**: Layanan utama bot seperti `SheetsService` dan `ReportService` sekarang diinisialisasi hanya sekali saat bot pertama kali dijalankan. Ini mencegah inisialisasi yang memakan waktu dan otorisasi API yang berulang, membuat bot lebih responsif terhadap perintah pengguna.
*   **Konfigurasi Aman**: Penanganan variabel lingkungan telah ditingkatkan untuk keamanan. Misalnya, `GOOGLE_SHEET_ID` sekarang harus selalu ditentukan, menghindari penggunaan *placeholder* yang tidak disengaja. Pesan kesalahan konfigurasi juga lebih informatif dan terintegrasi dengan sistem *logging*.

## 🚀 Peningkatan di Masa Depan

*   **Migrasi ke *Database* Khusus**: Untuk bot yang sangat aktif dengan banyak transaksi, memindahkan data dari Google Sheets ke *database* relasional khusus (seperti PostgreSQL atau SQLite) sangat direkomendasikan. Ini akan meningkatkan kecepatan pemrosesan transaksi, mendukung kueri data yang lebih kompleks, dan meningkatkan skalabilitas secara keseluruhan.

## 📄 License

Private Project - © 2026