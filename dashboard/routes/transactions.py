"""Transactions table with filters, edit, and delete."""
import io
import csv
from datetime import datetime

from flask import Blueprint, render_template, request, Response, redirect, url_for, flash

from dashboard.auth import login_required
from app.db.repository import Repository
from app.config.constants import ALL_SERVICES, PAYMENT_METHODS, BRANCHES

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/transactions')
@login_required
def transactions():
    db  = Repository()
    now = datetime.now()

    # ── Date range filter ──────────────────────────────────────────
    start_str = request.args.get('start', now.replace(day=1).strftime('%Y-%m-%d'))
    end_str   = request.args.get('end',   now.strftime('%Y-%m-%d'))
    capster_f = request.args.get('capster', '').strip()
    branch_f  = request.args.get('branch', '').strip()

    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d')
        end_dt   = datetime.strptime(end_str,   '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        start_dt = now.replace(day=1)
        end_dt   = now

    df = db.get_transactions_by_range(start_dt, end_dt)

    # Apply filters
    if not df.empty:
        if capster_f and 'Capster' in df.columns:
            df = df[df['Capster'].str.lower().str.contains(capster_f.lower(), na=False)]
        if branch_f and 'Branch' in df.columns:
            df = df[df['Branch'].str.lower().str.contains(branch_f.lower(), na=False)]

    total_revenue  = int(df['Price'].sum())   if not df.empty else 0
    total_count    = len(df)

    # Sort newest first, limit display to 500
    if not df.empty:
        df = df.sort_values('Date', ascending=False).head(500)

    rows = []
    if not df.empty:
        for _, r in df.iterrows():
            rows.append({
                'id':      int(r.get('id', 0)),
                'date':    r['Date'].strftime('%Y-%m-%d %H:%M') if hasattr(r['Date'], 'strftime') else str(r['Date']),
                'date_input': r['Date'].strftime('%Y-%m-%dT%H:%M') if hasattr(r['Date'], 'strftime') else str(r['Date'])[:16],
                'capster': r.get('Capster', '-'),
                'service': r.get('Service', '-'),
                'price':   int(r.get('Price', 0)),
                'payment': r.get('Payment_Method', '-'),
                'branch':  r.get('Branch', '-'),
            })

    # Unique values for filter dropdowns
    all_capsters = sorted(df['Capster'].dropna().unique().tolist()) if not df.empty and 'Capster' in df.columns else []
    all_branches = sorted(df['Branch'].dropna().unique().tolist())  if not df.empty and 'Branch' in df.columns else []

    # Data for edit modal dropdowns
    service_names = sorted({v['name'] for v in ALL_SERVICES.values()})
    payment_names = [v['name'] for v in PAYMENT_METHODS.values()]
    branch_shorts = sorted({cfg.get('short', bid) for bid, cfg in BRANCHES.items()})

    return render_template(
        'transactions.html',
        rows=rows,
        total_revenue=total_revenue,
        total_count=total_count,
        start_str=start_str,
        end_str=end_str,
        capster_f=capster_f,
        branch_f=branch_f,
        all_capsters=all_capsters,
        all_branches=all_branches,
        service_names=service_names,
        payment_names=payment_names,
        branch_shorts=branch_shorts,
        active_page='transactions',
    )


@transactions_bp.route('/transactions/export')
@login_required
def export_csv():
    db  = Repository()
    now = datetime.now()

    start_str = request.args.get('start', now.replace(day=1).strftime('%Y-%m-%d'))
    end_str   = request.args.get('end',   now.strftime('%Y-%m-%d'))

    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d')
        end_dt   = datetime.strptime(end_str,   '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        start_dt = now.replace(day=1)
        end_dt   = now

    df = db.get_transactions_by_range(start_dt, end_dt)
    if not df.empty:
        df = df.sort_values('Date', ascending=False)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tanggal', 'Capster', 'Layanan', 'Harga', 'Pembayaran', 'Cabang'])
    if not df.empty:
        for _, r in df.iterrows():
            writer.writerow([
                r['Date'].strftime('%Y-%m-%d %H:%M') if hasattr(r['Date'], 'strftime') else str(r['Date']),
                r.get('Capster', ''),
                r.get('Service', ''),
                int(r.get('Price', 0)),
                r.get('Payment_Method', ''),
                r.get('Branch', ''),
            ])

    filename = f"transaksi_{start_str}_{end_str}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@transactions_bp.route('/transactions/<int:tx_id>/edit', methods=['POST'])
@login_required
def edit_transaction(tx_id: int):
    db = Repository()

    # Parse form fields
    date_str = request.form.get('date', '').strip()
    capster  = request.form.get('capster', '').strip()
    service  = request.form.get('service', '').strip()
    payment  = request.form.get('payment', '').strip()
    branch   = request.form.get('branch', '').strip()

    try:
        price = int(float(request.form.get('price', '0').replace('.', '').replace(',', '')))
        if price <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash('Harga harus berupa angka lebih dari 0.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    try:
        tx_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Format tanggal tidak valid.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    if not capster or not service or not payment or not branch:
        flash('Semua field wajib diisi.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    if db.update_transaction(tx_id, tx_date, capster, service, price, payment, branch):
        flash(f'Transaksi #{tx_id} berhasil diperbarui.', 'success')
    else:
        flash(f'Transaksi #{tx_id} tidak ditemukan atau gagal diperbarui.', 'danger')

    return redirect(request.referrer or url_for('transactions.transactions'))


@transactions_bp.route('/transactions/<int:tx_id>/delete', methods=['POST'])
@login_required
def delete_transaction(tx_id: int):
    db = Repository()
    if db.delete_transaction(tx_id):
        flash(f'Transaksi #{tx_id} berhasil dihapus.', 'success')
    else:
        flash(f'Transaksi #{tx_id} tidak ditemukan.', 'danger')
    return redirect(request.referrer or url_for('transactions.transactions'))
