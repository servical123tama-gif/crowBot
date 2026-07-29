"""Laporan mingguan — Senin s.d. Minggu, breakdown per hari + per layanan/capster/dll."""
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, render_template, request

from web.auth import login_required
from app.db.repository import Repository

report_weekly_bp = Blueprint('report_weekly', __name__)

DAYS_ID = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
MONTHS_ID = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember',
}


def _fmt_id_date(d: datetime, with_year: bool = True) -> str:
    """Contoh: '16 Februari 2026' (with_year) atau '16 Februari'."""
    base = f"{d.day} {MONTHS_ID[d.month]}"
    return f"{base} {d.year}" if with_year else base


def _monday_of(d: datetime) -> datetime:
    """Kembalikan tanggal Senin dari minggu yang mengandung d (00:00:00)."""
    return (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


@report_weekly_bp.route('/report/weekly')
@login_required
def report_weekly():
    db  = Repository()
    now = datetime.now()

    # ?week=YYYY-MM-DD → any date within the week, dinormalisasi ke Senin.
    date_str = request.args.get('week', now.strftime('%Y-%m-%d'))
    try:
        picked = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        picked = now

    monday = _monday_of(picked)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)

    prev_week = (monday - timedelta(days=7)).strftime('%Y-%m-%d')
    next_week = (monday + timedelta(days=7)).strftime('%Y-%m-%d')
    is_current_week = _monday_of(now) == monday

    # Label rentang: "20 - 26 Juli 2026" atau "29 Juni - 5 Juli 2026" kalau lintas bulan
    if monday.month == sunday.month:
        range_label = f"{monday.day} - {sunday.day} {MONTHS_ID[monday.month]} {monday.year}"
    elif monday.year == sunday.year:
        range_label = f"{_fmt_id_date(monday, with_year=False)} - {_fmt_id_date(sunday)}"
    else:
        range_label = f"{_fmt_id_date(monday)} - {_fmt_id_date(sunday)}"

    df = db.get_transactions_by_range(monday, sunday)

    empty_ctx = dict(
        date_str=monday.strftime('%Y-%m-%d'),
        monday=monday,
        sunday=sunday,
        range_label=range_label,
        prev_week=prev_week,
        next_week=next_week,
        is_current_week=is_current_week,
        total_revenue=0, total_tx=0, avg_daily_revenue=0, active_days=0,
        by_service=[], by_capster=[], by_payment=[], by_branch=[], by_day=[],
        active_page='report_weekly',
        now=now,
    )

    if df.empty or 'Price' not in df.columns:
        return render_template('report_weekly.html', **empty_ctx)

    df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)

    total_revenue = int(df['Price'].sum())
    total_tx      = len(df)

    # Per hari (Senin..Minggu — 7 baris, isi 0 kalau kosong)
    df['_dayidx'] = df['Date'].dt.weekday if 'Date' in df.columns else 0
    daily_group = df.groupby('_dayidx').agg(count=('Price', 'count'), revenue=('Price', 'sum'))
    by_day = []
    for i in range(7):
        the_date = monday + timedelta(days=i)
        if i in daily_group.index:
            row = daily_group.loc[i]
            cnt = int(row['count'])
            rev = int(row['revenue'])
        else:
            cnt, rev = 0, 0
        by_day.append({
            'day_name':  DAYS_ID[i],
            'date':      the_date,
            'date_str':  the_date.strftime('%Y-%m-%d'),
            'date_label': _fmt_id_date(the_date, with_year=False),
            'count':     cnt,
            'revenue':   rev,
            'pct':       round(rev / total_revenue * 100) if total_revenue else 0,
        })

    active_days = sum(1 for d in by_day if d['count'] > 0)
    avg_daily_revenue = total_revenue // active_days if active_days else 0

    # Per layanan
    by_service = []
    if 'Service' in df.columns:
        svc = df.groupby('Service').agg(count=('Price', 'count'), revenue=('Price', 'sum')) \
                .sort_values('count', ascending=False)
        for name, row in svc.iterrows():
            by_service.append({
                'name':    name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
                'pct':     round(row['count'] / total_tx * 100) if total_tx else 0,
            })

    # Per capster
    by_capster = []
    if 'Capster' in df.columns:
        cap = df.groupby('Capster').agg(count=('Price', 'count'), revenue=('Price', 'sum')) \
                .sort_values('revenue', ascending=False)
        for name, row in cap.iterrows():
            by_capster.append({
                'name':    name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
            })

    # Per metode bayar
    by_payment = []
    if 'Payment_Method' in df.columns:
        pay = df.groupby('Payment_Method').agg(count=('Price', 'count'), revenue=('Price', 'sum')) \
                .sort_values('revenue', ascending=False)
        for name, row in pay.iterrows():
            by_payment.append({
                'name':    name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
                'pct':     round(row['revenue'] / total_revenue * 100) if total_revenue else 0,
            })

    # Per cabang
    by_branch = []
    if 'Branch' in df.columns:
        brn = df.groupby('Branch').agg(count=('Price', 'count'), revenue=('Price', 'sum')) \
                .sort_values('revenue', ascending=False)
        for name, row in brn.iterrows():
            by_branch.append({
                'name':    name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
            })

    return render_template(
        'report_weekly.html',
        date_str=monday.strftime('%Y-%m-%d'),
        monday=monday,
        sunday=sunday,
        range_label=range_label,
        prev_week=prev_week,
        next_week=next_week,
        is_current_week=is_current_week,
        total_revenue=total_revenue,
        total_tx=total_tx,
        avg_daily_revenue=avg_daily_revenue,
        active_days=active_days,
        by_service=by_service,
        by_capster=by_capster,
        by_payment=by_payment,
        by_branch=by_branch,
        by_day=by_day,
        active_page='report_weekly',
        now=now,
    )
