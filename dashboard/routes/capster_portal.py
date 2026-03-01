"""Capster self-service portal — private view per capster."""
from datetime import datetime
from functools import wraps

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify, Response,
)
from werkzeug.security import check_password_hash

from app.db.repository import Repository
from app.config.constants import BRANCHES

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
            session['capster_telegram_id'] = int(capster['TelegramID'])
            session['capster_alias']       = capster['Alias']
            session['capster_type']        = capster['EmploymentType']
            session['capster_rate']        = float(capster['CommissionRate'])
            session['capster_salary']      = int(float(capster['MonthlySalary']))
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

    txs = repo.get_transactions_by_capster_month(
        cap['name'], cap['alias'], year, month
    )
    revenue  = sum(t['price'] for t in txs)
    tx_count = len(txs)

    if cap['type'] == 'mitra':
        earned = int(revenue * cap['rate'])
    else:
        earned = cap['salary']

    # All-time balance
    withdrawals = repo.get_withdrawals(cap['telegram_id'])
    withdrawn_all = sum(int(float(w.get('Amount', 0))) for w in withdrawals)

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

    txs      = repo.get_transactions_by_capster_month(cap['name'], cap['alias'], year, month)
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
        active_page='transactions',
    )


# ── Pendapatan ────────────────────────────────────────────────────────────── #

@capster_portal_bp.route('/earnings')
@capster_login_required
def earnings():
    cap  = _current_capster()
    repo = Repository()
    now  = datetime.now()

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

            if rev == 0 and count == 0:
                continue

            if cap['type'] == 'mitra':
                earned = int(rev * cap['rate'])
            else:
                earned = cap['salary']

            withdrawals = repo.get_withdrawals(cap['telegram_id'])
            withdrawn_month = sum(
                int(float(w.get('Amount', 0)))
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
        total=sum(int(float(r.get('Amount', 0))) for r in records),
        active_page='withdraw',
    )


# ── Profil & Ganti Password ───────────────────────────────────────────────── #

@capster_portal_bp.route('/profile')
@capster_login_required
def profile():
    cap = _current_capster()
    repo = Repository()
    now  = datetime.now()
    capster_data = repo.get_capster_by_username(
        next(
            (c['Username'] for c in repo.get_all_capsters()
             if str(c.get('TelegramID')) == str(cap['telegram_id'])),
            ''
        )
    )
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

    if request.method == 'POST':
        name  = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name:
            flash('Nama pengunjung wajib diisi.', 'danger')
            return redirect(url_for('capster_portal.add_customer'))

        class _C:
            pass
        c = _C()
        c.name  = name
        c.phone = phone

        ok = repo.add_customer(c, added_by=cap.get('name', ''))
        if ok:
            # Ambil ID customer yang baru saja ditambahkan
            all_c   = repo.get_all_customers()
            added   = next(
                (x for x in reversed(all_c) if x['Name'] == name), None
            )
            added_id = added['id'] if added else ''
            return redirect(url_for('capster_portal.add_customer', added=added_id))
        else:
            flash('Gagal menambahkan pengunjung.', 'danger')

    return render_template(
        'capster_portal/add_customer.html',
        cap=cap,
        now=now,
        new_customer=new_customer,
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

    services   = repo.get_all_services()
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
        # Ambil cabang: override per-transaksi atau pakai daily branch
        branch = request.form.get('branch_override', '').strip() or daily_branch or ''

        svc = next((s for s in services if s['ServiceID'] == service_id), None)
        if not svc:
            flash('Layanan tidak valid.', 'danger')
            return redirect(url_for('capster_portal.add_transaction'))

        cid = int(customer_id) if customer_id.isdigit() else None

        ok = repo.add_transaction_full(
            date=now,
            capster_name=cap['name'],
            service_name=svc['Name'],
            price=int(svc['Price']),
            payment_method=payment_method,
            branch=branch,
            customer_id=cid,
        )
        if ok:
            return redirect(url_for('capster_portal.add_transaction', success=1))
        else:
            flash('Gagal menyimpan transaksi.', 'danger')

    branch_name = BRANCHES.get(daily_branch, {}).get('name', '') if daily_branch else ''

    return render_template(
        'capster_portal/add_transaction.html',
        cap=cap,
        now=now,
        services=services,
        success=success,
        need_branch=need_branch,
        daily_branch=daily_branch,
        daily_branch_name=branch_name,
        branches=BRANCHES,
        active_page='add_transaction',
    )


@capster_portal_bp.route('/customers')
@capster_login_required
def customers():
    repo  = Repository()
    now   = datetime.now()
    query = request.args.get('q', '').strip()

    results = repo.search_customers(query) if query else []

    return render_template(
        'capster_portal/customers.html',
        cap=_current_capster(),
        now=now,
        query=query,
        results=results,
        active_page='customers',
    )


@capster_portal_bp.route('/customer/lookup')
@capster_login_required
def customer_lookup():
    repo  = Repository()
    query = request.args.get('q', '').strip()
    cid   = request.args.get('id', '').strip()

    if cid.isdigit():
        # Lookup by ID (from QR scan)
        all_c = repo.get_all_customers()
        found = next((c for c in all_c if c['id'] == int(cid)), None)
        if found:
            return jsonify([{
                'id': found['id'], 'name': found['Name'],
                'phone': found['Phone'], 'visits': found['VisitCount'],
            }])
        return jsonify([])

    if len(query) < 1:
        return jsonify([])

    results = repo.search_customers(query)
    return jsonify(results)


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
