"""Customer management routes."""
import hmac as _hmac
import hashlib
import os
import re

import requests as _requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, abort, jsonify

from web.auth import login_required
from app.db.repository import Repository
from app.utils.phone import normalize_id_phone, display_id_phone, wa_me_url

_QR_SECRET = os.getenv('SECRET_KEY', 'barbershop-qr-secret-2026')

# Phone hanya boleh digit, +, -, spasi. Anti stored XSS via nomor HP.
_PHONE_RE = re.compile(r'^[\d\+\-\s]{0,30}$')


def _is_valid_phone(phone: str) -> bool:
    """Return True kalau phone kosong atau match format aman (digit/+-space, max 30)."""
    return not phone or bool(_PHONE_RE.match(phone))


def _qr_token(cid: int) -> str:
    return _hmac.new(_QR_SECRET.encode(), f"qr-{cid}".encode(), hashlib.sha256).hexdigest()[:24]

customers_bp = Blueprint('customers', __name__)


def _auto_send_welcome_wa(cid: int, name: str, phone: str, repo: Repository) -> tuple:
    """Kirim WA selamat datang + link QR otomatis setelah customer baru ditambahkan.
    Returns (ok: bool, message: str).
    """
    if not phone:
        return False, 'no_phone'

    if repo.get_setting('wa_auto_send', '0') != '1':
        return False, 'disabled'

    fonnte_token = repo.get_setting('fonnte_token', '')
    if not fonnte_token:
        return False, 'no_token'

    clean_phone = normalize_id_phone(phone)

    template = repo.get_setting(
        'wa_template',
        'Halo {nama}, selamat datang di barbershop kami! Berikut QR Code membership kamu. Tunjukkan saat kunjungan ya! ✂️',
    )
    message = template.replace('{nama}', name).replace('{kunjungan}', '1')

    # Simpan QR ke file statis
    from flask import current_app
    png_bytes = repo.generate_customer_qr_png(cid)
    qr_dir = os.path.join(current_app.static_folder, 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    with open(os.path.join(qr_dir, f'member_{cid}.png'), 'wb') as f:
        f.write(png_bytes)

    app_base_url = (
        repo.get_setting('app_base_url', '')
        or os.getenv('APP_BASE_URL', '').rstrip('/')
        or f"{request.headers.get('X-Forwarded-Proto', request.scheme)}://{request.host}"
    )
    qr_url = f"{app_base_url.rstrip('/')}/static/qr/member_{cid}.png"
    full_message = f"{message}\n\n🔗 QR Code kamu:\n{qr_url}"

    try:
        resp = _requests.post(
            'https://api.fonnte.com/send',
            headers={'Authorization': fonnte_token},
            data={'target': clean_phone, 'message': full_message},
            timeout=30,
        )
        result = resp.json()
        if result.get('status'):
            return True, f'WA terkirim ke {name} ({clean_phone})'
        return False, f'Gagal kirim WA: {result.get("reason", str(result))}'
    except Exception as e:
        return False, f'Error koneksi WA: {e}'


@customers_bp.route('/customers')
@login_required
def customers_list():
    repo = Repository()
    all_customers = repo.get_all_customers()
    all_capsters  = repo.get_all_capsters()

    search = request.args.get('q', '').strip().lower()
    total_all = len(all_customers)   # sebelum filter — untuk "Menampilkan X dari Y"

    if search:
        all_customers = [
            c for c in all_customers
            if search in c['Name'].lower() or search in c['Phone'].lower()
        ]
    total_filtered = len(all_customers)

    # ── Paginasi server-side ──
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = int(request.args.get('per_page', 50))
    except (ValueError, TypeError):
        per_page = 50
    per_page = min(max(per_page, 10), 200)

    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_customers = all_customers[start:start + per_page]

    # Enrich display phone + wa link untuk template
    for c in page_customers:
        raw = c.get('Phone', '') or ''
        c['PhoneDisplay'] = display_id_phone(raw) if raw else ''
        c['PhoneWaUrl']   = wa_me_url(raw)

    wa_settings = {
        'fonnte_token': repo.get_setting('fonnte_token'),
        'wa_template':  repo.get_setting(
            'wa_template',
            'Halo {nama}, selamat datang di barbershop kami! Berikut QR Code membership kamu. Tunjukkan saat kunjungan ya! ✂️'
        ),
        'app_base_url':  repo.get_setting('app_base_url'),
        'wa_auto_send':  repo.get_setting('wa_auto_send', '0'),
    }

    return render_template(
        'customers.html',
        customers=page_customers,
        capsters=all_capsters,
        search=search,
        total_all=total_all,
        total_filtered=total_filtered,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        wa_settings=wa_settings,
        active_page='customers',
    )


@customers_bp.route('/customers/check-phone')
@login_required
def customers_check_phone():
    """AJAX endpoint: cek apakah nomor sudah terdaftar. Return JSON."""
    raw = request.args.get('phone', '').strip()
    normalized = normalize_id_phone(raw)
    if not normalized:
        return jsonify({'valid': False, 'reason': 'empty'})
    repo = Repository()
    dup = repo.get_customer_by_phone(normalized)
    if not dup:
        # Coba raw (data lama belum di-normalize)
        dup = repo.get_customer_by_phone(raw)
    return jsonify({
        'valid': True,
        'normalized': normalized,
        'display':    display_id_phone(normalized),
        'exists':     bool(dup),
        'existing':   {
            'id':      dup['id'],
            'name':    dup['Name'],
            'visits':  dup.get('VisitCount', 0),
        } if dup else None,
    })


@customers_bp.route('/customers/add', methods=['POST'])
@login_required
def customer_add():
    name = request.form.get('name', '').strip()
    phone_raw = request.form.get('phone', '').strip()

    if not name:
        flash('Nama customer wajib diisi.', 'danger')
        return redirect(url_for('customers.customers_list'))

    if not _is_valid_phone(phone_raw):
        flash('Nomor HP tidak valid. Hanya boleh angka, +, -, dan spasi (maks 30 karakter).', 'danger')
        return redirect(url_for('customers.customers_list'))

    # Normalize phone ke format E.164 (628xxx) sebelum simpan/dedup check.
    phone = normalize_id_phone(phone_raw)

    repo = Repository()

    if phone:
        # Dedup check pakai raw + normalized (backward compat data lama)
        dup = repo.get_customer_by_phone(phone) or repo.get_customer_by_phone(phone_raw)
        if dup:
            flash(
                f'Nomor HP {display_id_phone(phone)} sudah terdaftar atas nama "{dup["Name"]}" '
                f'({dup["VisitCount"]} kunjungan). Customer tidak ditambahkan.',
                'warning'
            )
            return redirect(url_for('customers.customers_list'))

    class _C:
        pass

    c = _C()
    c.name = name
    c.phone = phone
    repo.add_customer(c)

    flash(f'Customer "{name}" berhasil ditambahkan.', 'success')

    # Auto kirim WA jika diaktifkan
    if phone:
        added = repo.get_customer_by_phone(phone)
        if added:
            ok, msg = _auto_send_welcome_wa(added['id'], name, phone, repo)
            if ok:
                flash(f'✅ {msg}', 'success')
            elif msg not in ('disabled', 'no_token', 'no_phone'):
                flash(f'⚠️ {msg}', 'warning')

    return redirect(url_for('customers.customers_list'))


@customers_bp.route('/customers/<int:cid>/edit', methods=['POST'])
@login_required
def customer_edit(cid):
    name      = request.form.get('name', '').strip()
    phone_raw = request.form.get('phone', '').strip()
    added_by  = request.form.get('added_by', '').strip()
    visit_count_str = request.form.get('visit_count', '').strip()
    visit_count = int(visit_count_str) if visit_count_str.isdigit() else None
    point_balance_str = request.form.get('point_balance', '').strip()
    point_balance = int(point_balance_str) if point_balance_str.isdigit() else None

    if not name:
        flash('Nama customer wajib diisi.', 'danger')
        return redirect(url_for('customers.customers_list'))

    if not _is_valid_phone(phone_raw):
        flash('Nomor HP tidak valid. Hanya boleh angka, +, -, dan spasi (maks 30 karakter).', 'danger')
        return redirect(url_for('customers.customers_list'))

    # Normalize phone ke format E.164 (628xxx) — konsisten dgn add.
    phone = normalize_id_phone(phone_raw)

    repo = Repository()
    ok = repo.update_customer(cid, name, phone, added_by=added_by,
                              visit_count=visit_count, point_balance=point_balance)

    if ok:
        flash(f'Customer "{name}" berhasil diupdate.', 'success')
    else:
        flash('Customer tidak ditemukan.', 'danger')
    return redirect(url_for('customers.customers_list'))


@customers_bp.route('/customers/<int:cid>/loyalty')
@login_required
def customer_loyalty(cid):
    """Halaman audit log perubahan poin untuk satu customer."""
    repo = Repository()
    customer = repo.get_customer_by_id(cid)
    if not customer:
        flash('Customer tidak ditemukan.', 'danger')
        return redirect(url_for('customers.customers_list'))
    audit = repo.get_loyalty_audit(cid, limit=200)
    return render_template(
        'customer_loyalty.html',
        customer=customer,
        audit=audit,
        active_page='customers',
    )


@customers_bp.route('/customers/<int:cid>/qr.png')
@login_required
def customer_qr(cid):
    repo = Repository()
    png  = repo.generate_customer_qr_png(cid)
    return Response(png, mimetype='image/png')


@customers_bp.route('/qr-public/<int:cid>')
def customer_qr_public(cid):
    """Public QR endpoint — no login, secured with HMAC token."""
    t = request.args.get('t', '')
    if not _hmac.compare_digest(t, _qr_token(cid)):
        abort(403)
    repo = Repository()
    png = repo.generate_customer_qr_png(cid)
    return Response(png, mimetype='image/png')


@customers_bp.route('/customers/<int:cid>/send-qr', methods=['POST'])
@login_required
def customer_send_qr(cid):
    repo = Repository()
    customers = repo.get_all_customers()
    cust = next((c for c in customers if c['id'] == cid), None)

    if not cust:
        flash('Customer tidak ditemukan.', 'danger')
        return redirect(url_for('customers.customers_list'))

    phone = normalize_id_phone(cust.get('Phone') or '')
    if not phone:
        flash(f'Customer "{cust["Name"]}" tidak punya nomor HP.', 'warning')
        return redirect(url_for('customers.customers_list'))

    fonnte_token = repo.get_setting('fonnte_token')
    if not fonnte_token:
        flash('Token Fonnte belum diset. Isi dulu di Pengaturan WA.', 'warning')
        return redirect(url_for('customers.customers_list'))

    template = repo.get_setting(
        'wa_template',
        'Halo {nama}, berikut QR Code membership kamu di barbershop kami. Tunjukkan saat datang ya! ✂️'
    )
    message = template.replace('{nama}', cust['Name']).replace('{kunjungan}', str(cust.get('VisitCount', 0)))

    # Simpan QR ke file statis agar URL-nya bersih & bisa diakses Fonnte
    from flask import current_app
    png_bytes = repo.generate_customer_qr_png(cid)
    qr_dir  = os.path.join(current_app.static_folder, 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    qr_file = os.path.join(qr_dir, f'member_{cid}.png')
    with open(qr_file, 'wb') as f:
        f.write(png_bytes)

    app_base_url = (
        repo.get_setting('app_base_url')
        or os.getenv('APP_BASE_URL', '').rstrip('/')
        or f"{request.headers.get('X-Forwarded-Proto', request.scheme)}://{request.host}"
    )
    qr_url = f"{app_base_url.rstrip('/')}/static/qr/member_{cid}.png"

    # Sisipkan link QR langsung di dalam teks pesan
    full_message = f"{message}\n\n🔗 QR Code kamu:\n{qr_url}"

    try:
        resp = _requests.post(
            'https://api.fonnte.com/send',
            headers={'Authorization': fonnte_token},
            data={'target': phone, 'message': full_message},
            timeout=30,
        )
        result = resp.json()
        if result.get('status'):
            flash(f'QR berhasil dikirim ke {cust["Name"]} ({phone}).', 'success')
        else:
            flash(f'Gagal kirim: {result.get("reason", str(result))}', 'danger')
    except Exception as e:
        flash(f'Error koneksi ke Fonnte: {e}', 'danger')

    return redirect(url_for('customers.customers_list'))


@customers_bp.route('/customers/wa-settings', methods=['POST'])
@login_required
def save_wa_settings():
    repo = Repository()
    repo.set_setting('fonnte_token',  request.form.get('fonnte_token', '').strip())
    repo.set_setting('wa_template',   request.form.get('wa_template', '').strip())
    repo.set_setting('app_base_url',  request.form.get('app_base_url', '').strip())
    repo.set_setting('wa_auto_send',  '1' if request.form.get('wa_auto_send') else '0')
    flash('Pengaturan WA disimpan.', 'success')
    return redirect(url_for('customers.customers_list'))


@customers_bp.route('/customers/<int:cid>/delete', methods=['POST'])
@login_required
def customer_delete(cid):
    repo = Repository()
    ok = repo.delete_customer(cid)

    if ok:
        flash('Customer berhasil dihapus.', 'success')
    else:
        flash('Customer tidak ditemukan.', 'danger')
    return redirect(url_for('customers.customers_list'))
