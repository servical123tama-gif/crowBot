"""Laporan harian detail — breakdown per layanan, capster, metode bayar."""
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, render_template, request

from dashboard.auth import login_required
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

    if df.empty or 'Price' not in df.columns:
        return render_template(
            'report_daily.html',
            date_str=date_str,
            selected=selected,
            prev_date=prev_date,
            next_date=next_date,
            is_today=is_today,
            total_revenue=0, total_tx=0,
            by_service=[], by_capster=[], by_payment=[], by_branch=[],
            transactions=[],
            active_page='report_daily',
            now=now,
        )

    df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)

    # ── Ringkasan ────────────────────────────────────────────
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
        transactions=transactions,
        active_page='report_daily',
        now=now,
    )
