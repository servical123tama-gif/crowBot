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
    service_f = request.args.get('service', '').strip()
    type_f    = request.args.get('type', '').strip()   # 'layanan' | 'produk' | ''

    try:
        start_dt = datetime.strptime(start_str, '%Y-%m-%d')
        end_dt   = datetime.strptime(end_str,   '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    except ValueError:
        start_dt = now.replace(day=1)
        end_dt   = now

    # ── Haircut transactions ───────────────────────────────────────
    df = db.get_transactions_by_range(start_dt, end_dt)

    # Save unfiltered service names for datalist BEFORE applying service_f filter
    # so old transaction service names (not in ALL_SERVICES) are still suggested
    df_service_names: set = set()
    if not df.empty and 'Service' in df.columns:
        df_service_names = set(df['Service'].dropna().unique().tolist())

    if not df.empty:
        if capster_f and 'Capster' in df.columns:
            df = df[df['Capster'].str.lower().str.contains(capster_f.lower(), na=False)]
        if branch_f and 'Branch' in df.columns:
            # branch_f may be a short display name (e.g. "Cabang A"); map to branch_id
            short_to_id = {cfg.get('short', bid): bid for bid, cfg in BRANCHES.items()}
            branch_id_f = short_to_id.get(branch_f, branch_f)
            df = df[df['Branch'].str.lower().str.contains(branch_id_f.lower(), na=False)]
        if service_f and 'Service' in df.columns:
            df = df[df['Service'].str.lower().str.contains(service_f.lower(), na=False)]

    # ── Product sales ──────────────────────────────────────────────
    product_sales_raw = db.get_product_sales_by_range(
        start_dt, end_dt,
        capster_name=capster_f if capster_f else None,
    )

    # ── Build unified rows ─────────────────────────────────────────
    rows = []

    if type_f != 'produk':   # show haircut rows unless filtered to produk only
        if not df.empty:
            for _, r in df.iterrows():
                raw_date = r['Date']
                # Normalize to Python datetime for consistent sort (pandas Timestamp → datetime)
                if hasattr(raw_date, 'to_pydatetime'):
                    sort_date = raw_date.to_pydatetime().replace(tzinfo=None)
                elif isinstance(raw_date, datetime):
                    sort_date = raw_date.replace(tzinfo=None)
                else:
                    sort_date = datetime.min
                raw_branch = r.get('Branch', '') or ''
                branch_disp = BRANCHES.get(raw_branch, {}).get('short', raw_branch) or raw_branch or '-'
                rows.append({
                    'id':         int(r.get('id', 0)),
                    'type':       'layanan',
                    'date':       raw_date.strftime('%Y-%m-%d %H:%M') if hasattr(raw_date, 'strftime') else str(raw_date),
                    'date_input': raw_date.strftime('%Y-%m-%dT%H:%M') if hasattr(raw_date, 'strftime') else str(raw_date)[:16],
                    'date_sort':  sort_date,
                    'capster':    r.get('Capster', '-'),
                    'service':    r.get('Service', '-'),
                    'price':      int(r.get('Price', 0)),
                    'payment':    r.get('Payment_Method', '-'),
                    'branch':     branch_disp,
                    'branch_id':  raw_branch,
                    'promo_name': r.get('PromoName', '') or '',
                })

    if type_f != 'layanan':  # show product rows unless filtered to layanan only
        for ps in product_sales_raw:
            label = ps['ProductName']
            if ps['Quantity'] > 1:
                label += f" ×{ps['Quantity']}"
            # Apply service/product name filter
            if service_f and service_f.lower() not in ps['ProductName'].lower():
                continue
            # Apply branch filter
            if branch_f:
                b_short = BRANCHES.get(ps['BranchID'], {}).get('short', ps['BranchID'])
                if branch_f.lower() not in b_short.lower() and branch_f.lower() not in (ps['BranchID'] or '').lower():
                    continue
            # Normalize product DateObj to Python datetime
            prod_date = ps['DateObj']
            if hasattr(prod_date, 'to_pydatetime'):
                prod_sort = prod_date.to_pydatetime().replace(tzinfo=None)
            elif isinstance(prod_date, datetime):
                prod_sort = prod_date.replace(tzinfo=None)
            else:
                prod_sort = datetime.min
            rows.append({
                'id':             ps['ID'],
                'type':           'produk',
                'date':           ps['Date'],
                'date_input':     ps['Date'][:16],
                'date_sort':      prod_sort,
                'capster':        ps['CapsterName'],
                'service':        label,
                'price':          ps['Total'],
                'payment':        '-',
                'branch':         BRANCHES.get(ps['BranchID'], {}).get('short', ps['BranchID'] or '-'),
                'qty':            ps['Quantity'],
                'commission':     ps['CommissionEarned'],
                'promo_name':     '',
                # Extra fields needed for edit modal
                'product_id':     ps['ProductID'],
                'product_name':   ps['ProductName'],
                'price_each':     ps['PriceEach'],
                'branch_id':      ps['BranchID'] or '',
            })

    # Sort combined newest first, limit 500 (all date_sort are now Python datetime)
    rows.sort(key=lambda x: x['date_sort'], reverse=True)
    rows = rows[:500]

    total_revenue = sum(r['price'] for r in rows)
    total_count   = len(rows)
    layanan_count = sum(1 for r in rows if r['type'] == 'layanan')
    produk_count  = sum(1 for r in rows if r['type'] == 'produk')

    # Unique values for filter dropdowns (from filtered rows)
    all_capsters = sorted({r['capster'] for r in rows if r['capster'] and r['capster'] != '-'})
    all_branches = sorted({r['branch']  for r in rows if r['branch']  and r['branch']  != '-'})

    # Service datalist: current services + actual service names in this date range
    # so old transactions with renamed/different services are still filterable
    all_service_opts = sorted({v['name'] for v in ALL_SERVICES.values()} | df_service_names)
    all_product_opts = sorted({ps['Name'] for ps in db.get_all_products()})

    # Data for edit modals
    service_names = sorted({v['name'] for v in ALL_SERVICES.values()})
    payment_names = [v['name'] for v in PAYMENT_METHODS.values()]
    branch_shorts = sorted({cfg.get('short', bid) for bid, cfg in BRANCHES.items()})
    all_products  = db.get_all_products()   # for product-sale edit modal
    branch_map    = {bid: cfg.get('short', bid) for bid, cfg in BRANCHES.items()}

    # Paket member choices
    paket_members_raw = db.get_setting('paket_members', 'Bapak,Anak 1,Anak 2,Anak 3')
    paket_members = [m.strip() for m in paket_members_raw.split(',') if m.strip()]

    return render_template(
        'transactions.html',
        rows=rows,
        total_revenue=total_revenue,
        total_count=total_count,
        layanan_count=layanan_count,
        produk_count=produk_count,
        start_str=start_str,
        end_str=end_str,
        capster_f=capster_f,
        branch_f=branch_f,
        service_f=service_f,
        type_f=type_f,
        all_capsters=all_capsters,
        all_branches=all_branches,
        all_service_opts=all_service_opts,
        all_product_opts=all_product_opts,
        service_names=service_names,
        payment_names=payment_names,
        branch_shorts=branch_shorts,
        all_products=all_products,
        branch_map=branch_map,
        paket_members=paket_members,
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


@transactions_bp.route('/transactions/product-sale/<int:sale_id>/edit', methods=['POST'])
@login_required
def edit_product_sale(sale_id: int):
    db = Repository()

    date_str   = request.form.get('date', '').strip()
    capster    = request.form.get('capster', '').strip()
    product_id = request.form.get('product_id', '').strip()
    branch_id  = request.form.get('branch_id', '').strip()

    try:
        quantity = max(1, int(request.form.get('quantity', '1') or 1))
    except (ValueError, TypeError):
        flash('Jumlah harus berupa angka lebih dari 0.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    try:
        tx_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Format tanggal tidak valid.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    if not capster or not product_id or not branch_id:
        flash('Semua field wajib diisi.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    if branch_id not in BRANCHES:
        flash(f"Cabang '{branch_id}' tidak valid.", 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    all_products = db.get_all_products()
    product = next((p for p in all_products if p['ProductID'] == product_id), None)
    if not product:
        flash('Produk tidak valid.', 'danger')
        return redirect(request.referrer or url_for('transactions.transactions'))

    if db.update_product_sale(
        sale_id=sale_id,
        date=tx_date,
        capster_name=capster,
        product_id=product_id,
        product_name=product['Name'],
        price_each=int(float(product['Price'])),
        quantity=quantity,
        commission_rate=float(product['CommissionRate']),
        branch_id=branch_id,
    ):
        flash(f'Penjualan produk #{sale_id} berhasil diperbarui.', 'success')
    else:
        flash(f'Penjualan produk #{sale_id} tidak ditemukan atau gagal diperbarui.', 'danger')

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


@transactions_bp.route('/transactions/product-sale/<int:sale_id>/delete', methods=['POST'])
@login_required
def delete_product_sale(sale_id: int):
    db = Repository()
    if db.delete_product_sale(sale_id):
        flash(f'Penjualan produk #{sale_id} berhasil dihapus. Stok dikembalikan.', 'success')
    else:
        flash(f'Penjualan produk #{sale_id} tidak ditemukan.', 'danger')
    return redirect(request.referrer or url_for('transactions.transactions'))
