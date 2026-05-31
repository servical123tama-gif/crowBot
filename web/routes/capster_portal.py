"""Capster self-service portal — private view per capster."""
import logging
from datetime import datetime
from functools import wraps

import pandas as pd

logger = logging.getLogger(__name__)
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, Response,
)
from werkzeug.security import check_password_hash

from app.db.repository import Repository
from app.config.constants import BRANCHES
from web import limiter
from web.routes.customers import _auto_send_welcome_wa

capster_portal_bp = Blueprint('capster_portal', __name__, url_prefix='/portal')

MONTHS_ID = {
    1:'Januari', 2:'Februari', 3:'Maret', 4:'April',
    5:'Mei', 6:'Juni', 7:'Juli', 8:'Agustus',
    9:'September', 10:'Oktober', 11:'November', 12:'Desember',
}


def capster_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('capster_logged_in'):
            return redirect(url_for('capster_portal.login'))
        return f(*args, **kwargs)
    return decorated


def _current_capster():
    return {
        'name':      session.get('capster_name', ''),
        'telegram_id': session.get('capster_telegram_id'),
        'alias':     session.get('capster_alias', ''),
        'type':      session.get('capster_type', 'mitra'),
        'rate':      session.get('capster_rate', 0.5),
        'salary':    session.get('capster_salary', 0),
        'branch_id': session.get('capster_branch_id', ''),
    }


def _capster_names(cap):
    """Return set of lowercased names to match transactions."""
    names = {cap['name'].lower()}
    if cap['alias']:
        names.add(cap['alias'].lower())
    return names


# ── Login / Logout ────────────────────────────────────────────────────────── #

@capster_portal_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'], error_message='Terlalu banyak percobaan login. Coba lagi dalam 1 menit.')
def login():
    if session.get('capster_logged_in'):
        return redirect(url_for('capster_portal.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        repo = Repository()
        capster = repo.verify_capster_login(username, password)
        if capster:
            session['capster_logged_in']   = True
            session['capster_name']        = capster['Name']
            session['capster_telegram_id'] = capster['TelegramID']
            session['capster_alias']       = capster['Alias']
            session['capster_type']        = capster['EmploymentType']
            session['capster_rate']        = capster['CommissionRate']
            session['capster_salary']      = capster['MonthlySalary']
            session['capster_branch_id']   = capster['BranchID']
            return redirect(url_for('capster_portal.dashboard'))
        else:
            error = 'Username atau password salah.'

    return render_template('capster_login.html', error=error)


@capster_portal_bp.route('/logout')
def logout():
    keys = [k for k in session if k.startswith('capster_')]
    for k in keys:
        session.pop(k, None)
    return redirect(url_for('capster_portal.login'))


# ── Dashboard ─────────────────────────────────────────────────────────────── #

@capster_portal_bp.route('/')
@capster_login_required
def dashboard():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()
    year, month = now.year, now.month

    # Ambil salary/rate terbaru dari DB
    all_caps  = repo.get_all_capsters()
    fresh_cap = next((c for c in all_caps if c.get('TelegramID') == cap['telegram_id']), None)
    if fresh_cap:
        cap = dict(cap)
        cap['salary'] = fresh_cap.get('MonthlySalary', cap['salary'])
        cap['rate']   = fresh_cap.get('CommissionRate', cap['rate'])

    txs = repo.get_transactions_by_capster_month(
        cap['name'], cap['alias'], year, month
    )
    svc_revenue = sum(t['price'] for t in txs)

    prod_sales  = repo.get_product_sales_by_capster_month(cap['name'], cap['alias'], year, month)
    prod_revenue     = sum(s['price'] for s in prod_sales)
    prod_commission  = sum(s.get('commission', 0) for s in prod_sales)

    revenue  = svc_revenue + prod_revenue
    tx_count = len(txs) + len(prod_sales)

    if cap['type'] == 'mitra':
        earned = int(svc_revenue * cap['rate']) + prod_commission
    else:
        earned = cap['salary'] + prod_commission

    # All-time balance
    withdrawals = repo.get_withdrawals(cap['telegram_id'])
    withdrawn_all = sum(w.get('Amount', 0) for w in withdrawals)

    all_years = list(range(2024, now.year + 1))
    earned_all = 0
    for y in all_years:
        df_y = repo.get_transactions_dataframe(year=y)
        if not df_y.empty and 'Capster' in df_y.columns:
            names = _capster_names(cap)
            cap_df = df_y[df_y['Capster'].str.lower().isin(names)]
            if cap['type'] == 'mitra':
                earned_all += int(cap_df['Price'].sum() * cap['rate'])
            else:
                months_worked = cap_df['Date'].dt.strftime('%Y-%m').nunique() if not cap_df.empty else 0
                earned_all += months_worked * cap['salary']
    # Tambah komisi produk all-time
    earned_all += repo.get_product_sales_commission_total(cap['name'])

    balance = earned_all - withdrawn_all

    return render_template(
        'capster_portal/dashboard.html',
        cap=cap,
        now=now,
        month_name=f"{MONTHS_ID[month]} {year}",
        revenue=revenue,
        tx_count=tx_count,
        earned=earned,
        balance=balance,
        recent_txs=txs[:10],
        branch_name=BRANCHES.get(cap['branch_id'], {}).get('name', cap['branch_id'] or '-'),
        branches=BRANCHES,
        active_page='dashboard',
    )


# ── Transaksi ─────────────────────────────────────────────────────────────── #

@capster_portal_bp.route('/transactions')
@capster_login_required
def transactions():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()

    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))

    txs_service = repo.get_transactions_by_capster_month(cap['name'], cap['alias'], year, month)
    for t in txs_service:
        t.setdefault('type', 'layanan')

    txs_product = repo.get_product_sales_by_capster_month(cap['name'], cap['alias'], year, month)

    txs      = sorted(txs_service + txs_product, key=lambda t: t['date'], reverse=True)
    revenue  = sum(t['price'] for t in txs)
    tx_count = len(txs)

    months = [{'value': m, 'label': MONTHS_ID[m]} for m in range(1, 13)]
    years  = list(range(2024, now.year + 1))

    return render_template(
        'capster_portal/transactions.html',
        cap=cap,
        now=now,
        txs=txs,
        revenue=revenue,
        tx_count=tx_count,
        year=year,
        month=month,
        month_name=f"{MONTHS_ID[month]} {year}",
        months=months,
        years=years,
        branches=BRANCHES,
        active_page='transactions',
    )


# ── Pendapatan ────────────────────────────────────────────────────────────── #

@capster_portal_bp.route('/earnings')
@capster_login_required
def earnings():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()

    # Ambil salary/rate terbaru dari DB (bukan dari session yang bisa stale)
    all_caps   = repo.get_all_capsters()
    fresh_cap  = next((c for c in all_caps if c.get('TelegramID') == cap['telegram_id']), None)
    if fresh_cap:
        cap = dict(cap)
        cap['salary'] = fresh_cap.get('MonthlySalary', cap['salary'])
        cap['rate']   = fresh_cap.get('CommissionRate', cap['rate'])

    # Ambil withdrawals sekali di luar loop (bug fix: sebelumnya dipanggil tiap iterasi)
    withdrawals = repo.get_withdrawals(cap['telegram_id'])

    monthly_stats = []
    for year in range(2024, now.year + 1):
        df_y = repo.get_transactions_dataframe(year=year)
        for month in range(1, 13):
            if year == now.year and month > now.month:
                break
            month_str = f"{year:04d}-{month:02d}"
            if not df_y.empty and 'Capster' in df_y.columns:
                names  = _capster_names(cap)
                mdf    = df_y[df_y['Date'].dt.strftime('%Y-%m') == month_str]
                cap_df = mdf[mdf['Capster'].str.lower().isin(names)]
                rev    = int(cap_df['Price'].sum()) if not cap_df.empty else 0
                count  = len(cap_df)
            else:
                rev, count = 0, 0

            # Komisi produk bulan ini
            prod_sales_month = repo.get_product_sales_by_capster_month(
                cap['name'], cap['alias'], year, month
            )
            prod_commission_month = sum(s.get('commission', 0) for s in prod_sales_month)

            if rev == 0 and count == 0 and prod_commission_month == 0:
                continue

            if cap['type'] == 'mitra':
                earned = int(rev * cap['rate']) + prod_commission_month
            else:
                earned = cap['salary'] + prod_commission_month

            withdrawn_month = sum(
                w.get('Amount', 0)
                for w in withdrawals
                if str(w.get('Date', ''))[:7] == month_str
            )

            monthly_stats.append({
                'month_str': month_str,
                'label':     f"{MONTHS_ID[month]} {year}",
                'revenue':   rev,
                'count':     count,
                'earned':    earned,
                'withdrawn': withdrawn_month,
                'saldo':     earned - withdrawn_month,
            })

    monthly_stats.reverse()

    total_earned    = sum(s['earned']    for s in monthly_stats)
    total_withdrawn = sum(s['withdrawn'] for s in monthly_stats)
    total_balance   = total_earned - total_withdrawn

    return render_template(
        'capster_portal/earnings.html',
        cap=cap,
        now=now,
        monthly_stats=monthly_stats,
        total_earned=total_earned,
        total_withdrawn=total_withdrawn,
        total_balance=total_balance,
        active_page='earnings',
    )


# ── Withdraw ──────────────────────────────────────────────────────────────── #

@capster_portal_bp.route('/withdraw')
@capster_login_required
def withdraw():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()

    records = repo.get_withdrawals(cap['telegram_id'])

    return render_template(
        'capster_portal/withdraw.html',
        cap=cap,
        now=now,
        records=records,
        total=sum(r.get('Amount', 0) for r in records),
        active_page='withdraw',
    )


# ── Profil & Ganti Password ───────────────────────────────────────────────── #

@capster_portal_bp.route('/profile')
@capster_login_required
def profile():
    cap = _current_capster()
    now  = datetime.now()
    branch_name = BRANCHES.get(cap['branch_id'], {}).get('name', cap['branch_id'] or '-')
    return render_template(
        'capster_portal/profile.html',
        cap=cap,
        now=now,
        branch_name=branch_name,
        active_page='profile',
    )


# ── Tambah Pengunjung (Customer) ─────────────────────────────────────────── #

@capster_portal_bp.route('/add-customer', methods=['GET', 'POST'])
@capster_login_required
def add_customer():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()

    new_customer_id = request.args.get('added', type=int)
    new_customer    = None

    if new_customer_id:
        all_c = repo.get_all_customers()
        new_customer = next(
            (c for c in all_c if c['id'] == new_customer_id), None
        )

    existing_phone_customer = None

    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name:
            flash('Nama pengunjung wajib diisi.', 'danger')
            return redirect(url_for('capster_portal.add_customer'))

        # Cek duplikat nomor HP
        if phone:
            dup = repo.get_customer_by_phone(phone)
            if dup:
                existing_phone_customer = dup
                # Render form lagi dengan notifikasi, biarkan user memutuskan
                return render_template(
                    'capster_portal/add_customer.html',
                    cap=cap,
                    now=now,
                    new_customer=new_customer,
                    existing_phone_customer=existing_phone_customer,
                    prefill_name=name,
                    prefill_phone=phone,
                    active_page='add_customer',
                )

        class _C:
            pass
        c = _C()
        c.name  = name
        c.phone = phone

        ok = repo.add_customer(c, added_by=cap.get('name', ''))
        if ok:
            # Ambil ID customer yang baru saja ditambahkan
            # Prioritas: cari by phone (unik), fallback by nama terbaru
            if phone:
                added = repo.get_customer_by_phone(phone)
            else:
                all_c = repo.get_all_customers()
                added = next(
                    (x for x in reversed(all_c) if x['Name'] == name), None
                )
            added_id = added['id'] if added else ''

            # Auto kirim WA jika diaktifkan
            if phone and added:
                wa_ok, wa_msg = _auto_send_welcome_wa(added['id'], name, phone, repo)
                if wa_ok:
                    flash(f'✅ {wa_msg}', 'success')
                elif wa_msg not in ('disabled', 'no_token', 'no_phone'):
                    flash(f'⚠️ {wa_msg}', 'warning')

            return redirect(url_for('capster_portal.add_customer', added=added_id))
        else:
            flash('Gagal menambahkan pengunjung.', 'danger')

    return render_template(
        'capster_portal/add_customer.html',
        cap=cap,
        now=now,
        new_customer=new_customer,
        existing_phone_customer=None,
        prefill_name='',
        prefill_phone='',
        active_page='add_customer',
    )


# ── Tambah Transaksi ──────────────────────────────────────────────────────── #

@capster_portal_bp.route('/set-daily-branch', methods=['POST'])
@capster_login_required
def set_daily_branch():
    branch_id = request.form.get('branch_id', '').strip()
    if branch_id:
        session['daily_branch']      = branch_id
        session['daily_branch_date'] = datetime.now().strftime('%Y-%m-%d')
    else:
        session.pop('daily_branch', None)
        session.pop('daily_branch_date', None)
    return redirect(url_for('capster_portal.add_transaction'))


@capster_portal_bp.route('/add-transaction', methods=['GET', 'POST'])
@capster_login_required
def add_transaction():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()

    services_raw = repo.get_all_services()
    popularity   = repo.get_service_popularity()
    # Sort by transaction count descending within each category
    services = sorted(
        services_raw,
        key=lambda s: (-popularity.get(s['Name'].lower(), 0), s['Name']),
    )
    success    = request.args.get('success') == '1'
    today_str  = now.strftime('%Y-%m-%d')

    # Cek daily branch — reset jika beda hari
    daily_branch      = session.get('daily_branch')
    daily_branch_date = session.get('daily_branch_date')
    if daily_branch_date != today_str:
        daily_branch = None
        session.pop('daily_branch', None)
        session.pop('daily_branch_date', None)

    need_branch = daily_branch is None

    if request.method == 'POST':
        service_id     = request.form.get('service_id', '').strip()
        payment_method = request.form.get('payment_method', 'Cash').strip()
        customer_id    = request.form.get('customer_id', '').strip()
        new_cust_name  = request.form.get('new_customer_name', '').strip()
        new_cust_phone = request.form.get('new_customer_phone', '').strip()
        promo_id_str   = request.form.get('promo_id', '').strip()
        family_member  = request.form.get('family_member', '').strip()
        family_count   = max(1, int(request.form.get('family_count', '1') or '1'))
        branch         = request.form.get('branch_override', '').strip() or daily_branch or ''
        sold_ids       = request.form.getlist('sell_product')
        use_loyalty    = request.form.get('use_loyalty', '').strip()  # '50pct' | 'free' | ''

        svc = next((s for s in services if s['ServiceID'] == service_id), None)

        # Service optional — validasi hanya jika ada service_id
        if service_id and not svc:
            flash('Layanan tidak valid.', 'danger')
            return redirect(url_for('capster_portal.add_transaction'))

        # Wajib ada minimal layanan ATAU produk
        if not svc and not sold_ids:
            flash('Pilih minimal satu layanan atau produk.', 'danger')
            return redirect(url_for('capster_portal.add_transaction'))

        cid = int(customer_id) if customer_id.isdigit() else None

        # ── Mode "Customer Baru": create customer dulu, pakai ID-nya ────────
        # Trigger: ada new_customer_name DAN tidak ada customer_id pilihan.
        # Cek duplikasi nomor HP supaya tidak double-register.
        if new_cust_name and not cid:
            existing = repo.get_customer_by_phone(new_cust_phone) if new_cust_phone else None
            if existing:
                cid = existing['id']
                flash(f"Nomor HP {new_cust_phone} sudah terdaftar atas nama "
                      f"{existing['Name']} — transaksi dilink ke customer tersebut.", 'info')
            else:
                from types import SimpleNamespace
                new_c = SimpleNamespace(name=new_cust_name, phone=new_cust_phone)
                new_id = repo.add_customer(new_c, added_by=cap.get('name', ''))
                if new_id:
                    cid = new_id
                    # Auto-kirim WA welcome kalau ada nomor HP
                    if new_cust_phone:
                        try:
                            _auto_send_welcome_wa(new_id, new_cust_name, new_cust_phone, repo)
                        except Exception as e:
                            logger.warning(f"Welcome WA gagal: {e}")
                else:
                    flash('Gagal mendaftarkan customer baru. Transaksi tetap dilanjutkan sebagai walk-in.', 'warning')

        # ── Validasi loyalty claim ──
        loyalty_status = repo.get_loyalty_status(cid) if cid else {'point_balance': 0, 'available': []}
        valid_claim_types = {c['type'] for c in loyalty_status['available']}
        if use_loyalty and use_loyalty not in valid_claim_types:
            use_loyalty = ''  # klaim tidak valid / poin tidak cukup

        # ── Simpan transaksi layanan (jika ada) ──────────────────────────
        final_price        = 0
        chosen_promo_name  = None
        commission_preview = 0
        ok_service         = True
        loyalty_label      = None

        if svc:
            service_display_name = svc['Name']
            if family_member:
                service_display_name = f"{svc['Name']} ({family_member})"

            final_price = svc['Price'] * family_count

            # Promo diskon
            if promo_id_str.isdigit():
                all_promos = repo.get_all_promos()
                chosen_promo = next(
                    (p for p in all_promos
                     if p['id'] == int(promo_id_str) and svc['ServiceID'] in p['service_ids']),
                    None
                )
                if chosen_promo:
                    price_per_orang = int(svc['Price'] * (1 - chosen_promo['discount_pct'] / 100))
                    final_price = price_per_orang * family_count
                    chosen_promo_name = chosen_promo['name']

            # Loyalty claim override promo (prioritas lebih tinggi)
            if use_loyalty == 'free':
                final_price   = 0
                loyalty_label = 'Potong Gratis (10 poin)'
                chosen_promo_name = None
            elif use_loyalty == '50pct':
                final_price   = int(final_price * 0.5)
                loyalty_label = 'Diskon 50% (5 poin)'
                chosen_promo_name = None

            ok_service = repo.add_transaction_full(
                date=now,
                capster_name=cap['name'],
                service_name=service_display_name,
                price=final_price,
                payment_method=payment_method,
                branch=branch,
                customer_id=cid,
                promo_name=chosen_promo_name,
            )
            if ok_service:
                commission_preview = int(final_price * cap['rate']) if cap['type'] == 'mitra' else 0
            else:
                flash('Gagal menyimpan transaksi layanan.', 'danger')

        if ok_service:
            # ── Proses penjualan produk (independen dari layanan) ────────
            all_products = repo.get_all_products()
            prod_map = {p['ProductID']: p for p in all_products}
            products_summary = []
            for pid in sold_ids:
                if pid not in prod_map:
                    continue
                try:
                    qty = max(1, int(request.form.get(f'qty_{pid}', 1) or 1))
                except (ValueError, TypeError):
                    qty = 1
                p = prod_map[pid]
                price_each = p.get('Price', 0)
                comm_rate  = p.get('CommissionRate', 0.0)
                prod_comm  = int(price_each * qty * comm_rate)
                repo.add_product_sale(
                    capster_name=cap['name'],
                    product_id=pid,
                    product_name=p['Name'],
                    price_each=price_each,
                    quantity=qty,
                    commission_rate=comm_rate,
                    branch_id=branch,
                )
                products_summary.append({
                    'name':       p['Name'],
                    'qty':        qty,
                    'commission': prod_comm,
                })

            # ── Loyalty: catat klaim atau tambah poin ────────────────────
            # Kalau klaim → poin BERKURANG (subtract threshold). Visit ini tidak +1 poin.
            # Kalau tidak klaim → poin BERTAMBAH +1.
            new_point_balance = None
            if cid and svc:  # poin hanya untuk transaksi layanan
                tx_id = None
                if use_loyalty:
                    try:
                        all_tx = repo.get_transactions_by_customer(cid, limit=1)
                        tx_id = all_tx[0]['id'] if all_tx and 'id' in all_tx[0] else None
                    except Exception:
                        pass
                    new_point_balance = repo.use_loyalty_claim(cid, use_loyalty, transaction_id=tx_id)
                    if new_point_balance is None:
                        # Claim gagal (race condition: poin sudah berkurang sejak validasi)
                        # Fallback: tambah poin normal supaya tidak hilang
                        new_point_balance = repo.add_customer_points(cid, 1)
                        loyalty_label = None  # batalkan label klaim di success page
                else:
                    new_point_balance = repo.add_customer_points(cid, 1)

            session['last_tx'] = {
                'service':           svc['Name'] if svc else None,
                'price':             final_price,
                'payment':           payment_method,
                'branch_name':       BRANCHES.get(branch, {}).get('name', branch or '-'),
                'commission':        commission_preview,
                'products':          products_summary,
                'had_customer':      bool(cid) and bool(svc),
                'promo_name':        chosen_promo_name,
                'loyalty_label':     loyalty_label,
                'new_point_balance': new_point_balance,
            }
            return redirect(url_for('capster_portal.add_transaction', success=1))

    # Pop success summary from session (only available right after redirect)
    last_tx = session.pop('last_tx', None) if success else None

    # Pre-select customer dari halaman tambah pengunjung
    preset_customer = None
    preset_cid = request.args.get('preset_customer', '').strip()
    if preset_cid.isdigit():
        all_c = repo.get_all_customers()
        preset_customer = next((c for c in all_c if c['id'] == int(preset_cid)), None)

    branch_name = BRANCHES.get(daily_branch, {}).get('name', '') if daily_branch else ''

    # Stok produk di branch ini untuk step 4
    products_in_stock = repo.get_product_stocks(branch_id=daily_branch) if daily_branch else []

    # Promo aktif untuk cabang hari ini
    active_promos = repo.get_active_promos_for_branch(daily_branch) if daily_branch else []

    # Pilihan anggota paket (dari setting owner)
    paket_members_raw = repo.get_setting('paket_members', 'Bapak,Anak 1,Anak 2,Anak 3')
    paket_members = [m.strip() for m in paket_members_raw.split(',') if m.strip()]

    return render_template(
        'capster_portal/add_transaction.html',
        cap=cap,
        now=now,
        services=services,
        success=success,
        last_tx=last_tx,
        need_branch=need_branch,
        daily_branch=daily_branch,
        daily_branch_name=branch_name,
        branches=BRANCHES,
        products_in_stock=products_in_stock,
        active_promos=active_promos,
        paket_members=paket_members,
        preset_customer=preset_customer,
        active_page='add_transaction',
    )


@capster_portal_bp.route('/customers')
@capster_login_required
def customers():
    repo  = Repository()
    now   = datetime.now()
    cap   = _current_capster()
    query = request.args.get('q', '').strip()

    if query:
        results      = repo.search_customers(query)
        my_customers = None
    else:
        results      = None
        my_customers = repo.get_customers_by_capster(cap.get('name', ''))

    return render_template(
        'capster_portal/customers.html',
        cap=cap,
        now=now,
        query=query,
        results=results,
        my_customers=my_customers,
        active_page='customers',
    )


@capster_portal_bp.route('/customer/lookup')
@capster_login_required
def customer_lookup():
    repo  = Repository()
    query = request.args.get('q', '').strip()
    cid   = request.args.get('id', '').strip()

    def _loyalty(c):
        status = repo.get_loyalty_status(c['id'])
        return {
            'id':            c['id'],
            'name':          c['Name'],
            'phone':         c['Phone'],
            'visits':        c['VisitCount'],
            'point_balance': status['point_balance'],
            'available':     status['available'],
        }

    if cid.isdigit():
        all_c = repo.get_all_customers()
        found = next((c for c in all_c if c['id'] == int(cid)), None)
        if found:
            return jsonify([_loyalty(found)])
        return jsonify([])

    if len(query) < 1:
        return jsonify([])

    results = repo.search_customers(query)
    return jsonify([_loyalty(c) for c in results])


@capster_portal_bp.route('/customer/<int:cid>/qr.png')
@capster_login_required
def customer_qr(cid):
    repo = Repository()
    png  = repo.generate_customer_qr_png(cid)
    return Response(png, mimetype='image/png')


@capster_portal_bp.route('/profile/password', methods=['POST'])
@capster_login_required
def change_password():
    cap      = _current_capster()
    old_pwd  = request.form.get('old_password', '').strip()
    new_pwd  = request.form.get('new_password', '').strip()
    confirm  = request.form.get('confirm_password', '').strip()

    repo = Repository()

    # Verify old password
    all_caps = repo.get_all_capsters()
    username = next(
        (c['Username'] for c in all_caps
         if str(c.get('TelegramID')) == str(cap['telegram_id'])),
        ''
    )
    capster_auth = repo.get_capster_by_username(username) if username else None
    if not capster_auth or not check_password_hash(capster_auth.get('password_hash', ''), old_pwd):
        flash('Password lama salah.', 'danger')
        return redirect(url_for('capster_portal.profile'))

    if len(new_pwd) < 6:
        flash('Password baru minimal 6 karakter.', 'danger')
        return redirect(url_for('capster_portal.profile'))

    if new_pwd != confirm:
        flash('Konfirmasi password tidak cocok.', 'danger')
        return redirect(url_for('capster_portal.profile'))

    if repo.update_capster_password(cap['telegram_id'], new_pwd):
        flash('Password berhasil diubah.', 'success')
    else:
        flash('Gagal mengubah password.', 'danger')

    return redirect(url_for('capster_portal.profile'))
