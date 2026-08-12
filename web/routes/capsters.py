"""Capster earnings/salary page + CRUD management."""
from datetime import datetime

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash

from web.auth import login_required
from app.db.repository import Repository
from app.config.constants import BRANCHES
from dataclasses import dataclass, field

@dataclass
class CapsterModel:
    name: str
    alias: str = ''
    employment_type: str = 'mitra'
    commission_rate: float = 0.5
    monthly_salary: int = 0
    branch_id: str = ''

capsters_bp = Blueprint('capsters', __name__)


@capsters_bp.route('/capsters')
@login_required
def capsters():
    db  = Repository()
    now = datetime.now()

    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    month_str = f"{year:04d}-{month:02d}"

    # Transactions for the selected month
    year_df   = db.get_transactions_dataframe(year=year)
    month_df  = (
        year_df[year_df['Date'].dt.strftime('%Y-%m') == month_str]
        if not year_df.empty else pd.DataFrame()
    )

    # All transactions across all years (for all-time balance)
    all_years = list(range(2024, now.year + 1))
    all_dfs = []
    for y in all_years:
        if y == year:
            df_y = year_df  # reuse already-fetched df
        else:
            df_y = db.get_transactions_dataframe(year=y)
        if not df_y.empty:
            all_dfs.append(df_y)
    all_time_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    # All capsters
    raw_capsters = db.get_all_capsters()

    # Build per-capster stats
    cap_stats = []
    for c in raw_capsters:
        name      = c.get('Name', '')
        alias     = c.get('Alias', '')
        etype     = (c.get('EmploymentType') or 'mitra').lower()
        rate      = c.get('CommissionRate', 0.5)
        salary    = c.get('MonthlySalary', 0)
        branch_id = c.get('BranchID', '') or ''
        branch_name = BRANCHES.get(branch_id, {}).get('name', branch_id) if branch_id else '-'

        # Match transactions by name or alias
        names_lower = {name.lower()}
        if alias:
            names_lower.add(alias.lower())

        # ── This month ──────────────────────────────────────────────
        if not month_df.empty and 'Capster' in month_df.columns:
            cap_df   = month_df[month_df['Capster'].str.lower().isin(names_lower)]
            revenue  = int(cap_df['Price'].sum()) if not cap_df.empty else 0
            tx_count = len(cap_df)
        else:
            revenue  = 0
            tx_count = 0

        if etype == 'mitra':
            earned = int(revenue * rate)
            pay_info = f"Komisi {int(rate*100)}%"
        else:
            earned   = salary
            pay_info = f"Tetap Rp {salary:,}".replace(',', '.')

        # ── All-time earned (for saldo) ─────────────────────────────
        if not all_time_df.empty and 'Capster' in all_time_df.columns:
            cap_all_df = all_time_df[all_time_df['Capster'].str.lower().isin(names_lower)]
        else:
            cap_all_df = pd.DataFrame()

        if etype == 'mitra':
            revenue_all   = int(cap_all_df['Price'].sum()) if not cap_all_df.empty else 0
            earned_all    = int(revenue_all * rate)
        else:
            # Count distinct YYYY-MM months that have any transaction for this capster
            if not cap_all_df.empty and 'Date' in cap_all_df.columns:
                distinct_months = cap_all_df['Date'].dt.strftime('%Y-%m').nunique()
            else:
                distinct_months = 0
            earned_all = distinct_months * salary

        # ── Withdrawals ─────────────────────────────────────────────
        withdrawals = db.get_withdrawals(c.get('id', 0))
        withdrawn_month = 0
        withdrawn_all   = 0
        for w in withdrawals:
            amt = w.get('Amount', 0)
            withdrawn_all += amt
            w_date = str(w.get('Date', ''))[:7]  # 'YYYY-MM'
            if w_date == month_str:
                withdrawn_month += amt

        product_commission = db.get_product_sales_commission_total(name)
        saldo_adj = int(c.get('SaldoAdjustment', 0) or 0)
        balance = earned_all + product_commission - withdrawn_all + saldo_adj

        cap_stats.append({
            'id':               c.get('id', 0),
            'name':             name,
            'alias':            alias,
            'type':             etype,
            'pay_info':         pay_info,
            'branch_name':      branch_name,
            'branch_id':        branch_id,
            'commission_rate':  rate,
            'monthly_salary':   salary,
            'saldo_adjustment': saldo_adj,
            'revenue':          revenue,
            'tx_count':         tx_count,
            'earned':           earned,          # this month
            'withdrawn':        withdrawn_month, # this month
            'withdrawn_all':    withdrawn_all,   # all time
            'balance':          balance,         # all time
        })

    # Sort: by revenue desc
    cap_stats.sort(key=lambda x: x['revenue'], reverse=True)

    months = [
        {'value': m, 'label': datetime(2000, m, 1).strftime('%B')}
        for m in range(1, 13)
    ]
    years = list(range(2024, now.year + 1))

    return render_template(
        'capsters.html',
        cap_stats=cap_stats,
        year=year,
        month=month,
        month_name=datetime(year, month, 1).strftime('%B %Y'),
        months=months,
        years=years,
        active_page='capsters',
    )


# ── CRUD Management ────────────────────────────────────────────────────────────

@capsters_bp.route('/capsters/manage')
@login_required
def capster_manage():
    db  = Repository()
    raw = db.get_all_capsters()
    capsters = []
    for c in raw:
        etype  = (c.get('EmploymentType') or 'mitra').lower()
        rate   = c.get('CommissionRate', 0.5)
        salary = c.get('MonthlySalary', 0)
        bid    = c.get('BranchID', '') or ''
        bname = BRANCHES.get(bid, {}).get('name', bid) if bid else '-'
        capsters.append({
            'id':               c.get('id', 0),
            'name':             c.get('Name', ''),
            'alias':            c.get('Alias', ''),
            'type':             etype,
            'commission_pct':   int(rate * 100),
            'monthly_salary':   salary,
            'saldo_adjustment': int(c.get('SaldoAdjustment', 0) or 0),
            'branch_id':        bid,
            'branch_name':      bname,
            'username':         c.get('Username', ''),
        })
    return render_template(
        'capster_manage.html',
        capsters=capsters,
        branches=BRANCHES,
        active_page='capster_manage',
        now=datetime.now(),
    )


@capsters_bp.route('/capsters/add', methods=['POST'])
@login_required
def capster_add():
    db   = Repository()
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nama capster tidak boleh kosong.', 'danger')
        return redirect(url_for('capsters.capster_manage'))

    alias = request.form.get('alias', '').strip()
    etype = request.form.get('employment_type', 'mitra').strip().lower()
    if etype not in ('mitra', 'tetap'):
        etype = 'mitra'

    commission_rate = 0.5  # komisi per layanan, bukan per capster

    try:
        monthly_salary = int(float(request.form.get('monthly_salary', '0') or '0'))
    except (ValueError, TypeError):
        monthly_salary = 0

    branch_id = request.form.get('branch_id', '').strip()
    if branch_id and branch_id not in BRANCHES:
        branch_id = ''

    capster = CapsterModel(
        name=name,
        alias=alias,
        employment_type=etype,
        commission_rate=commission_rate,
        monthly_salary=monthly_salary,
        branch_id=branch_id,
    )
    if db.add_capster(capster) is not None:
        flash(f"Capster '{name}' berhasil ditambahkan.", 'success')
    else:
        flash('Gagal menambahkan capster.', 'danger')
    return redirect(url_for('capsters.capster_manage'))


@capsters_bp.route('/capsters/edit/<int:capster_id>', methods=['POST'])
@login_required
def capster_edit(capster_id):
    db = Repository()

    name = request.form.get('name', '').strip() or None
    alias = request.form.get('alias', '').strip()   # '' = clear alias

    etype = request.form.get('employment_type', '').strip().lower()
    etype = etype if etype in ('mitra', 'tetap') else None

    commission_rate = None  # komisi per layanan, tidak di-update dari sini

    try:
        monthly_salary = int(float(request.form.get('monthly_salary', '0') or '0'))
    except (ValueError, TypeError):
        monthly_salary = None

    branch_id = request.form.get('branch_id', '').strip()
    if branch_id and branch_id not in BRANCHES:
        branch_id = ''

    # Saldo adjustment — bisa negatif (mis. koreksi setelah switch tipe)
    raw_adj = request.form.get('saldo_adjustment', '').strip()
    if raw_adj == '':
        saldo_adjustment = None  # jangan overwrite
    else:
        try:
            saldo_adjustment = int(float(raw_adj.replace('.', '').replace(',', '')))
        except (ValueError, TypeError):
            saldo_adjustment = None

    if db.update_capster(
        capster_id,
        name=name,
        alias=alias,
        employment_type=etype,
        commission_rate=commission_rate,
        monthly_salary=monthly_salary,
        branch_id=branch_id,
        saldo_adjustment=saldo_adjustment,
    ):
        flash('Capster berhasil diperbarui.', 'success')
    else:
        flash('Gagal memperbarui capster.', 'danger')
    return redirect(url_for('capsters.capster_manage'))


@capsters_bp.route('/capsters/<int:capster_id>/set-password', methods=['POST'])
@login_required
def capster_set_password(capster_id):
    db       = Repository()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password:
        flash('Username dan password wajib diisi.', 'danger')
        return redirect(url_for('capsters.capster_manage'))

    if len(password) < 6:
        flash('Password minimal 6 karakter.', 'danger')
        return redirect(url_for('capsters.capster_manage'))

    ok, err = db.set_capster_credentials(capster_id, username, password)
    if ok:
        flash(f'Akun portal untuk capster berhasil diset. Username: {username}', 'success')
    else:
        flash(err or 'Gagal menyimpan akun.', 'danger')
    return redirect(url_for('capsters.capster_manage'))


@capsters_bp.route('/capsters/delete/<int:capster_id>', methods=['POST'])
@login_required
def capster_delete(capster_id):
    db = Repository()
    name = next(
        (c['Name'] for c in db.get_all_capsters() if c.get('id') == capster_id),
        'Unknown',
    )
    if db.remove_capster(capster_id):
        flash(f"Capster '{name}' berhasil dihapus.", 'success')
    else:
        flash('Gagal menghapus capster.', 'danger')
    return redirect(url_for('capsters.capster_manage'))
