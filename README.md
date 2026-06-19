# Barbershop Management

Sistem manajemen barbershop multi-cabang. Terdiri dari dua channel:

- **Web dashboard** — admin (laporan, kelola data) dan capster (self-service portal)
- **Bot Telegram** — laporan ringkasan untuk owner/admin (read-only)

## Tech Stack

- **Python 3.11+**
- **Flask 2.3** — web framework
- **Flask-WTF 1.2** — CSRF protection global di semua form POST
- **Flask-Limiter 3.8** — rate limit login (5/menit per IP)
- **SQLAlchemy 2.0** — ORM
- **Alembic** — database migrations
- **PostgreSQL** (production) / **SQLite** (dev) — pilih lewat `DATABASE_URL`
- **python-telegram-bot 21.7** — bot
- **pandas** — kalkulasi laporan
- **Werkzeug** — `check_password_hash` (admin & capster login)

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
| `DASHBOARD_PASSWORD_HASH` | ✅ | Hash admin password. Generate: `py -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_PWD'))"` |
| `DASHBOARD_SECRET_KEY` | ✅ | Random 32-byte hex. Generate: `py -c "import secrets; print(secrets.token_hex(32))"` |
| `TELEGRAM_BOT_TOKEN` | ⚠️ | Wajib kalau pakai bot. Dapat dari [@BotFather](https://t.me/BotFather) |
| `OWNER_IDS` | ⚠️ | Telegram user IDs owner (koma-separated). Bot auth & notifikasi 23:00 |
| `ADMIN_IDS` | ⚠️ | Telegram user IDs admin (koma-separated) |
| `TIMEZONE` | – | Default `Asia/Jakarta` (untuk scheduler bot) |
| `FONNTE_TOKEN` | – | WhatsApp gateway (kirim QR member otomatis) |
| `BASE_URL` | – | Untuk link QR ke aplikasi |
| `DEBUG` | – | `True` untuk dev (cookie SECURE off). Default `False` |

> **Tanpa `DASHBOARD_SECRET_KEY` atau `DASHBOARD_PASSWORD_HASH`, app raise
> `RuntimeError` di startup** (intentional fail-loud, tidak ada default fallback).

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

Production = **laptop owner + Cloudflare Tunnel**. Tidak ada cloud
deploy. Web + bot + PostgreSQL semua di mesin yang sama.

### Cloudflare Tunnel (web)

Tunnel sudah dikonfigurasi di dashboard Cloudflare Zero Trust,
forward URL publik → `localhost:5000`. Untuk menjalankan production:

```bash
# Terminal 1 — dashboard web
python run_dashboard.py

# Terminal 2 — tunnel (kalau pakai cloudflared CLI)
cloudflared tunnel run <tunnel-name>
```

Atau pakai Cloudflare Tunnel service (cloudflared di-install sebagai
Windows service via `cloudflared service install`), supaya tunnel
auto-start saat boot.

### Bot Telegram

```bash
python run_bot.py
```

Saat ini dijalankan manual saat dibutuhkan. Rencananya auto-start
lewat Windows Task Scheduler atau NSSM (lihat TODO.md).

### Backup DB

Ingat: ini single-host. Backup PostgreSQL harian wajib:

```powershell
# PowerShell scheduled task harian
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" `
   -h localhost -U postgres -d barbershop_db `
   -f "D:\Document\barber\bot_barber_2\backups\auto_$(Get-Date -Format yyyyMMdd).sql"
```

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

Mix arsip historis + maintenance script aktif:

| Script | Status | Apa |
|---|---|---|
| `migrate_from_sheets.py` | Arsip | Migrasi Google Sheets → SQLite (Feb 2026) |
| `migrate_sqlite_to_postgres.py` | Arsip | Migrasi SQLite → PostgreSQL |
| `fix_branch_data.py` | Arsip | Normalisasi kolom branch (Apr 2026) |
| `sync_loyalty_points.py` | **Aktif** | Sync `point_balance` dari `visit_count − klaim_used`. Idempotent. Run dengan `--apply` untuk write. Pakai kalau ada inkonsistensi data atau setelah import bulk. |

## Loyalty rules (singkat)

- Tiap transaksi-dengan-customer: +1 visit + +1 poin (cap 10).
- Klaim 50% (5 poin): sisa = `max(0, balance − 5)`.
- Klaim Free (10 poin): sisa = `max(0, balance − 10)`.
- Visibility lenient: customer 4 poin sudah bisa klaim 50% (antisipasi +1 visit).
- Setiap mutasi poin auto-log di tabel `loyalty_audits`. Lihat per customer di
  `/customers/<id>/loyalty` atau ikon ⭐ di tabel customer.

Detail lengkap di [ARCHITECTURE.md](ARCHITECTURE.md) → "Loyalty system semantic".

## License

Private Project
