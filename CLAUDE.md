# CLAUDE.md — Konteks untuk sesi Claude Code

> File ini di-load otomatis oleh Claude Code saat membuka project ini. Gunakan untuk konteks proyek yang harus diketahui SEBELUM mulai kerja, bukan dokumentasi mendalam (yang ada di [ARCHITECTURE.md](ARCHITECTURE.md)).

## Apa proyek ini

**Barbershop Management System** — sistem manajemen barbershop multi-cabang. Satu web app + shared core:

- **Web dashboard** (`web/`) — admin & capster portal.
- **Shared core** (`app/`) — config, db (SQLAlchemy), services (business logic).

**Production = laptop owner + Cloudflare Tunnel.** Tidak ada cloud deploy.

Owner: arsybejo@gmail.com. Bisnis aktif (bukan sandbox).

## Aturan import — wajib dipatuhi

```
app/   → boleh diimpor semua
web/   → impor dari app/
```

Business logic letakkan di `app/services/`. Route web harus **tipis**: terima input → panggil service → format output.

## Entry points

| File | Untuk apa |
|------|-----------|
| `run_dashboard.py` | Jalankan Flask dashboard (`python run_dashboard.py`) |

Jangan buat entry point baru di root. Tambahkan script one-off ke `scripts/`.

## Stack & versi

- Python 3.11+ (venv di `venv/`)
- Flask 2.3, SQLAlchemy 2.0, Alembic
- Flask-Limiter 3.8 (rate limit login), Flask-WTF 1.2 (CSRF)
- DB: PostgreSQL 18 (prod & local), SQLite (fallback dev) — pilih lewat `DATABASE_URL`
- Pandas (laporan), Werkzeug (auth hashing + check_password_hash), Fonnte (WhatsApp gateway)

## Common commands

```bash
# Run
python run_dashboard.py       # web, port 5000

# DB
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "ubah X"  # buat migration baru

# Backup DB sebelum migrasi/refactor besar
"C:/Program Files/PostgreSQL/18/bin/pg_dump.exe" -h localhost -U postgres -d barbershop_db -f backups/dump_$(date +%Y%m%d_%H%M%S).sql

# Syntax check (Claude shell tidak punya deps; pakai venv kalau perlu runtime test)
py -m py_compile <file>
venv/Scripts/python.exe -c "from web import create_app; create_app()"
```

## Konvensi commit

Format mengikuti Conventional Commits versi singkat:
```
<type>: <pesan singkat Indonesia>

<body opsional, jelaskan WHY>
```
- `feat:` fitur baru
- `fix:` bug fix
- `refactor:` perubahan struktur tanpa ubah behaviour
- `chore:` housekeeping
- `docs:` dokumentasi
- `backup:` snapshot/checkpoint

Bahasa: Indonesia. Subject ≤ 72 char.

## Branch strategy

```
main      → production (langsung jalan dari laptop owner, tidak auto-deploy)
staging   → pre-production / QA
dev       → integration
feature/* → fitur individual (PR ke dev)
```

Ideal: push langsung ke `main` cuma untuk fix kecil. Refactor besar lewat PR
dari `dev` → `staging` → `main`. Tapi sekarang sering langsung ke `main` karena
single-developer & no CI.

## Hal yang TIDAK boleh dilakukan

1. **Jangan paste secret asli (.env values, tokens, passwords) ke chat Claude** — Claude transcript disimpan di disk dan ke server. Pakai placeholder atau `<redacted>`.
2. **Jangan commit `.env` atau `credentials.json`** — sudah di-gitignore, tapi jangan iseng `git add -f`.
3. **Jangan delete `backups/`** — dump DB lokal, kalau hilang tidak bisa dikembalikan.
4. **Jangan hidupkan kembali Google Sheets** — sudah dimigrasi ke SQLAlchemy, balik = downgrade.
5. **Jangan rename `run_dashboard.py`** — Cloudflare Tunnel config & shortcut owner mengasumsikan nama ini.

## Security — semua audit findings sudah di-fix

5 temuan audit 2026-04-18 sudah selesai semua (commit `d4d8088`, `661af37`,
`6bb1635`, `6e5c512`). Tetap berhati-hati:

- `DASHBOARD_SECRET_KEY` & `DASHBOARD_PASSWORD_HASH` di `.env` — tanpa default
  fallback. Kalau kosong, app raise RuntimeError di startup.
- CSRF aktif global via Flask-WTF. Semua form POST harus include
  `{{ csrf_token() }}` (sudah injected di 21 template).
- Rate limit 5/menit di `/login` & `/portal/login` pakai Flask-Limiter +
  ProxyFix supaya ambil real IP dari Cloudflare Tunnel.
- Session cookies: SECURE conditional (HTTPS prod), HTTPONLY=True, SAMESITE=Lax.

Detail di [TODO.md](TODO.md) → "Security" section (semua centang).

## Loyalty system — aturan

- `point_balance` & `visit_count` adalah dua kolom independen di `customers`.
- Per transaksi customer (tanpa klaim): +1 visit, +1 poin (cap di 10).
- Klaim 50%: -5 poin (`max(0, balance - 5)`). Klaim Free: -10 poin (`max(0, balance - 10)`).
- Visibility lenient (anticipate +1): customer 4 poin sudah lihat opsi klaim 50%.
- Setiap mutasi poin auto-log di tabel `loyalty_audits`. Lihat
  `/customers/<id>/loyalty` untuk history per customer.
- Tidak ada auto-sync `point = visit_count` di `init_db()` (sudah dihapus,
  pernah jadi sumber bug). Sync manual via `scripts/sync_loyalty_points.py`.

## Memori auto-load

Selain CLAUDE.md ini, ada juga memori Claude pribadi user di:
`C:\Users\tama\.claude\projects\D--Document-barber-bot-barber-2\memory\MEMORY.md`

Memori itu untuk preferensi user. CLAUDE.md ini untuk konteks proyek (commit ke repo, dibaca semua dev).

## Untuk lebih dalam

- Arsitektur detail: [ARCHITECTURE.md](ARCHITECTURE.md)
- Pekerjaan pending: [TODO.md](TODO.md)
- Setup awal & cara jalankan (web + tunnel): [README.md](README.md)
- `docs/*.md` — semua versi v1 (era Telegram bot + Google Sheets), abaikan / tunggu dihapus
