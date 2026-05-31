"""Perbandingan antar cabang — revenue, transaksi, top capster."""
from datetime import datetime

import pandas as pd
from flask import Blueprint, render_template, request

from web.auth import login_required
from app.db.repository import Repository
from app.config.constants import BRANCHES

compare_bp = Blueprint('compare', __name__)


@compare_bp.route('/compare')
@login_required
def compare():
    db  = Repository()
    now = datetime.now()

    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))
    month_str = f"{year:04d}-{month:02d}"

    year_df  = db.get_transactions_dataframe(year=year)
    month_df = (
        year_df[year_df['Date'].dt.strftime('%Y-%m') == month_str]
        if not year_df.empty else pd.DataFrame()
    )

    # Kumpulkan semua branch dari DB + BRANCHES constant
    raw_branches = db.get_all_branches_config()
    branch_ids   = [b['BranchID'] for b in raw_branches]

    branch_stats = []
    for b in raw_branches:
        bid   = b['BranchID']
        bname = b['Name']
        short = b.get('Short', bid)

        if not month_df.empty and 'Branch' in month_df.columns:
            bdf = month_df[month_df['Branch'] == short]
        else:
            bdf = pd.DataFrame()

        revenue  = int(bdf['Price'].sum()) if not bdf.empty else 0
        tx_count = len(bdf)
        avg_tx   = int(revenue / tx_count) if tx_count else 0

        # Top capster bulan ini
        top_cap = None
        if not bdf.empty and 'Capster' in bdf.columns:
            cap_rev = bdf.groupby('Capster')['Price'].sum()
            if not cap_rev.empty:
                top_cap = {'name': cap_rev.idxmax(), 'revenue': int(cap_rev.max())}

        # Top layanan bulan ini
        top_svc = None
        if not bdf.empty and 'Service' in bdf.columns:
            svc_cnt = bdf['Service'].value_counts()
            if not svc_cnt.empty:
                top_svc = {'name': svc_cnt.idxmax(), 'count': int(svc_cnt.max())}

        # Revenue per hari (untuk mini sparkline — 7 hari terakhir)
        sparkline = []
        if not month_df.empty and 'Date' in month_df.columns:
            for day in range(1, 32):
                try:
                    d = datetime(year, month, day).date()
                except ValueError:
                    break
                ddf = bdf[bdf['Date'].dt.date == d] if not bdf.empty else pd.DataFrame()
                sparkline.append(int(ddf['Price'].sum()) if not ddf.empty else 0)

        branch_stats.append({
            'branch_id': bid,
            'name':      bname,
            'short':     short,
            'revenue':   revenue,
            'tx_count':  tx_count,
            'avg_tx':    avg_tx,
            'top_cap':   top_cap,
            'top_svc':   top_svc,
            'sparkline': sparkline,
        })

    # Urutkan by revenue desc
    branch_stats.sort(key=lambda x: x['revenue'], reverse=True)

    # Hitung % share
    total_rev = sum(b['revenue'] for b in branch_stats) or 1
    for b in branch_stats:
        b['rev_pct'] = round(b['revenue'] / total_rev * 100)

    # Trend: compare with previous month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    prev_str = f"{prev_year:04d}-{prev_month:02d}"

    prev_year_df = db.get_transactions_dataframe(year=prev_year) if prev_year != year else year_df
    prev_month_df = (
        prev_year_df[prev_year_df['Date'].dt.strftime('%Y-%m') == prev_str]
        if not prev_year_df.empty else pd.DataFrame()
    )

    for b in branch_stats:
        short = b['short']
        if not prev_month_df.empty and 'Branch' in prev_month_df.columns:
            prev_rev = int(prev_month_df[prev_month_df['Branch'] == short]['Price'].sum())
        else:
            prev_rev = 0
        if prev_rev:
            b['growth'] = round((b['revenue'] - prev_rev) / prev_rev * 100, 1)
        else:
            b['growth'] = None
        b['prev_revenue'] = prev_rev

    months = [{'value': m, 'label': datetime(2000, m, 1).strftime('%B')} for m in range(1, 13)]
    years  = list(range(2024, now.year + 1))

    return render_template(
        'compare.html',
        branch_stats=branch_stats,
        total_rev=total_rev,
        year=year,
        month=month,
        month_name=datetime(year, month, 1).strftime('%B %Y'),
        months=months,
        years=years,
        active_page='compare',
        now=now,
    )
