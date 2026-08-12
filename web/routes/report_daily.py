"""Laporan harian detail — breakdown per layanan, capster, metode bayar, produk."""
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, render_template, request

from web.auth import login_required
from app.db.repository import Repository

report_daily_bp = Blueprint('report_daily', __name__)


@report_daily_bp.route('/report/daily')
@login_required
def report_daily():
    db  = Repository()
    now = datetime.now()

    date_str = request.args.get('date', now.strftime('%Y-%m-%d'))
    try:
        selected = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        selected = now

    prev_date = (selected - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (selected + timedelta(days=1)).strftime('%Y-%m-%d')
    is_today  = selected.date() == now.date()

    # Ambil transaksi hari itu
    start_dt = selected.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt   = selected.replace(hour=23, minute=59, second=59, microsecond=999999)
    df = db.get_transactions_by_range(start_dt, end_dt)
    product_sales = db.get_product_sales_by_range(start_dt, end_dt)
    branches_cfg = db.get_all_branches_config()

    # ── Ringkasan produk ─────────────────────────────────────
    prod_total_revenue = sum(ps.get('Total', 0) for ps in product_sales)
    prod_total_qty     = sum(ps.get('Quantity', 0) for ps in product_sales)
    prod_total_comm    = sum(ps.get('CommissionEarned', 0) for ps in product_sales)

    # ── Ringkasan produk per cabang ──────────────────────────
    prod_per_branch = {}   # {branch_id: {'revenue', 'qty', 'commission'}}
    for ps in product_sales:
        bid = ps.get('BranchID') or ''
        if bid not in prod_per_branch:
            prod_per_branch[bid] = {'revenue': 0, 'qty': 0, 'commission': 0}
        prod_per_branch[bid]['revenue']    += ps.get('Total', 0)
        prod_per_branch[bid]['qty']        += ps.get('Quantity', 0)
        prod_per_branch[bid]['commission'] += ps.get('CommissionEarned', 0)

    # Breakdown per produk
    by_product = {}
    for ps in product_sales:
        key = ps.get('ProductName', '-')
        if key not in by_product:
            by_product[key] = {'name': key, 'qty': 0, 'revenue': 0, 'commission': 0}
        by_product[key]['qty']        += ps.get('Quantity', 0)
        by_product[key]['revenue']    += ps.get('Total', 0)
        by_product[key]['commission'] += ps.get('CommissionEarned', 0)
    by_product = sorted(by_product.values(), key=lambda x: x['revenue'], reverse=True)

    # Detail transaksi produk (row per sale)
    product_transactions = []
    for ps in product_sales:
        raw_date = ps.get('DateObj') or ps.get('Date')
        time_str = raw_date.strftime('%H:%M') if hasattr(raw_date, 'strftime') else str(raw_date)[11:16]
        product_transactions.append({
            'time':       time_str,
            'capster':    ps.get('CapsterName', ''),
            'product':    ps.get('ProductName', ''),
            'qty':        ps.get('Quantity', 1),
            'price_each': ps.get('PriceEach', 0),
            'total':      ps.get('Total', 0),
            'commission': ps.get('CommissionEarned', 0),
            'branch':     ps.get('BranchID', ''),
        })
    product_transactions.sort(key=lambda x: x['time'])

    if df.empty or 'Price' not in df.columns:
        # Kalau tidak ada layanan tapi ada produk, tetap tampilkan branch detail (produk-only)
        branch_detail_empty = []
        for bid, p in prod_per_branch.items():
            cfg = next((b for b in branches_cfg if b.get('BranchID') == bid), {})
            display_name = cfg.get('Short') or cfg.get('Name') or bid or '(tanpa cabang)'
            branch_detail_empty.append({
                'branch_id':      bid,
                'name':           display_name,
                'svc_cash': 0, 'svc_qris': 0, 'svc_other': 0, 'svc_total': 0, 'svc_tx': 0,
                'prod_revenue':   p['revenue'],
                'prod_qty':       p['qty'],
                'prod_commission':p['commission'],
                'grand_total':    p['revenue'],
            })
        branch_detail_empty.sort(key=lambda x: x['grand_total'], reverse=True)
        return render_template(
            'report_daily.html',
            date_str=date_str,
            selected=selected,
            prev_date=prev_date,
            next_date=next_date,
            is_today=is_today,
            total_revenue=0, total_tx=0,
            by_service=[], by_capster=[], by_payment=[], by_branch=[],
            branch_detail=branch_detail_empty,
            transactions=[],
            # produk
            prod_total_revenue=prod_total_revenue,
            prod_total_qty=prod_total_qty,
            prod_total_comm=prod_total_comm,
            by_product=by_product,
            product_transactions=product_transactions,
            grand_total=prod_total_revenue,
            active_page='report_daily',
            now=now,
        )

    df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)

    # ── Ringkasan layanan ────────────────────────────────────
    total_revenue = int(df['Price'].sum())
    total_tx      = len(df)

    # Breakdown per layanan
    by_service = []
    if 'Service' in df.columns:
        svc = df.groupby('Service').agg(count=('Price','count'), revenue=('Price','sum')).sort_values('count', ascending=False)
        for svc_name, row in svc.iterrows():
            by_service.append({
                'name':    svc_name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
                'pct':     round(row['count'] / total_tx * 100) if total_tx else 0,
            })

    # Breakdown per capster
    by_capster = []
    if 'Capster' in df.columns:
        cap = df.groupby('Capster').agg(count=('Price','count'), revenue=('Price','sum')).sort_values('revenue', ascending=False)
        for cap_name, row in cap.iterrows():
            by_capster.append({
                'name':    cap_name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
            })

    # Breakdown per metode bayar
    by_payment = []
    if 'Payment_Method' in df.columns:
        pay = df.groupby('Payment_Method').agg(count=('Price','count'), revenue=('Price','sum')).sort_values('revenue', ascending=False)
        for pay_name, row in pay.iterrows():
            by_payment.append({
                'name':    pay_name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
                'pct':     round(row['revenue'] / total_revenue * 100) if total_revenue else 0,
            })

    # Breakdown per cabang
    by_branch = []
    if 'Branch' in df.columns:
        brn = df.groupby('Branch').agg(count=('Price','count'), revenue=('Price','sum')).sort_values('revenue', ascending=False)
        for brn_name, row in brn.iterrows():
            by_branch.append({
                'name':    brn_name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
            })

    # ── Per cabang detail: Cash | QRIS | Produk | Total ──────
    # Service payment split per branch
    svc_per_branch = {}   # {branch_id: {'cash': X, 'qris': Y, 'other': Z, 'tx': N}}
    if 'Branch' in df.columns and 'Payment_Method' in df.columns:
        for (bid, pm), grp in df.groupby(['Branch', 'Payment_Method']):
            if bid not in svc_per_branch:
                svc_per_branch[bid] = {'cash': 0, 'qris': 0, 'other': 0, 'tx': 0}
            rev = int(grp['Price'].sum())
            cnt = len(grp)
            svc_per_branch[bid]['tx'] += cnt
            pm_l = (pm or '').lower()
            if 'cash' in pm_l:
                svc_per_branch[bid]['cash'] += rev
            elif 'qris' in pm_l:
                svc_per_branch[bid]['qris'] += rev
            else:
                svc_per_branch[bid]['other'] += rev

    # Detail transaksi (tabel bawah)
    transactions = []
    for _, row in df.sort_values('Date').iterrows():
        transactions.append({
            'time':    row['Date'].strftime('%H:%M') if hasattr(row['Date'], 'strftime') else str(row['Date'])[11:16],
            'capster': row.get('Capster', ''),
            'service': row.get('Service', ''),
            'branch':  row.get('Branch', ''),
            'payment': row.get('Payment_Method', ''),
            'price':   int(row['Price']),
        })

    # ── Merge svc_per_branch + prod_per_branch → branch_detail ──
    all_branch_ids = set(svc_per_branch.keys()) | set(prod_per_branch.keys())
    branch_detail = []
    for bid in all_branch_ids:
        # cari display name dari config
        cfg = next((b for b in branches_cfg if b.get('BranchID') == bid), {})
        display_name = cfg.get('Short') or cfg.get('Name') or bid or '(tanpa cabang)'
        s = svc_per_branch.get(bid, {'cash': 0, 'qris': 0, 'other': 0, 'tx': 0})
        p = prod_per_branch.get(bid, {'revenue': 0, 'qty': 0, 'commission': 0})
        svc_total = s['cash'] + s['qris'] + s['other']
        grand = svc_total + p['revenue']
        branch_detail.append({
            'branch_id':      bid,
            'name':           display_name,
            'svc_cash':       s['cash'],
            'svc_qris':       s['qris'],
            'svc_other':      s['other'],
            'svc_total':      svc_total,
            'svc_tx':         s['tx'],
            'prod_revenue':   p['revenue'],
            'prod_qty':       p['qty'],
            'prod_commission':p['commission'],
            'grand_total':    grand,
        })
    branch_detail.sort(key=lambda x: x['grand_total'], reverse=True)

    return render_template(
        'report_daily.html',
        date_str=date_str,
        selected=selected,
        prev_date=prev_date,
        next_date=next_date,
        is_today=is_today,
        total_revenue=total_revenue,
        total_tx=total_tx,
        by_service=by_service,
        by_capster=by_capster,
        by_payment=by_payment,
        by_branch=by_branch,
        branch_detail=branch_detail,
        transactions=transactions,
        # produk
        prod_total_revenue=prod_total_revenue,
        prod_total_qty=prod_total_qty,
        prod_total_comm=prod_total_comm,
        by_product=by_product,
        product_transactions=product_transactions,
        grand_total=total_revenue + prod_total_revenue,
        active_page='report_daily',
        now=now,
    )
