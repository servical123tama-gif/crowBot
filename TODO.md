# TODO.md

Daftar pekerjaan terorganisasi by priority. Update saat selesai (centang `[x]`).

> Tanggal acuan: 2026-05-31.

---

## 🔴 Critical — Security (audit 2026-04-18)

Verifikasi dulu mana yang sudah di-patch sebelum mulai kerja. Lihat juga memori `project_security_audit.md`.

- [x] **#1 Default secret key & admin password fallback** — fixed `d4d8088`
  - File: `web/__init__.py`, `web/auth.py`
  - Solusi: raise RuntimeError kalau env kosong (fail-loud), pesan kasih command untuk generate.
  - ⚠️ **Action item kamu**: rotate `DASHBOARD_SECRET_KEY` ke nilai random 32-byte. Sekarang masih 14 char weak.
    ```bash
    py -c "import secrets; print(secrets.token_hex(32))"
    # copy output, paste ke .env DASHBOARD_SECRET_KEY=...
    ```

- [ ] **#2 CSRF protection di semua form POST**
  - Affected: `/login`, `/portal/login`, semua POST di transactions/customers/withdraw/profit/promos
  - Fix: `Flask-WTF` atau `flask-seasurf`. Tambahkan `{{ csrf_token() }}` ke semua form template.
  - Risk: PR besar — bertahap per blueprint, atau global setting + opt-out per endpoint.

- [x] **#3 Admin password compare plain-text** — fixed
  - File: `web/auth.py`, `web/routes/home.py`
  - Solusi: ganti `DASHBOARD_PASSWORD` plain → `DASHBOARD_PASSWORD_HASH` (pbkdf2:sha256, 1M iter). Pakai `werkzeug.security.check_password_hash` (built-in constant-time).
  - Rate limit (terpisah, masih open di #5 di bawah).

- [x] **#4 Session cookie flags absent** — fixed `d4d8088`
  - File: `web/__init__.py`
  - SECURE conditional pada `DEBUG` env (True kalau prod via Cloudflare HTTPS, False di dev).
  - HTTPONLY=True, SAMESITE='Lax' selalu aktif.

- [ ] **#5 Rate limit di `/login` & `/portal/login`**
  - Fix: `Flask-Limiter` dengan limit misal `5/minute per IP` untuk login endpoints.
  - Test: brute-force script harus kena 429.

---

## 🟠 High Priority — Operational

- [ ] **Bot Telegram jarang nyala — bikin auto-start di Windows**
  - Status: jalan di laptop owner yang sama dengan web, tapi cuma dinyalakan manual.
  - Opsi (pilih satu):
    - **Windows Task Scheduler** — trigger "At log on" → `python run_bot.py`. Paling gampang, no extra tool.
    - **NSSM** (Non-Sucking Service Manager) — wrap `run_bot.py` jadi Windows Service. Auto-restart kalau crash. Recommended.
    - **PowerShell startup script** — taruh di Startup folder, sederhana tapi log management manual.
  - Sebelum auto-start: pastikan log rotation di place (lihat item logging di bawah).
  - Bukan target deploy ke cloud — single-host adalah keputusan desain.

- [ ] **`.env.example` masih punya legacy var**
  - File: `.env.example`
  - Hapus: `AUTHORIZED_CAPSTERS` (bot lama), `GOOGLE_SHEET_ID`, `GEMINI_API_KEY`, `DB_DUAL_WRITE`, `DB_ONLY`
  - Tambah deskripsi WHY untuk yang baru.

- [ ] **`docs/` masih versi v1 (Google Sheets era)**
  - File: `docs/SETUP.md`, `docs/DEPLOYMENT.md`, `docs/API.md`
  - Aksi: hapus + redirect ke `README.md` + `ARCHITECTURE.md`, atau tulis ulang.
  - Rekomendasi: hapus saja, info sudah ada di root docs baru.

- [ ] **Backup DB otomatis harian (PowerShell Task Scheduler)**
  - Single-host → kalau laptop rusak / DB corrupt, data hilang.
  - Setup: scheduled task harian jam 02:00 → `pg_dump` ke `backups/auto_YYYYMMDD.sql`.
  - Retention: simpan 30 hari terakhir, sisanya autodelete.
  - Bonus: sync ke OneDrive / cloud storage lain untuk off-site copy.

- [ ] **Cloudflare Tunnel jalan sebagai Windows service**
  - Kalau belum: `cloudflared service install` supaya tunnel auto-start saat boot.
  - Verify: reboot laptop → URL publik harus tetap reachable tanpa intervensi manual.

- [ ] **GitHub Actions: tambah CI lint + test (opsional)**
  - File: `.github/workflows/ci.yml` (baru — folder sudah dihapus karena Azure deploy legacy juga dibuang)
  - Jalankan: `py_compile` semua file, `ruff check`, `pytest` (kalau sudah ada test).
  - Trigger: PR ke `dev`, `staging`, `main`.
  - Catatan: bukan untuk deploy (production = local), murni untuk catch bug sebelum merge.

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
- Critical: ☑ 3 / ☐ 2 (sisa: #2 CSRF, #5 rate limit)
- High: ☐ 6
- Medium: ☐ 6
- Low: ☐ 5

Total: **22 item** (3 selesai).

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
