# Barbershop Management Bot

Bot Telegram untuk manajemen operasional barbershop multi-cabang. Mencatat transaksi, menghasilkan laporan keuangan, dan mengelola konfigurasi bisnis langsung dari Telegram.

## Fitur

### Pencatatan Transaksi
- Catat transaksi layanan (potong rambut, coloring, dll) dengan detail lengkap
- Catat penjualan produk (pomade, powder, hair tonic, dll)
- Pilih cabang, layanan, dan metode pembayaran via menu interaktif
- Data tersimpan otomatis ke Google Sheets per bulan

### Laporan Keuangan
- **Laporan Harian** — ringkasan transaksi hari ini per cabang dan capster
- **Laporan Mingguan** — rekapitulasi minggu berjalan dengan breakdown per hari
- **Laporan Bulanan** — rekapitulasi bulanan dengan navigasi antar bulan
- **Laporan Profit** — laba rugi per cabang (pendapatan - biaya operasional - komisi)
- **Laporan Per Capster** — laporan harian/mingguan/bulanan per individu capster
- **Notifikasi Harian Otomatis** — ringkasan harian dikirim ke owner setiap jam 23:00 WIB

### RAG (Tanya Jawab AI)
- Perintah `/tanya` untuk bertanya tentang data bisnis dalam bahasa natural
- Didukung oleh Google Gemini AI (gemini-2.0-flash) dengan fallback keyword matching
- Contoh: `/tanya berapa pendapatan minggu ini?`, `/tanya siapa capster terbaik bulan januari?`
- Mendukung filter per tanggal, cabang, capster, dan rentang waktu

### Manajemen Capster (Owner)
- Tambah, edit, hapus capster via bot
- Data capster tersimpan di Google Sheets (sheet `CapsterList`)
- Merge otomatis dengan data `.env` saat startup
- Migrasi nama transaksi lama ke nama capster baru

### Pengaturan via Bot (Owner)
- **Kelola Layanan** — tambah, edit harga, hapus layanan (main & coloring)
- **Kelola Produk** — tambah, edit harga, hapus produk
- **Kelola Cabang** — edit biaya operasional dan komisi per cabang
- Semua konfigurasi tersimpan di Google Sheets dan di-load otomatis saat startup

### Manajemen Pelanggan
- Tambah dan lihat daftar pelanggan

### Multi-Cabang
- Capster memilih cabang kerja setiap hari
- Transaksi otomatis tercatat ke cabang yang dipilih
- Laporan profit per cabang dengan biaya operasional berbeda

### Sistem Role
| Role | Akses |
|------|-------|
| **Owner** | Semua fitur + pengaturan + laporan profit + kelola capster |
| **Admin** | Laporan umum + kelola pelanggan |
| **Capster** | Catat transaksi + laporan pribadi |

## Tech Stack

- **Python 3.11+**
- **python-telegram-bot 20.7** — framework bot Telegram
- **gspread + oauth2client** — Google Sheets API
- **pandas** — pemrosesan data dan laporan
- **google-generativeai** — Google Gemini AI untuk fitur RAG
- **Flask** — health check server untuk deployment
- **pytz** — timezone support

## Struktur Project

```
app/
├── config/
│   ├── constants.py          # Konstanta, callback data, pesan
│   └── settings.py           # Konfigurasi dari .env
├── handlers/
│   ├── start.py              # Handler /start
│   ├── transaction.py        # Catat transaksi layanan & produk
│   ├── branch.py             # Pilih/ganti cabang
│   ├── report.py             # Laporan harian/mingguan/bulanan/profit
│   ├── callback.py           # Router callback query
│   ├── capster.py            # CRUD capster
│   ├── config_handler.py     # CRUD layanan, produk, cabang
│   ├── customer.py           # Manajemen pelanggan
│   ├── query_handler.py      # Handler /tanya (RAG)
│   └── scheduler.py          # Notifikasi harian otomatis
├── models/
│   ├── transaction.py        # Model transaksi
│   ├── capster.py            # Model capster
│   ├── customer.py           # Model pelanggan
│   └── query.py              # Model query RAG
├── services/
│   ├── sheets_service.py     # CRUD Google Sheets
│   ├── report_service.py     # Generate laporan
│   ├── config_service.py     # Load/save konfigurasi
│   ├── capster_service.py    # Business logic capster
│   ├── auth_service.py       # Autentikasi & role
│   ├── branch_service.py     # Manajemen cabang harian
│   ├── gemini_service.py     # Google Gemini AI
│   └── query_parser_service.py  # Parser query natural language
├── utils/
│   ├── keyboards.py          # Inline keyboard builders
│   ├── formatters.py         # Format mata uang, tanggal
│   ├── decorators.py         # @require_auth, @require_owner, dll
│   ├── helpers.py            # Utility functions
│   └── week_calculator.py    # Kalkulasi minggu dalam bulan
├── bot.py                    # Inisialisasi & wiring aplikasi
└── web_server.py             # Health check untuk deployment
main.py                       # Entry point
requirements.txt
```

## Setup

### 1. Buat Bot Telegram
- Buka [@BotFather](https://t.me/BotFather) di Telegram
- Buat bot baru dan catat `TELEGRAM_BOT_TOKEN`

### 2. Setup Google Sheets API
- Buat project di [Google Cloud Console](https://console.cloud.google.com/)
- Aktifkan Google Sheets API dan Google Drive API
- Buat Service Account, download file credentials sebagai `credentials.json`
- Buat Google Spreadsheet baru, catat `GOOGLE_SHEET_ID` dari URL
- Share spreadsheet ke email service account (dengan akses Editor)

### 3. (Opsional) Setup Gemini AI
- Dapatkan API key gratis di [Google AI Studio](https://aistudio.google.com/apikey)
- Untuk fitur `/tanya` (natural language query)

### 4. Install Dependencies

```bash
# Buat virtual environment
python -m venv venv

# Aktivasi (Windows)
venv\Scripts\activate

# Aktivasi (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Konfigurasi Environment

```bash
copy .env.example .env    # Windows
cp .env.example .env      # Linux/Mac
```

Edit file `.env`:

```env
# Wajib
TELEGRAM_BOT_TOKEN=your_bot_token
GOOGLE_SHEET_ID=your_sheet_id
AUTHORIZED_CAPSTERS=123456,789012       # Telegram User ID capster (koma-separated)
OWNER_IDS=123456                        # Telegram User ID owner
ADMIN_IDS=789012                        # Telegram User ID admin

# Opsional
GEMINI_API_KEY=your_gemini_api_key      # Untuk fitur /tanya AI
BOT_NAME=BarbershopBot
BOT_USERNAME=your_bot_username
DEBUG=False
LOG_LEVEL=INFO
CURRENCY=Rp
TIMEZONE=Asia/Jakarta
```

### 6. Letakkan credentials.json
Pastikan file `credentials.json` berada di root project.

### 7. Jalankan Bot

```bash
# Development (dengan validasi environment)
python main.py --dev

# Production
python main.py
```

## Google Sheets

Bot otomatis membuat worksheet yang dibutuhkan saat pertama kali dijalankan:

| Sheet | Fungsi |
|-------|--------|
| `Januari 2026`, `Februari 2026`, ... | Data transaksi per bulan |
| `CapsterList` | Daftar capster (Name, TelegramID, Alias) |
| `ServiceList` | Daftar layanan & harga (ServiceID, Name, Category, Price) |
| `BranchConfig` | Konfigurasi cabang & biaya operasional |
| `ProductList` | Daftar produk & harga |
| `Customers` | Data pelanggan |

## Deployment

Bot mendukung deployment ke platform seperti Render.com:
- Mode production otomatis menjalankan health check server (Flask)
- Jalankan dengan `python main.py` (tanpa `--dev`)

## License

Private Project
