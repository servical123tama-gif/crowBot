# 📚 Setup Guide

## Persiapan Awal

### 1. Telegram Bot

1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`
3. Ikuti instruksi untuk memberi nama bot
4. **Simpan TOKEN** yang diberikan

### 2. Google Cloud Setup

#### Buat Project
1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru
3. Enable API:
   - Google Sheets API
   - Google Drive API

#### Service Account
1. IAM & Admin → Service Accounts
2. Create Service Account
3. Beri nama (e.g., "barbershop-bot-sa")
4. Create Key → JSON
5. Download file JSON

### 3. Google Sheets

1. Buat Google Sheets baru
2. Copy Sheet ID dari URL
3. Share dengan service account email
   - Buka file `credentials.json`
   - Copy `client_email`
   - Share sheet dengan email tersebut (Editor access)

## Instalasi
```bash
# Clone repository
git clone <your-repo>
cd barbershop-bot

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
nano .env  # Edit dengan kredensial Anda

# Copy credentials.json ke root folder

# Setup sheets structure
python scripts/setup_sheets.py

# Run bot
python run.py
```

## Konfigurasi .env
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
GOOGLE_SHEET_ID=1AbCdEfG...
AUTHORIZED_CASTERS=123456789,987654321
DEBUG=False
LOG_LEVEL=INFO
```

## Mendapatkan User ID

1. Chat ke bot **@userinfobot**
2. Kirim pesan apa saja
3. Bot akan reply dengan User ID Anda
4. Tambahkan ke `AUTHORIZED_CASTERS`

## Testing
```bash
# Jalankan bot
python run.py

# Kirim /start ke bot
# Pastikan Anda bisa akses menu
```

## Troubleshooting

**Bot tidak merespon?**
- Cek TOKEN benar
- Pastikan bot running
- Cek User ID di AUTHORIZED_CASTERS

**Error Google Sheets?**
- Pastikan credentials.json ada
- Cek sheet sudah di-share
- Pastikan API sudah enabled

**Transaksi tidak tersimpan?**
- Cek struktur sheet
- Jalankan `python scripts/setup_sheets.py`