"""JSON API endpoints for Chart.js."""
from datetime import datetime, timedelta

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

    # Filter by branch if provided
    if branch_f and not df.empty and 'Branch' in df.columns:
        df = df[df['Branch'] == branch_f]

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
        for branch, rev in by_branch.items():
            labels.append(branch)
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
