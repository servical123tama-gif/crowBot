# ARCHITECTURE.md

Dokumentasi arsitektur teknis. Untuk konteks singkat lihat [CLAUDE.md](CLAUDE.md).

## High-level

```
┌───────────────────┐         ┌───────────────────┐
│  Admin & Capster  │         │       Owner       │
│      (browser)    │         │     (Telegram)    │
└─────────┬─────────┘         └─────────┬─────────┘
          │ HTTPS                       │ Bot API
          ▼                             ▼
┌───────────────────┐         ┌───────────────────┐
│   web/  (Flask)   │         │   bot/ (PTB 21)   │
│  - 15 blueprints  │         │  - 7 commands     │
│  - Jinja2 views   │         │  - inline buttons │
│  - login_required │         │  - JobQueue 23:00 │
└─────────┬─────────┘         └─────────┬─────────┘
          │                             │
          └──────────────┬──────────────┘
                         ▼
            ┌────────────────────────┐
            │   app/  (shared core)  │
            │  ┌──────────────────┐  │
            │  │ services/        │  │  business logic
            │  │  reports.py      │  │
            │  └────────┬─────────┘  │
            │           │            │
            │  ┌────────▼─────────┐  │
            │  │ db/              │  │  data access
            │  │  models.py       │  │
            │  │  repository.py   │  │
            │  └────────┬─────────┘  │
            │           │            │
            │  ┌────────▼─────────┐  │
            │  │ config/          │  │  constants & env
            │  └──────────────────┘  │
            └────────────┬───────────┘
                         ▼
                ┌────────────────┐
                │   PostgreSQL   │  (prod & local)
                │   ↳ SQLite     │  (fallback dev)
                └────────────────┘
```

## Folder layer

| Layer | Folder | Tanggung jawab |
|-------|--------|----------------|
| **Channel** | `web/` | Presentation — HTTP routes, templates, auth web |
| **Channel** | `bot/` | Presentation — Telegram commands, inline keyboard, auth bot |
| **Service** | `app/services/` | Business logic murni, pure functions, tidak tahu transport |
| **Data** | `app/db/` | ORM models, repository pattern, session management |
| **Config** | `app/config/` | Constants (BRANCHES, SERVICES_MAIN), env settings |
| **Persistence** | `alembic/` | DB migrations |
| **One-off** | `scripts/` | Arsip migrasi & utility script |

## Aturan dependency

```
                ┌─────────┐
                │   app   │ ◄────┐
                └─────────┘      │
                     ▲           │
                     │           │
                  ┌──┴──┐     ┌──┴──┐
                  │ web │     │ bot │
                  └─────┘     └─────┘
```

- **`app/` adalah leaf**: tidak impor dari mana pun (kecuali stdlib & third-party).
- **`web/` dan `bot/` adalah edge**: boleh impor dari `app/`, tidak boleh saling impor.
- Pelanggaran aturan ini langsung jadi indikator code smell — duplikasi atau coupling salah arah.

## Data model (12 tabel)

Definisi di `app/db/models.py`. Yang penting:

| Tabel | Isi | Catatan |
|-------|-----|---------|
| `transactions` | Setiap transaksi layanan | Index by `date`, `branch`, `(capster, date)` |
| `capsters` | Master capster | `telegram_id` warisan (UNIQUE), `username` untuk login web |
| `customers` | Pelanggan | `point_balance` untuk loyalty |
| `loyalty_claims` | Riwayat klaim poin | `claim_type` = `50pct` atau `free` |
| `services` | Master layanan | `commission_rate` per layanan (mitra) |
| `branches` | Master cabang | `commission_rate` per cabang (fallback) |
| `products` | Master produk | Punya `commission_rate` sendiri |
| `product_stocks` | Stok produk per cabang | Composite PK |
| `product_sales` | Penjualan produk | Tracking komisi capster |
| `promos` | Promo aktif | `service_ids` & `branch_ids` comma-separated |
| `settings` | Key-value config app | Misal token Fonnte |
| `salary_withdrawals` | Penarikan gaji capster | Period tracking |

Constants in-memory (`BRANCHES`, `SERVICES_MAIN`, dll) di `app/config/constants.py` di-mutate saat runtime dari DB (seed pada `init_db`). Ini design legacy — idealnya selalu load dari DB.

## Akses data

Semua akses DB lewat `Repository` (`app/db/repository.py`). Pattern:

```python
from app.db.repository import Repository

repo = Repository()
df = repo.get_transactions_by_date(datetime.now())
profit_data = calc_profit(repo, year=2026, month=5)  # service
```

Repository mengembalikan DataFrame pandas (legacy SheetsService format) atau dict. Connection management via `get_db()` context manager (`app/db/database.py`).

## Auth model

### Web

| Endpoint | Decorator | Auth check |
|----------|-----------|------------|
| `/admin`, `/transactions`, dll | `@login_required` | Session `logged_in` setelah submit `DASHBOARD_PASSWORD` |
| `/portal/*` | `@capster_login_required` | Session `capster_logged_in` setelah verify `username` + `password_hash` |
| `/`, `/login`, `/portal/login` | (public) | – |

### Bot

| Decorator | Logika |
|-----------|--------|
| `@admin_only` (di `bot/auth.py`) | `user.id ∈ (OWNER_IDS ∪ ADMIN_IDS)` parsed dari `.env` |

Bot tidak punya kelas role — semua admin/owner punya hak sama. Hanya `OWNER_IDS` yang menerima notifikasi 23:00.

## Lifecycle web request

1. `gunicorn run_dashboard:app` → load `wsgi.py` / `application.py`
2. `from run_dashboard import app` → `from web import create_app` → `create_app()`
3. `create_app()` register 15 blueprints
4. Request masuk: Flask routing → blueprint handler (`web/routes/*.py`)
5. Handler: parse params → panggil `Repository` (atau service di `app/services/`) → render Jinja2 template
6. Response keluar

## Lifecycle bot

1. `python run_bot.py` → load env → `init_db()` → `from bot import run`
2. `build_app()` membuat `telegram.ext.Application` + register `CommandHandler` & `CallbackQueryHandler`
3. `setup_daily_push()` register job `run_daily(_push_daily, 23:00 WIB)` ke JobQueue
4. `app.run_polling(allowed_updates=['message', 'callback_query'])` blocking
5. Update masuk: PTB routing → handler di `bot/handlers.py`
6. Handler: cek `@admin_only` → panggil `bot/reports.py` builder → kirim text

## Deploy topology

```
                    Internet
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
   ┌─────────────────┐   ┌───────────────────┐
   │  Azure App      │   │  Telegram Bot API │
   │  Service (Win)  │   │  (managed)        │
   │  ─ gunicorn     │   │                   │
   │  ─ Python 3.11  │   └────────┬──────────┘
   └────────┬────────┘            │ polling
            │                     ▼
            │            ┌────────────────────┐
            │            │ Owner's laptop /   │
            │            │ VPS (belum diatur) │
            │            │ ─ python run_bot.py│
            │            └────────┬───────────┘
            │                     │
            └──────────┬──────────┘
                       ▼
            ┌──────────────────────┐
            │  PostgreSQL          │
            │  (mana? — lihat env) │
            └──────────────────────┘
```

**Catatan deploy:**
- **Web**: sudah aktif di Azure App Service. Auto-deploy dari branch `main` (lihat `.github/workflows/`).
- **Bot**: belum di-deploy. Saat ini cuma jalan di laptop owner saat manual. Untuk auto-run 24/7 perlu VPS / Azure Container Apps / Cloud Run / Worker process.
- **PostgreSQL**: env `DATABASE_URL` menentukan. Local dev pakai `localhost:5432`, prod sebaiknya managed DB (Azure Database for PostgreSQL atau Supabase).

## Constants legacy (`app/config/constants.py`)

File ini campur:
1. **Aktif & dipakai**: `BRANCHES`, `SERVICES_MAIN`, `SERVICES_COLORING`, `PRODUCTS`, `PAYMENT_METHODS`, `MONTHS_*`, dll.
2. **Legacy bot Telegram lama**: `CB_*` callback prefixes (~50 baris) — bisa dihapus, tidak ada importer setelah refactor.
3. **Legacy Sheets**: `SHEET_*` names — sudah tidak relevan.

Cleanup belum dilakukan supaya tidak ganggu fokus rename folder. TODO ada di [TODO.md](TODO.md).

## Library choices & alasan

| Pilihan | Alasan |
|---------|--------|
| Flask (bukan FastAPI) | Aplikasi server-rendered HTML, bukan API. Jinja2 mature. |
| SQLAlchemy ORM | Dropin migration dari Sheets, pandas integrasi mudah |
| python-telegram-bot v21 | Latest stable async; built-in JobQueue |
| pandas | Migrasi dari Sheets era — semua kalkulasi laporan pakai DataFrame |
| Werkzeug `check_password_hash` | Standar Flask, salt-aware |
| Fonnte WA gateway | Murah & mudah untuk Indonesia (vs. WA Business API) |

## Hal yang belum ideal (intentional / debt)

1. **In-memory constants di `app/config/constants.py`** — di-mutate dari DB saat seed. Idealnya selalu read langsung dari DB.
2. **`telegram_id` di `Capster`** — warisan dari bot lama, masih NOT NULL constraint. Login pakai username/password sekarang. Kalau ada capster baru tanpa Telegram, harus diisi dummy ID.
3. **Pandas-heavy reports** — slow di dataset besar. Belum ada masalah scale, tapi OK to ganti dengan SQL aggregation kalau perlu.
4. **`add_transaction_legacy` di Repository** — placeholder NotImplementedError, sisa bot lama. Bisa dihapus.

## Diagram interaksi: contoh "Owner cek profit Mei via bot"

```
Owner          Telegram          PTB           bot/handlers   bot/reports   app/services   Repository    PostgreSQL
  │              │                │                │              │              │             │            │
  ├─"/profit"───▶│                │                │              │              │             │            │
  │              ├─update────────▶│                │              │              │             │            │
  │              │                ├─cmd_profit────▶│              │              │             │            │
  │              │                │           @admin_only check OK│              │             │            │
  │              │                │                ├─profit_report()             │             │            │
  │              │                │                │              ├─calc_profit()│             │            │
  │              │                │                │              │              ├─get_txns()──▶│            │
  │              │                │                │              │              │             ├─SELECT────▶│
  │              │                │                │              │              │             │◀──rows─────┤
  │              │                │                │              │              │◀───────DF───┤            │
  │              │                │                │              │◀──dict──────┤             │            │
  │              │                │                │◀──text──────┤              │             │            │
  │              │                │◀──reply───────┤              │              │             │            │
  │              │◀──message──────┤                │              │              │             │            │
  │◀──notif──────┤                │                │              │              │             │            │
```

## Glossary

- **Capster**: tukang potong rambut. Dua tipe: **mitra** (komisi %) & **tetap** (gaji bulanan).
- **Branch**: cabang barbershop. Punya biaya operasional bulanan.
- **Loyalty claim**: penukaran poin customer — `50pct` (10 visit → diskon 50%) atau `free` (20 visit → gratis).
- **Promo**: diskon yang berlaku untuk service & branch tertentu, dalam rentang tanggal.
- **Mitra**: capster yang dibayar % dari layanan/produk yang dia jual.
- **Tetap**: capster gajian bulanan flat.
