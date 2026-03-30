"""Home / Overview page."""
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, render_template, request, session, redirect, url_for

from dashboard.auth import login_required, DASHBOARD_PASSWORD
from app.db.repository import Repository
from app.config.constants import BRANCHES

home_bp = Blueprint('home', __name__)


@home_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('home.index'))
    error = None
    if request.method == 'POST':
        if request.form.get('password') == DASHBOARD_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('home.index'))
        error = 'Password salah'
    return render_template('login.html', error=error)


@home_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home.login'))


@home_bp.route('/')
@login_required
def index():
    db = Repository()
    now = datetime.now()

    # ── Today ──────────────────────────────────────────────────────
    today_df = db.get_transactions_by_date(now)
    today_revenue = int(today_df['Price'].sum()) if not today_df.empty else 0
    today_count   = len(today_df)

    # ── This month ─────────────────────────────────────────────────
    year_df   = db.get_transactions_dataframe(year=now.year)
    month_str = now.strftime('%Y-%m')
    month_df  = (
        year_df[year_df['Date'].dt.strftime('%Y-%m') == month_str]
        if not year_df.empty else pd.DataFrame()
    )
    month_revenue = int(month_df['Price'].sum()) if not month_df.empty else 0
    month_count   = len(month_df)

    # ── Last month ─────────────────────────────────────────────────
    first_day = now.replace(day=1)
    last_month_date = first_day - timedelta(days=1)
    lm_str    = last_month_date.strftime('%Y-%m')
    lm_year   = db.get_transactions_dataframe(year=last_month_date.year)
    lm_df     = (
        lm_year[lm_year['Date'].dt.strftime('%Y-%m') == lm_str]
        if not lm_year.empty else pd.DataFrame()
    )
    last_month_revenue = int(lm_df['Price'].sum()) if not lm_df.empty else 0

    # Month growth %
    if last_month_revenue > 0:
        growth = round((month_revenue - last_month_revenue) / last_month_revenue * 100, 1)
    else:
        growth = None

    # ── Per branch today ───────────────────────────────────────────
    branch_today = {}
    if not today_df.empty and 'Branch' in today_df.columns:
        for branch, grp in today_df.groupby('Branch'):
            short = BRANCHES.get(branch, {}).get('short', branch)
            branch_today[short] = branch_today.get(short, 0) + int(grp['Price'].sum())

    # ── Per branch this month ──────────────────────────────────────
    branch_month = {}
    if not month_df.empty and 'Branch' in month_df.columns:
        for branch, grp in month_df.groupby('Branch'):
            short = BRANCHES.get(branch, {}).get('short', branch)
            existing = branch_month.get(short, {'revenue': 0, 'count': 0})
            branch_month[short] = {
                'revenue': existing['revenue'] + int(grp['Price'].sum()),
                'count': existing['count'] + len(grp),
            }

    # ── Top 5 capsters this month ──────────────────────────────────
    top_capsters = []
    if not month_df.empty and 'Capster' in month_df.columns:
        cap_totals = (
            month_df.groupby('Capster')['Price'].sum()
            .sort_values(ascending=False).head(5)
        )
        cap_counts = month_df.groupby('Capster')['Price'].count()
        for cap, rev in cap_totals.items():
            top_capsters.append({
                'name':    cap,
                'revenue': int(rev),
                'count':   int(cap_counts.get(cap, 0)),
            })

    # ── Active capsters count ─────────────────────────────────────
    capster_count = len(db.get_all_capsters())

    # ── Notifikasi customer baru (10 terakhir) ────────────────────
    recent_customers = db.get_recent_customers(limit=10)

    # ── Extra quick stats ─────────────────────────────────────────
    today_avg     = int(today_revenue / today_count) if today_count else 0
    month_avg     = int(month_revenue / month_count) if month_count else 0
    month_top_svc = ''
    if not month_df.empty and 'Service' in month_df.columns:
        svc_counts = month_df['Service'].value_counts()
        if not svc_counts.empty:
            month_top_svc = svc_counts.idxmax()

    # Growth per branch (bulan ini vs bulan lalu)
    # lm_df['Branch'] berisi branch_id, tapi branch_month pakai key 'short'
    short_to_id = {cfg.get('short', bid): bid for bid, cfg in BRANCHES.items()}
    branch_growth = {}
    for short, stats in branch_month.items():
        lm_rev = 0
        if not lm_df.empty and 'Branch' in lm_df.columns:
            branch_id = short_to_id.get(short, short)
            lm_rev = int(lm_df[lm_df['Branch'] == branch_id]['Price'].sum())
        if lm_rev:
            branch_growth[short] = round((stats['revenue'] - lm_rev) / lm_rev * 100, 1)

    return render_template(
        'home.html',
        now=now,
        today_revenue=today_revenue,
        today_count=today_count,
        today_avg=today_avg,
        month_revenue=month_revenue,
        month_count=month_count,
        month_avg=month_avg,
        month_top_svc=month_top_svc,
        last_month_revenue=last_month_revenue,
        growth=growth,
        branch_today=branch_today,
        branch_month=branch_month,
        branch_growth=branch_growth,
        top_capsters=top_capsters,
        capster_count=capster_count,
        recent_customers=recent_customers,
        branches=BRANCHES,
        active_page='home',
    )
