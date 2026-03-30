"""JSON API endpoints for Chart.js."""
from datetime import datetime, timedelta, timezone

import pandas as pd
from flask import Blueprint, jsonify, request, session, redirect, url_for

from app.db.repository import Repository
from app.config.constants import BRANCHES

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _auth_check():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@api_bp.route('/chart/revenue-daily')
def revenue_daily():
    err = _auth_check()
    if err:
        return err

    days      = int(request.args.get('days', 30))
    branch_f  = request.args.get('branch', '').strip()   # optional branch filter
    db        = Repository()
    now       = datetime.now()

    start_dt = now - timedelta(days=days - 1)
    start_dt = start_dt.replace(hour=0, minute=0, second=0)
    df = db.get_transactions_by_range(start_dt, now)

    # Filter by branch if provided (branch_f is short name, DB stores branch_id)
    if branch_f and not df.empty and 'Branch' in df.columns:
        # Build reverse map: short → branch_id (handles both short and branch_id as input)
        short_to_id = {cfg.get('short', bid): bid for bid, cfg in BRANCHES.items()}
        branch_id_f = short_to_id.get(branch_f, branch_f)
        df = df[df['Branch'] == branch_id_f]

    labels = []
    values = []

    for i in range(days):
        d = (start_dt + timedelta(days=i)).date()
        labels.append(d.strftime('%d/%m'))
        if not df.empty and 'Date' in df.columns:
            day_df = df[df['Date'].dt.date == d]
            values.append(int(day_df['Price'].sum()) if not day_df.empty else 0)
        else:
            values.append(0)

    return jsonify({'labels': labels, 'values': values})


@api_bp.route('/chart/branch-split')
def branch_split():
    err = _auth_check()
    if err:
        return err

    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))

    db        = Repository()
    year_df   = db.get_transactions_dataframe(year=year)
    month_str = f"{year:04d}-{month:02d}"
    month_df  = (
        year_df[year_df['Date'].dt.strftime('%Y-%m') == month_str]
        if not year_df.empty else pd.DataFrame()
    )

    labels = []
    values = []
    if not month_df.empty and 'Branch' in month_df.columns:
        by_branch = month_df.groupby('Branch')['Price'].sum().sort_values(ascending=False)
        for branch_id, rev in by_branch.items():
            short = BRANCHES.get(branch_id, {}).get('short', branch_id)
            labels.append(short)
            values.append(int(rev))

    return jsonify({'labels': labels, 'values': values})


@api_bp.route('/chart/payment-split')
def payment_split():
    err = _auth_check()
    if err:
        return err

    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))

    db        = Repository()
    year_df   = db.get_transactions_dataframe(year=year)
    month_str = f"{year:04d}-{month:02d}"
    month_df  = (
        year_df[year_df['Date'].dt.strftime('%Y-%m') == month_str]
        if not year_df.empty else pd.DataFrame()
    )

    labels = []
    values = []
    if not month_df.empty and 'Payment_Method' in month_df.columns:
        by_pay = month_df.groupby('Payment_Method')['Price'].sum().sort_values(ascending=False)
        for method, rev in by_pay.items():
            labels.append(method)
            values.append(int(rev))

    return jsonify({'labels': labels, 'values': values})


@api_bp.route('/chart/top-services')
def top_services():
    err = _auth_check()
    if err:
        return err

    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    top_n = int(request.args.get('n', 8))

    db        = Repository()
    year_df   = db.get_transactions_dataframe(year=year)
    month_str = f"{year:04d}-{month:02d}"
    month_df  = (
        year_df[year_df['Date'].dt.strftime('%Y-%m') == month_str]
        if not year_df.empty else pd.DataFrame()
    )

    if month_df.empty or 'Service' not in month_df.columns:
        return jsonify({'labels': [], 'counts': [], 'revenues': []})

    by_service = (
        month_df.groupby('Service')
        .agg(count=('Price', 'count'), revenue=('Price', 'sum'))
        .sort_values('count', ascending=False)
        .head(top_n)
    )

    return jsonify({
        'labels':   by_service.index.tolist(),
        'counts':   by_service['count'].tolist(),
        'revenues': by_service['revenue'].astype(int).tolist(),
    })


@api_bp.route('/customer/<int:cid>/transactions')
def customer_transactions(cid):
    err = _auth_check()
    if err:
        return err
    db   = Repository()
    rows = db.get_transactions_by_customer(cid, limit=30)
    data = [
        {
            'date':    r['date'].strftime('%d %b %Y'),
            'time':    r['date'].strftime('%H:%M'),
            'service': r['service'],
            'price':   r['price'],
            'capster': r['capster'],
            'payment': r['payment'],
            'promo':   r['promo'],
        }
        for r in rows
    ]
    return jsonify({'transactions': data, 'total': len(data)})


@api_bp.route('/notifications')
def notifications():
    err = _auth_check()
    if err:
        return err

    db   = Repository()
    rows = db.get_recent_customers(limit=15)
    now  = datetime.now()

    items = []
    for r in rows:
        created = r.get('CreatedAt')
        if created:
            diff   = now - created
            secs   = int(diff.total_seconds())
            if secs < 60:
                ago = 'Baru saja'
            elif secs < 3600:
                ago = f'{secs // 60} menit lalu'
            elif secs < 86400:
                ago = f'{secs // 3600} jam lalu'
            else:
                ago = f'{secs // 86400} hari lalu'
        else:
            ago = ''

        date_str = created.strftime('%d %b %Y, %H:%M') if created else ''

        items.append({
            'name':     r.get('Name', ''),
            'phone':    r.get('Phone', '') or '-',
            'added_by': r.get('AddedBy', '') or '-',
            'ago':      ago,
            'date_str': date_str,
        })

    return jsonify({'notifications': items, 'count': len(items)})
