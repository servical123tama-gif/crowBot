"""Withdraw capster — tarik saldo + riwayat transaksi withdraw."""
from datetime import datetime

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash

from web.auth import login_required
from app.db.repository import Repository
from app.config.constants import BRANCHES

withdraw_bp = Blueprint('withdraw', __name__)


def _build_capster_balances(db: Repository) -> list:
    """Hitung saldo terkini tiap capster (earned all-time - withdrawn all-time)."""
    now = datetime.now()

    # Semua transaksi dari semua tahun
    all_dfs = []
    for y in range(2024, now.year + 1):
        df_y = db.get_transactions_dataframe(year=y)
        if not df_y.empty:
            all_dfs.append(df_y)
    all_time_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    raw_capsters = db.get_all_capsters()
    result = []

    for c in raw_capsters:
        name        = c.get('Name', '')
        alias       = c.get('Alias', '')
        etype       = (c.get('EmploymentType') or 'mitra').lower()
        rate        = c.get('CommissionRate', 0.5)
        salary      = c.get('MonthlySalary', 0)
        telegram_id = c.get('TelegramID', 0)
        branch_id   = c.get('BranchID', '') or ''
        branch_name = BRANCHES.get(branch_id, {}).get('name', branch_id) if branch_id else '-'

        names_lower = {name.lower()}
        if alias:
            names_lower.add(alias.lower())

        # All-time service earned
        if not all_time_df.empty and 'Capster' in all_time_df.columns:
            cap_df = all_time_df[all_time_df['Capster'].str.lower().isin(names_lower)]
        else:
            cap_df = pd.DataFrame()

        if etype == 'mitra':
            rev_all    = int(cap_df['Price'].sum()) if not cap_df.empty else 0
            earned_all = int(rev_all * rate)
            pay_label  = f"Komisi {int(rate * 100)}%"
        else:
            distinct_months = cap_df['Date'].dt.strftime('%Y-%m').nunique() if (not cap_df.empty and 'Date' in cap_df.columns) else 0
            earned_all = distinct_months * salary
            pay_label  = f"Tetap {salary:,}/bln".replace(',', '.')

        # All-time product commission
        prod_commission = db.get_product_sales_commission_total(name)

        # All-time withdrawn
        withdrawals   = db.get_withdrawals(telegram_id)
        withdrawn_all = sum(w.get('Amount', 0) for w in withdrawals)

        result.append({
            'name':            name,
            'alias':           alias,
            'type':            etype,
            'pay_label':       pay_label,
            'branch_name':     branch_name,
            'telegram_id':     telegram_id,
            'earned_all':      earned_all + prod_commission,
            'withdrawn_all':   withdrawn_all,
            'balance':         earned_all + prod_commission - withdrawn_all,
        })

    result.sort(key=lambda x: x['balance'], reverse=True)
    return result


@withdraw_bp.route('/withdraw')
@login_required
def withdraw_list():
    db  = Repository()
    now = datetime.now()

    capsters     = _build_capster_balances(db)
    all_records  = db.get_all_withdrawals()

    # Filter untuk riwayat
    filter_capster = request.args.get('capster', '').strip()
    filter_month   = request.args.get('month', '').strip()

    records = all_records
    if filter_capster:
        records = [r for r in records if filter_capster.lower() in r['CapsterName'].lower()]
    if filter_month:
        records = [r for r in records if str(r['Date'])[:7] == filter_month]

    total_withdrawn = sum(r.get('Amount', 0) for r in records)
    capster_names   = sorted({r['CapsterName'] for r in all_records})

    return render_template(
        'withdraw.html',
        capsters=capsters,
        records=records,
        total_withdrawn=total_withdrawn,
        capster_names=capster_names,
        filter_capster=filter_capster,
        filter_month=filter_month,
        now=now,
        active_page='withdraw',
    )


@withdraw_bp.route('/withdraw/add', methods=['POST'])
@login_required
def withdraw_add():
    db = Repository()

    capster_name = request.form.get('capster_name', '').strip()
    if not capster_name:
        flash('Pilih capster terlebih dahulu.', 'danger')
        return redirect(url_for('withdraw.withdraw_list'))

    # Cari telegram_id
    telegram_id = 0
    for c in db.get_all_capsters():
        if c['Name'] == capster_name:
            telegram_id = c.get('TelegramID', 0)
            break

    try:
        amount = int(float(request.form.get('amount', '0').replace('.', '').replace(',', '')))
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash('Jumlah withdraw harus lebih dari 0.', 'danger')
        return redirect(url_for('withdraw.withdraw_list'))

    period_start = request.form.get('period_start', '').strip()
    period_end   = request.form.get('period_end', '').strip()
    note         = request.form.get('note', '').strip()

    for label, val in [('Periode mulai', period_start), ('Periode akhir', period_end)]:
        if val:
            try:
                datetime.strptime(val, '%Y-%m-%d')
            except ValueError:
                flash(f"{label}: format tanggal tidak valid.", 'danger')
                return redirect(url_for('withdraw.withdraw_list'))

    if db.add_withdrawal(capster_name, telegram_id, amount, period_start, period_end, note):
        flash(f"Withdraw Rp {amount:,} untuk '{capster_name}' berhasil dicatat.".replace(',', '.'), 'success')
    else:
        flash('Gagal mencatat withdrawal.', 'danger')

    return redirect(url_for('withdraw.withdraw_list'))
