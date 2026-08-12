# ARCHITECTURE.md

Dokumentasi arsitektur teknis. Untuk konteks singkat lihat [CLAUDE.md](CLAUDE.md).

## High-level

```
┌───────────────────┐
│  Admin & Capster  │
│      (browser)    │
└─────────┬─────────┘
          │ HTTPS
          ▼
┌───────────────────┐
│   web/  (Flask)   │
│  - blueprints     │
│  - Jinja2 views   │
│  - login_required │
└─────────┬─────────┘
          │
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
| **Service** | `app/services/` | Business logic murni, pure functions, tidak tahu transport |
| **Data** | `app/db/` | ORM models, repository pattern, session management |
| **Config** | `app/config/` | Constants (BRANCHES, SERVICES_MAIN), env settings |
| **Persistence** | `alembic/` | DB migrations |
| **One-off** | `scripts/` | Arsip migrasi & utility script |

## Aturan dependency

```
                ┌─────────┐
                │   app   │
                └─────────┘
                     ▲
                     │
                  ┌──┴──┐
                  │ web │
                  └─────┘
```

- **`app/` adalah leaf**: tidak impor dari mana pun (kecuali stdlib & third-party).
- **`web/`**: boleh impor dari `app/`.
- Pelanggaran aturan ini langsung jadi indikator code smell — duplikasi atau coupling salah arah.

## Data model (13 tabel)

Definisi di `app/db/models.py`. Yang penting:

| Tabel | Isi | Catatan |
|-------|-----|---------|
| `transactions` | Setiap transaksi layanan | Index by `date`, `branch`, `(capster, date)`. `promo_name` juga simpan "Loyalty 50%/Gratis" untuk klaim |
| `capsters` | Master capster | `telegram_id` warisan bot lama (UNIQUE, masih dipakai untuk identitas), `username` untuk login web |
| `customers` | Pelanggan | `point_balance` & `visit_count` independen |
| `loyalty_claims` | Riwayat klaim poin | `claim_type` = `50pct` atau `free`, `transaction_id` linked |
| `loyalty_audits` | Audit trail per perubahan poin | reason: `transaction`/`claim_*`/`manual_edit`/`sync`, actor tercatat |
| `services` | Master layanan | `commission_rate` per layanan (mitra) |
| `branches` | Master cabang | `commission_rate` per cabang (fallback) |
| `products` | Master produk | Punya `commission_rate` sendiri |
| `product_stocks` | Stok produk per cabang | Composite PK |
| `product_sales` | Penjualan produk | Tracking komisi capster |
| `promos` | Promo aktif | `service_ids` & `branch_ids` comma-separated |
| `settings` | Key-value config app | Misal token Fonnte, WA template |
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

| Endpoint | Decorator | Auth check |
|----------|-----------|------------|
| `/admin`, `/transactions`, dll | `@login_required` | Session `logged_in` setelah submit `DASHBOARD_PASSWORD` |
| `/portal/*` | `@capster_login_required` | Session `capster_logged_in` setelah verify `username` + `password_hash` |
| `/`, `/login`, `/portal/login` | (public) | – |

## Lifecycle web request

1. `python run_dashboard.py` → Flask dev server bind ke `0.0.0.0:5000`
2. `run_dashboard.py`: `load_dotenv()` → `init_db()` → `from web import create_app` → `app = create_app()`
3. `create_app()` register blueprints
4. Cloudflare Tunnel forward request publik → `localhost:5000`
5. Request masuk: Flask routing → blueprint handler (`web/routes/*.py`)
6. Handler: parse params → panggil `Repository` (atau service di `app/services/`) → render Jinja2 template
7. Response keluar lewat tunnel kembali ke browser

## Deploy topology

```
                       Internet
                          │
                          ▼
            ┌────────────────────────────┐
            │   Cloudflare Tunnel        │
            │   (public URL → localhost) │
            └────────────┬───────────────┘
                         │
            ┌────────────▼───────────────┐
            │  Owner's laptop (Windows)  │
            │  D:\Document\barber\...    │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ python run_dashboard │  │  Flask :5000
            │  └──────────────────────┘  │
            │                            │
            │  ┌──────────────────────┐  │
            │  │ PostgreSQL 18        │  │  localhost:5432
            │  │ barbershop_db        │  │
            │  └──────────────────────┘  │
            └────────────────────────────┘
```

**Catatan deploy:**
- **Single host**: web + DB jalan di laptop yang sama. Tidak ada cloud deploy.
- **Cloudflare Tunnel**: traffic publik masuk lewat tunnel ke `localhost:5000`. URL publik dikelola di dashboard Cloudflare Zero Trust. Tunnel ini sekaligus dipakai pentest lab (lihat memori `project_security_audit`).
- **Implikasi single host**:
  - Laptop mati = web mati → SPOF (single point of failure)
  - DB tidak punya off-site replica → backup harian via `pg_dump` ke disk lain wajib
  - Tidak ada gunicorn / WSGI server di prod (Flask dev server cukup untuk traffic kecil; bisa ditingkatkan dengan `waitress` Windows-native kalau perlu)

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
| pandas | Migrasi dari Sheets era — semua kalkulasi laporan pakai DataFrame |
| Werkzeug `check_password_hash` | Standar Flask, salt-aware |
| Fonnte WA gateway | Murah & mudah untuk Indonesia (vs. WA Business API) |

## Hal yang belum ideal (intentional / debt)

1. **In-memory constants di `app/config/constants.py`** — di-mutate dari DB saat seed. Idealnya selalu read langsung dari DB.
2. **`telegram_id` di `Capster`** — warisan dari bot lama, masih NOT NULL constraint. Login pakai username/password sekarang. Kalau ada capster baru tanpa Telegram, harus diisi dummy ID.
3. **Pandas-heavy reports** — slow di dataset besar. Belum ada masalah scale, tapi OK to ganti dengan SQL aggregation kalau perlu.
4. **`add_transaction_legacy` di Repository** — placeholder NotImplementedError, sisa bot lama. Bisa dihapus.

## Loyalty system semantic

- `customers.visit_count` & `customers.point_balance` adalah dua kolom **independen**:
  - `visit_count`: monotonic counter, +1 per transaksi-dengan-customer
  - `point_balance`: wallet poin, +1 per transaksi normal, -threshold saat klaim
- Threshold: 5 poin = Diskon 50%, 10 poin = Potong Gratis. MAX_POINTS=10.
- **Visibility lenient**: UI tampilkan opsi klaim kalau `balance + 1 >= threshold`
  (mengantisipasi +1 dari visit ini). Customer 4 poin sudah bisa lihat opsi 50%.
- **Klaim subtractive**: sisa = `max(0, balance - threshold)`. Customer 6 poin
  klaim 50% → sisa 1. Customer 4 poin klaim 50% → sisa 0 (clamp).
- **Saat klaim, visit ini TIDAK +1 poin** (tidak earn & spend bareng).
- Semua mutasi poin auto-log di `loyalty_audits` dengan actor (capster/admin/system)
  & reason (`transaction`/`claim_50pct`/`claim_free`/`manual_edit`/`sync`). View via
  `/customers/<id>/loyalty`.
- Sync masal data lama: `python scripts/sync_loyalty_points.py [--apply]`.
  Tidak ada auto-sync di startup (sebelumnya pernah, dihapus karena bug).

## Customer registration flow (capster portal)

Inline di `/portal/add-transaction` Step 2 — tidak ada halaman terpisah
"Tambah Pengunjung" lagi:

1. Capster pilih layanan + buka "Customer" section.
2. Tiga opsi: Scan QR, Cari Nama/HP, **Customer Baru**.
3. Klik "Customer Baru" → muncul inline form (nama + HP).
4. Capster ketik nomor HP → AJAX `/portal/customer/check-phone` → kalau
   sudah terdaftar, warning muncul dengan tombol "Pakai customer ini".
5. Tombol set `customer_id` sync (tidak race condition) lalu fetch loyalty
   info async untuk update badge poin & opsi klaim.
6. Submit form → server membuat customer (kalau bener-bener baru) + tx
   atomik. Dua mutasi dalam 1 request.

## Glossary

- **Capster**: tukang potong rambut. Dua tipe: **mitra** (komisi %) & **tetap** (gaji bulanan).
- **Branch**: cabang barbershop. Punya biaya operasional bulanan.
- **Loyalty claim**: penukaran poin customer — `50pct` (5 poin → diskon 50%) atau `free` (10 poin → gratis).
- **Promo**: diskon yang berlaku untuk service & branch tertentu, dalam rentang tanggal.
- **Mitra**: capster yang dibayar % dari layanan/produk yang dia jual.
- **Tetap**: capster gajian bulanan flat.
- **Walk-in**: transaksi tanpa link ke customer (tidak earn poin, tidak +visit).
- **Audit log**: row di `loyalty_audits`. Read-only history setiap perubahan poin.