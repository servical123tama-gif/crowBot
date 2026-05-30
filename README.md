# Barbershop Management

Sistem manajemen barbershop multi-cabang. Terdiri dari dua channel:

- **Web dashboard** — admin (laporan, kelola data) dan capster (self-service portal)
- **Bot Telegram** — laporan ringkasan untuk owner/admin (read-only)

## Tech Stack

- **Python 3.11+**
- **Flask 2.3** — web framework
- **SQLAlchemy 2.0** — ORM
- **Alembic** — database migrations
- **PostgreSQL** (production) / **SQLite** (dev) — pilih lewat `DATABASE_URL`
- **python-telegram-bot 21.7** — bot
- **pandas** — kalkulasi laporan
- **gunicorn** — WSGI server (production)

## Struktur Folder

```
bot_barber_2/
├── app/                       # SHARED CORE — dipakai web & bot
│   ├── config/                # constants, settings env
│   ├── db/                    # SQLAlchemy models, repository, engine
│   └── services/              # business logic (profit calc, dll.)
│
├── web/                       # Flask web dashboard
│   ├── __init__.py            # create_app()
│   ├── auth.py                # @login_required admin
│   ├── routes/                # 15 blueprints (home, profit, transactions, dll.)
│   ├── static/                # CSS, JS, QR member
│   └── templates/             # Jinja2 templates
│
├── bot/                       # Telegram bot (admin reports only)
│   ├── __init__.py            # re-export run, build_app
│   ├── bot.py                 # Application wiring
│   ├── auth.py                # @admin_only decorator
│   ├── formatters.py          # fmt_idr, fmt_date
│   ├── reports.py             # text builder laporan
│   ├── handlers.py            # command + callback handlers
│   └── scheduler.py           # auto-push 23:00 WIB
│
├── alembic/                   # DB migrations
├── scripts/                   # one-off scripts & arsip migrasi
├── docs/                      # API.md, SETUP.md, DEPLOYMENT.md
├── backups/                   # DB dumps (gitignored)
│
├── run_dashboard.py           # entry point web
├── run_bot.py                 # entry point bot
├── wsgi.py / application.py   # Azure App Service entry
├── startup.sh                 # Azure startup script
├── alembic.ini
├── requirements.txt
└── .env.example
```

### Aturan import

- `web/` boleh impor dari `app/`
- `bot/` boleh impor dari `app/`
- `app/` **TIDAK** boleh impor dari `web/` atau `bot/`
- `web/` dan `bot/` **TIDAK** saling impor

Business logic ditaruh di `app/services/`. Route web dan handler bot
ideally cuma tipis — terima input, panggil service, format output.

## Setup

### 1. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate           # Windows
# atau: source venv/bin/activate # Linux/macOS

pip install -r requirements.txt
```

### 2. Konfigurasi `.env`

```bash
cp .env.example .env
```

Edit `.env`. Variabel penting:

| Variabel | Wajib | Keterangan |
|----------|-------|------------|
| `DATABASE_URL` | ✅ | `sqlite:///./barbershop.db` (dev) atau `postgresql://...` (prod) |
| `DASHBOARD_PASSWORD` | ✅ | Password admin dashboard |
| `DASHBOARD_SECRET_KEY` | ✅ | Random string untuk session Flask |
| `TELEGRAM_BOT_TOKEN` | ⚠️ | Wajib kalau pakai bot. Dapat dari [@BotFather](https://t.me/BotFather) |
| `OWNER_IDS` | ⚠️ | Telegram user IDs owner (koma-separated). Bot auth & notifikasi 23:00 |
| `ADMIN_IDS` | ⚠️ | Telegram user IDs admin (koma-separated) |
| `TIMEZONE` | – | Default `Asia/Jakarta` (untuk scheduler bot) |
| `FONNTE_TOKEN` | – | WhatsApp gateway (kirim QR member otomatis) |
| `BASE_URL` | – | Untuk link QR ke aplikasi |

### 3. Initialize database

```bash
# Alembic migrations
alembic upgrade head
```

Atau biarkan `run_dashboard.py` auto-create tables saat pertama jalan
(`app.db.database.init_db()`).

## Run

### Dashboard web

```bash
python run_dashboard.py
# http://localhost:5000
```

Production (gunicorn):
```bash
gunicorn run_dashboard:app --bind=0.0.0.0:8000 --workers 2
```

Login admin: `/login` (pakai `DASHBOARD_PASSWORD`).
Portal capster: `/portal/login` (pakai `username` + `password` dari DB).

### Bot Telegram

```bash
python run_bot.py
```

Kirim `/start` ke bot di Telegram (akun harus terdaftar di
`OWNER_IDS` atau `ADMIN_IDS`).

Command yang tersedia:
- `/harian` — laporan hari ini
- `/mingguan` — 7 hari terakhir
- `/bulanan` — bulan ini
- `/profit` — profit per cabang (full calc + komisi)
- `/capster` — breakdown per capster
- `/help` — bantuan

Notifikasi otomatis ringkasan harian dikirim ke semua `OWNER_IDS` setiap
**23:00 WIB** (lewat JobQueue python-telegram-bot).

## Deploy

### Azure App Service

Sudah dikonfigurasi:
- `startup.sh` — jalankan gunicorn `run_dashboard:app`
- `wsgi.py` (Linux) & `application.py` (Windows) — entry point

Bot Telegram tidak ter-deploy ke Azure. Jalankan terpisah (VPS, Cloud
Run, atau laptop owner).

### Lain (Render, Railway, dll.)

Sama saja: `gunicorn run_dashboard:app` untuk web. Untuk bot, perlu
worker process terpisah.

## Migrations

```bash
# Buat migration baru setelah ubah models.py
alembic revision --autogenerate -m "deskripsi perubahan"

# Apply
alembic upgrade head

# Rollback satu langkah
alembic downgrade -1
```

## Folder `scripts/`

Arsip script migrasi historis (one-off, sudah dijalankan):
- `migrate_from_sheets.py` — migrasi Google Sheets → SQLite (Februari 2026)
- `migrate_sqlite_to_postgres.py` — migrasi SQLite → PostgreSQL
- `fix_branch_data.py` — normalisasi kolom branch (April 2026)

Disimpan sebagai referensi. Jangan jalankan ulang kecuali butuh.

## License

Private Project
