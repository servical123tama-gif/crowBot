# AGENTS.md — Konteks untuk sesi Codex

> File ini di-load otomatis oleh Codex saat membuka project ini. Gunakan untuk konteks proyek yang harus diketahui SEBELUM mulai kerja, bukan dokumentasi mendalam (yang ada di [ARCHITECTURE.md](ARCHITECTURE.md)).

## Apa proyek ini

**Barbershop Management System** — sistem manajemen barbershop multi-cabang. Dua channel terpisah, satu shared core:

- **Web dashboard** (`web/`) — admin & capster portal.
- **Bot Telegram** (`bot/`) — read-only laporan untuk admin.
- **Shared core** (`app/`) — config, db (SQLAlchemy), services (business logic).

**Production = laptop owner + Cloudflare Tunnel.** Tidak ada cloud deploy. Web & bot keduanya jalan dari mesin lokal yang sama. Bot saat ini jarang dinyalakan tapi rencananya rutin.

Owner: arsybejo@gmail.com. Bisnis aktif (bukan sandbox).

## Aturan import — wajib dipatuhi

```
app/   → boleh diimpor semua
web/   → impor dari app/, TIDAK boleh impor bot/
bot/   → impor dari app/, TIDAK boleh impor web/
```

Business logic letakkan di `app/services/`. Route web & handler bot harus **tipis**: terima input → panggil service → format output. Jangan duplikasi logic antar channel.

## Entry points

| File | Untuk apa |
|------|-----------|
| `run_dashboard.py` | Jalankan Flask dashboard (`python run_dashboard.py`) |
| `run_bot.py` | Jalankan Telegram bot (`python run_bot.py`) |

Jangan buat entry point baru di root. Tambahkan script one-off ke `scripts/`.

## Stack & versi

- Python 3.11+ (venv di `venv/`)
- Flask 2.3, SQLAlchemy 2.0, Alembic, python-telegram-bot 21.7
- DB: PostgreSQL 18 (prod & local), SQLite (fallback dev) — pilih lewat `DATABASE_URL`
- Pandas (laporan), Werkzeug (auth hashing), Fonnte (WhatsApp gateway)

## Common commands

```bash
# Run
python run_dashboard.py       # web, port 5000
python run_bot.py             # bot polling

# DB
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "ubah X"  # buat migration baru

# Backup DB sebelum migrasi/refactor besar
"C:/Program Files/PostgreSQL/18/bin/pg_dump.exe" -h localhost -U postgres -d barbershop_db -f backups/dump_$(date +%Y%m%d_%H%M%S).sql

# Syntax check (Codex shell tidak punya deps; pakai venv kalau perlu runtime test)
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

## Branch strategy (sudah jalan)

```
main      → production (auto-deploy ke Azure)
staging   → pre-production / QA
dev       → integration
feature/* → fitur individual (PR ke dev)
```

Jangan push langsung ke `main` — selalu PR dari `dev` atau `staging`.

## Hal yang TIDAK boleh dilakukan

1. **Jangan paste secret asli (.env values, tokens, passwords) ke chat Codex** — Codex transcript disimpan di disk dan ke server. Pakai placeholder atau `<redacted>`.
2. **Jangan commit `.env` atau `credentials.json`** — sudah di-gitignore, tapi jangan iseng `git add -f`.
3. **Jangan delete `backups/`** — dump DB lokal, kalau hilang tidak bisa dikembalikan.
4. **Jangan hidupkan kembali Google Sheets** — sudah dimigrasi ke SQLAlchemy, balik = downgrade.
5. **Jangan rename `run_dashboard.py` / `run_bot.py`** — Cloudflare Tunnel config & shortcut owner mengasumsikan nama ini.

## Kerentanan known (HARUS verify sebelum lanjut)

Audit 2026-04-18 menemukan 5 issue. Beberapa mungkin sudah di-patch — cek dulu sebelum klaim solved:

1. Default `DASHBOARD_SECRET_KEY` / `DASHBOARD_PASSWORD` fallback di `web/__init__.py` & `web/auth.py`
2. Tidak ada CSRF protection di form POST
3. Admin password compare plain-text (no hash, no rate limit)
4. Session cookie flags (SECURE/HTTPONLY/SAMESITE) belum diset
5. Tidak ada rate limit di `/login` & `/portal/login`

Detail di [TODO.md](TODO.md) → "Security".

## Memori auto-load

Selain AGENTS.md ini, ada juga memori Codex pribadi user di:
`C:\Users\tama\.Codex\projects\D--Document-barber-bot-barber-2\memory\MEMORY.md`

Memori itu untuk preferensi user. AGENTS.md ini untuk konteks proyek (commit ke repo, dibaca semua dev).

## Untuk lebih dalam

- Arsitektur detail: [ARCHITECTURE.md](ARCHITECTURE.md)
- Pekerjaan pending: [TODO.md](TODO.md)
- Setup awal & cara jalankan (web + bot + tunnel): [README.md](README.md)
- `docs/*.md` — semua versi v1 (Telegram bot + Google Sheets era), abaikan / tunggu dihapus
