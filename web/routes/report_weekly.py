"""Laporan mingguan — Senin s.d. Minggu, breakdown per hari + per layanan/capster/dll."""
import csv
import io
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, Response, render_template, request

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


@report_weekly_bp.route('/report/weekly/export')
@login_required
def report_weekly_export():
    """Export CSV — semua transaksi dalam 1 minggu."""
    db = Repository()
    now = datetime.now()
    date_str = request.args.get('week', now.strftime('%Y-%m-%d'))
    try:
        picked = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        picked = now
    monday = _monday_of(picked)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)

    df = db.get_transactions_by_range(monday, sunday)
    product_sales = db.get_product_sales_by_range(monday, sunday)

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Tanggal', 'Tipe', 'Capster', 'Layanan/Produk', 'Qty',
                'Total (Rp)', 'Pembayaran', 'Cabang', 'Promo'])
    if not df.empty:
        for _, r in df.iterrows():
            date_val = r['Date']
            date_out = date_val.strftime('%Y-%m-%d %H:%M') if hasattr(date_val, 'strftime') else str(date_val)
            w.writerow([date_out, 'Layanan',
                        r.get('Capster', ''), r.get('Service', ''),
                        1, int(r.get('Price', 0)),
                        r.get('Payment_Method', ''), r.get('Branch', ''),
                        r.get('PromoName', '') or ''])
    for ps in product_sales:
        w.writerow([ps.get('Date', ''), 'Produk',
                    ps.get('CapsterName', ''), ps.get('ProductName', ''),
                    ps.get('Quantity', 1), ps.get('Total', 0),
                    '-', ps.get('BranchID', ''), ''])

    filename = f"laporan_mingguan_{monday.strftime('%Y-%m-%d')}.csv"
    return Response(
        '﻿' + out.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


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
    product_sales = db.get_product_sales_by_range(monday, sunday)
    branches_cfg = db.get_all_branches_config()

    # ── Data minggu sebelumnya (untuk delta KPI) ─────────────────────
    prev_monday = monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    prev_df = db.get_transactions_by_range(prev_monday, prev_sunday)
    prev_prod = db.get_product_sales_by_range(prev_monday, prev_sunday)
    prev_svc_revenue = int(prev_df['Price'].sum()) if not prev_df.empty and 'Price' in prev_df.columns else 0
    prev_svc_tx      = len(prev_df) if not prev_df.empty else 0
    prev_prod_rev    = sum(ps.get('Total', 0) for ps in prev_prod)
    prev_total       = prev_svc_revenue + prev_prod_rev

    def _pct_delta(now_v, prev_v):
        if prev_v > 0:
            return round((now_v - prev_v) / prev_v * 100, 1)
        return None

    # ── Produk: ringkasan + breakdown per produk + per hari ─────────
    prod_total_revenue = sum(ps.get('Total', 0) for ps in product_sales)
    prod_total_qty     = sum(ps.get('Quantity', 0) for ps in product_sales)
    prod_total_comm    = sum(ps.get('CommissionEarned', 0) for ps in product_sales)

    # Produk per cabang
    prod_per_branch = {}
    for ps in product_sales:
        bid = ps.get('BranchID') or ''
        if bid not in prod_per_branch:
            prod_per_branch[bid] = {'revenue': 0, 'qty': 0, 'commission': 0}
        prod_per_branch[bid]['revenue']    += ps.get('Total', 0)
        prod_per_branch[bid]['qty']        += ps.get('Quantity', 0)
        prod_per_branch[bid]['commission'] += ps.get('CommissionEarned', 0)

    def _build_branch_detail(svc_pb):
        """Merge svc_per_branch (cash/qris) + prod_per_branch → list dict per cabang."""
        all_ids = set(svc_pb.keys()) | set(prod_per_branch.keys())
        rows = []
        for bid in all_ids:
            cfg = next((b for b in branches_cfg if b.get('BranchID') == bid), {})
            display_name = cfg.get('Short') or cfg.get('Name') or bid or '(tanpa cabang)'
            s = svc_pb.get(bid, {'cash': 0, 'qris': 0, 'other': 0, 'tx': 0})
            p = prod_per_branch.get(bid, {'revenue': 0, 'qty': 0, 'commission': 0})
            svc_total = s['cash'] + s['qris'] + s['other']
            rows.append({
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
                'grand_total':    svc_total + p['revenue'],
            })
        rows.sort(key=lambda x: x['grand_total'], reverse=True)
        return rows

    by_product = {}
    for ps in product_sales:
        key = ps.get('ProductName', '-')
        if key not in by_product:
            by_product[key] = {'name': key, 'qty': 0, 'revenue': 0, 'commission': 0}
        by_product[key]['qty']        += ps.get('Quantity', 0)
        by_product[key]['revenue']    += ps.get('Total', 0)
        by_product[key]['commission'] += ps.get('CommissionEarned', 0)
    by_product = sorted(by_product.values(), key=lambda x: x['revenue'], reverse=True)

    # Produk per hari (untuk row di tabel per-hari)
    prod_per_day = {}  # {dayidx: (qty, revenue)}
    for ps in product_sales:
        raw_date = ps.get('DateObj') or ps.get('Date')
        if hasattr(raw_date, 'weekday'):
            didx = raw_date.weekday()
        else:
            continue
        cur_q, cur_r = prod_per_day.get(didx, (0, 0))
        prod_per_day[didx] = (cur_q + ps.get('Quantity', 0), cur_r + ps.get('Total', 0))

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
        # produk
        prod_total_revenue=prod_total_revenue,
        prod_total_qty=prod_total_qty,
        prod_total_comm=prod_total_comm,
        by_product=by_product,
        branch_detail=_build_branch_detail({}),
        grand_total=prod_total_revenue,
        active_page='report_weekly',
        now=now,
    )

    # Kalau tidak ada layanan sama sekali, isi by_day dari produk saja (biar user tetap lihat trend)
    if df.empty or 'Price' not in df.columns:
        by_day_prod_only = []
        for i in range(7):
            the_date = monday + timedelta(days=i)
            q, r = prod_per_day.get(i, (0, 0))
            by_day_prod_only.append({
                'day_name':   DAYS_ID[i],
                'date':       the_date,
                'date_str':   the_date.strftime('%Y-%m-%d'),
                'date_label': _fmt_id_date(the_date, with_year=False),
                'count':      0,          # tx layanan
                'revenue':    0,          # revenue layanan
                'prod_qty':   q,
                'prod_revenue': r,
                'pct':        round(r / prod_total_revenue * 100) if prod_total_revenue else 0,
            })
        empty_ctx['by_day'] = by_day_prod_only
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
        prod_q, prod_r = prod_per_day.get(i, (0, 0))
        day_total = rev + prod_r
        by_day.append({
            'day_name':    DAYS_ID[i],
            'date':        the_date,
            'date_str':    the_date.strftime('%Y-%m-%d'),
            'date_label':  _fmt_id_date(the_date, with_year=False),
            'count':       cnt,
            'revenue':     rev,          # layanan
            'prod_qty':    prod_q,
            'prod_revenue': prod_r,
            'day_total':   day_total,     # gabungan
            'pct':         round(day_total / (total_revenue + prod_total_revenue) * 100)
                             if (total_revenue + prod_total_revenue) else 0,
        })

    active_days = sum(1 for d in by_day if d['count'] > 0)
    avg_daily_revenue = total_revenue // active_days if active_days else 0

    # Per layanan — compute BOTH pct_tx and pct_rev supaya template bisa label eksplisit
    by_service = []
    if 'Service' in df.columns:
        svc = df.groupby('Service').agg(count=('Price', 'count'), revenue=('Price', 'sum')) \
                .sort_values('revenue', ascending=False)
        for name, row in svc.iterrows():
            by_service.append({
                'name':    name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
                'pct_tx':  round(row['count']   / total_tx      * 100) if total_tx      else 0,
                'pct_rev': round(row['revenue'] / total_revenue * 100) if total_revenue else 0,
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

    # Per metode bayar — pct dari revenue (explicit label 'pct_rev')
    by_payment = []
    if 'Payment_Method' in df.columns:
        pay = df.groupby('Payment_Method').agg(count=('Price', 'count'), revenue=('Price', 'sum')) \
                .sort_values('revenue', ascending=False)
        for name, row in pay.iterrows():
            by_payment.append({
                'name':    name,
                'count':   int(row['count']),
                'revenue': int(row['revenue']),
                'pct_rev': round(row['revenue'] / total_revenue * 100) if total_revenue else 0,
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

    # Service payment split per branch → merge dgn produk
    svc_per_branch = {}
    if 'Branch' in df.columns and 'Payment_Method' in df.columns:
        for (bid, pm), grp in df.groupby(['Branch', 'Payment_Method']):
            if bid not in svc_per_branch:
                svc_per_branch[bid] = {'cash': 0, 'qris': 0, 'other': 0, 'tx': 0}
            rev = int(grp['Price'].sum())
            svc_per_branch[bid]['tx'] += len(grp)
            pm_l = (pm or '').lower()
            if 'cash' in pm_l:
                svc_per_branch[bid]['cash'] += rev
            elif 'qris' in pm_l:
                svc_per_branch[bid]['qris'] += rev
            else:
                svc_per_branch[bid]['other'] += rev
    branch_detail = _build_branch_detail(svc_per_branch)

    grand_total = total_revenue + prod_total_revenue
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
        capster_count=len(by_capster),
        by_service=by_service,
        by_capster=by_capster,
        by_payment=by_payment,
        by_branch=by_branch,
        branch_detail=branch_detail,
        by_day=by_day,
        # produk
        prod_total_revenue=prod_total_revenue,
        prod_total_qty=prod_total_qty,
        prod_total_comm=prod_total_comm,
        by_product=by_product,
        grand_total=grand_total,
        # ── Delta vs minggu lalu ──
        delta_svc_revenue = _pct_delta(total_revenue, prev_svc_revenue),
        delta_svc_tx      = _pct_delta(total_tx,      prev_svc_tx),
        delta_grand_total = _pct_delta(grand_total,   prev_total),
        prev_svc_revenue  = prev_svc_revenue,
        prev_grand_total  = prev_total,
        active_page='report_weekly',
        now=now,
    )
