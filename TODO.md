# TODO.md

Daftar pekerjaan terorganisasi by priority. Update saat selesai (centang `[x]`).

> Tanggal acuan: 2026-05-31.

---

## 🔴 Critical — Security (audit 2026-04-18)

Verifikasi dulu mana yang sudah di-patch sebelum mulai kerja. Lihat juga memori `project_security_audit.md`.

- [ ] **#1 Default secret key & admin password fallback**
  - File: `web/__init__.py` (`secret_key = os.getenv('DASHBOARD_SECRET_KEY', 'barbershop-dashboard-2026')`), `web/auth.py` (`DASHBOARD_PASSWORD` default `'admin123'`)
  - Fix: `os.environ['DASHBOARD_SECRET_KEY']` (raise kalau kosong, fail loud). Hapus default `admin123`.
  - Test: jalankan tanpa env var → harus error eksplisit.

- [ ] **#2 CSRF protection di semua form POST**
  - Affected: `/login`, `/portal/login`, semua POST di transactions/customers/withdraw/profit/promos
  - Fix: `Flask-WTF` atau `flask-seasurf`. Tambahkan `{{ csrf_token() }}` ke semua form template.
  - Risk: PR besar — bertahap per blueprint, atau global setting + opt-out per endpoint.

- [ ] **#3 Admin password compare plain-text + no rate limit**
  - File: `web/routes/home.py` (login handler)
  - Fix: hash `DASHBOARD_PASSWORD` di setup script, simpan di env sebagai hash. Gunakan `check_password_hash`. Tambah `Flask-Limiter` rate limit di `/login`.
  - Bonus: pertimbangkan migrasi ke akun admin di tabel DB (mirip capster).

- [ ] **#4 Session cookie flags absent**
  - File: `web/__init__.py`
  - Fix: tambahkan setelah `app.secret_key = ...`:
    ```python
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    ```
  - Caveat: `SECURE=True` butuh HTTPS — set ke `False` dev only via env flag.

- [ ] **#5 Rate limit di `/login` & `/portal/login`**
  - Fix: `Flask-Limiter` dengan limit misal `5/minute per IP` untuk login endpoints.
  - Test: brute-force script harus kena 429.

---

## 🟠 High Priority — Operational

- [ ] **Bot Telegram belum di-deploy**
  - Status: hanya jalan di laptop owner saat dijalankan manual.
  - Opsi deploy (pilih satu):
    - Azure Container App (1 worker, persistent)
    - Cloud Run (cold start jadi delay polling)
    - VPS murah (Hetzner / Contabo) — paling fleksibel, sekitar $5/bulan
  - Setelah deploy, tambah systemd / supervisor untuk auto-restart.

- [ ] **`.env.example` masih punya legacy var**
  - File: `.env.example`
  - Hapus: `AUTHORIZED_CAPSTERS` (bot lama), `GOOGLE_SHEET_ID`, `GEMINI_API_KEY`, `DB_DUAL_WRITE`, `DB_ONLY`
  - Tambah deskripsi WHY untuk yang baru.

- [ ] **`docs/` masih versi v1 (Google Sheets era)**
  - File: `docs/SETUP.md`, `docs/DEPLOYMENT.md`, `docs/API.md`
  - Aksi: hapus + redirect ke `README.md` + `ARCHITECTURE.md`, atau tulis ulang.
  - Rekomendasi: hapus saja, info sudah ada di root docs baru.

- [ ] **GitHub Actions: tambah CI lint + test**
  - File: `.github/workflows/ci.yml` (baru)
  - Jalankan: `py_compile` semua file, `ruff check`, `pytest` (kalau sudah ada test).
  - Trigger: PR ke `dev`, `staging`, `main`.

- [ ] **Belum ada test sama sekali**
  - Folder `test/` sudah dihapus karena semua broken.
  - Mulai dari `tests/test_services_reports.py` (test `calc_profit` dengan data sintetis).
  - Pakai `pytest` + `pytest-mock`. Fixture untuk in-memory SQLite.

---

## 🟡 Medium — Tech Debt

- [ ] **`app/config/constants.py` cleanup**
  - Hapus `CB_*` callback constants (sisa bot Telegram lama, sudah tidak ada importer)
  - Hapus `SHEET_*` constants (Sheets era)
  - Konsider: pindahkan `BRANCHES`, `SERVICES_MAIN`, dll ke DB-only access (jangan mutate constants in-memory)

- [ ] **`telegram_id` constraint di tabel `Capster`**
  - Saat ini `NOT NULL` + `UNIQUE`. Login pakai `username`+`password_hash`, jadi `telegram_id` legacy.
  - Migration: bikin `nullable=True`. Atau hapus column (perlu cek importer).

- [ ] **`add_transaction_legacy` placeholder di Repository**
  - File: `app/db/repository.py` line ~33
  - Hapus method ini (`raise NotImplementedError` + dead try/except).

- [ ] **README QR (`.gitignore` regenerated)**
  - `web/static/qr/member_*.png` ke-track di git, accumulate forever.
  - Aksi: tambah `web/static/qr/` ke `.gitignore`, atau pakai `git rm --cached` + commit.
  - Catatan: QR di-generate dari `customer_id` jadi reproducible.

- [ ] **Logging structure**
  - Setiap module logging.getLogger(__name__) sudah OK, tapi tidak ada rotation/retention.
  - Pertimbangkan `logging.handlers.RotatingFileHandler` atau ship ke Azure Log Analytics.

- [ ] **Type hints di Repository**
  - Banyak method return `pd.DataFrame` atau `List[Dict[str, Any]]` — masih bisa diketat.

---

## 🟢 Low — Future / Nice to have

- [ ] **`scripts/` butuh README**
  - Tiap script kasih comment di header: kapan terakhir dijalankan, masih relevan atau arsip.

- [ ] **Re-enable AI `/tanya` di bot** (kalau owner mau)
  - Pakai Gemini atau Claude. Read-only query: "berapa pendapatan minggu ini?" → SQL aggregate → natural answer.

- [ ] **Multi-tenancy** (kalau scale ke barbershop lain)
  - Saat ini single-tenant. Untuk multi: tambah `org_id` FK ke semua tabel, scope query.

- [ ] **Dashboard real-time updates** (WebSocket / SSE)
  - Saat ini refresh manual. Owner ingin lihat transaksi muncul live? Pakai Flask-SocketIO atau SSE polling tiap 10s.

- [ ] **Export laporan ke Excel**
  - `openpyxl` sudah di requirements. Tambah endpoint `/profit/export?year=Y&month=M` → `.xlsx`.

---

## 📊 Progress tracker

Hitung manual setelah update:
- Critical: ☐ 5
- High: ☐ 5
- Medium: ☐ 6
- Low: ☐ 5

Total: **21 item**.

---

## Catatan kebiasaan update

1. Saat mulai item, **buat branch** `fix/security-#1-secret-key` atau `feat/bot-deploy` dari `dev`.
2. **Centang `[x]`** sebelum merge PR.
3. **Pindahkan ke "Done & archived"** kalau item terlalu lama tidak relevan.
4. **Tambah konteks WHY** di setiap item baru — jangan cuma "fix X". Format:
   ```
   - [ ] **Singkat**
     - Why: alasan
     - Affected: file/area
     - Risk: dampak kalau salah
   ```
