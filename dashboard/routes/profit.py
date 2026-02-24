"""Profit Report page."""
from datetime import datetime

import pandas as pd
from flask import Blueprint, render_template, request

from dashboard.auth import login_required
from app.db.repository import Repository
from app.config.constants import BRANCHES

profit_bp = Blueprint('profit', __name__)


def _build_capster_lookup(db: Repository) -> dict:
    """name/alias lowercase → {employment_type, commission_rate, monthly_salary, branch_id, name}"""
    lookup = {}
    for c in db.get_all_capsters():
        try:
            salary = int(float(c.get('MonthlySalary') or 0))
        except (ValueError, TypeError):
            salary = 0
        info = {
            'employment_type': (c.get('EmploymentType') or 'mitra').lower().strip(),
            'commission_rate': float(c.get('CommissionRate') or 0.5),
            'monthly_salary':  salary,
            'branch_id':       (c.get('BranchID') or '').strip(),
            'name':            c.get('Name', ''),
        }
        for key in [c.get('Name', ''), c.get('Alias', '')]:
            k = (key or '').lower().strip()
            if k:
                lookup[k] = info
    return lookup


def _calc_profit(db: Repository, year: int, month: int) -> dict:
    """Return profit data dict for given month."""
    df = db.get_transactions_dataframe(year=year)
    if df.empty:
        return {}

    month_str = f"{year:04d}-{month:02d}"
    monthly_df = df[df['Date'].dt.strftime('%Y-%m') == month_str]
    if monthly_df.empty or 'Branch' not in monthly_df.columns:
        return {}

    capster_lookup = _build_capster_lookup(db)
    results = {}
    overall = {'revenue': 0, 'fixed': 0, 'salary': 0, 'commission': 0}

    for branch_id, branch_cfg in BRANCHES.items():
        short     = branch_cfg.get('short', branch_id)
        branch_df = monthly_df[monthly_df['Branch'] == short]
        revenue   = int(branch_df['Price'].sum())

        # Fixed operational (non-karyawan)
        costs_cfg = branch_cfg.get('operational_cost', {})
        fixed_ops = int(sum(v for k, v in costs_cfg.items() if k != 'karyawan'))

        # Tetap salary for this branch
        seen = set()
        tetap_lines = []
        tetap_total = 0
        for info in capster_lookup.values():
            if (info['employment_type'] == 'tetap'
                    and info['branch_id'] == branch_id
                    and info['name']
                    and info['name'] not in seen):
                tetap_lines.append({'name': info['name'], 'salary': info['monthly_salary']})
                tetap_total += info['monthly_salary']
                seen.add(info['name'])

        fixed_total = fixed_ops + tetap_total

        # Mitra commission per capster
        commission_total = 0
        mitra_lines = []
        if not branch_df.empty and 'Capster' in branch_df.columns:
            for cap_name, cap_df in branch_df.groupby('Capster'):
                cap_rev  = int(cap_df['Price'].sum())
                info     = capster_lookup.get(cap_name.lower().strip())
                if info and info['employment_type'] == 'mitra':
                    rate     = info['commission_rate']
                    cap_com  = int(cap_rev * rate)
                    commission_total += cap_com
                    mitra_lines.append({
                        'name': cap_name,
                        'rate': int(rate * 100),
                        'revenue': cap_rev,
                        'commission': cap_com,
                    })

        total_cost = fixed_total + commission_total
        net_profit = revenue - total_cost

        results[short] = {
            'branch_id':    branch_id,
            'name':         branch_cfg.get('name', short),
            'short':        short,
            'revenue':      revenue,
            'fixed_ops':    fixed_ops,
            'tetap_lines':  tetap_lines,
            'tetap_total':  tetap_total,
            'fixed_total':  fixed_total,
            'mitra_lines':  mitra_lines,
            'commission':   commission_total,
            'total_cost':   total_cost,
            'net_profit':   net_profit,
            'tx_count':     len(branch_df),
        }

        overall['revenue']    += revenue
        overall['fixed']      += fixed_total
        overall['salary']     += tetap_total
        overall['commission'] += commission_total

    overall['total_cost'] = overall['fixed'] + overall['commission']
    overall['net_profit'] = overall['revenue'] - overall['total_cost']
    return {'branches': results, 'overall': overall}


@profit_bp.route('/profit')
@login_required
def profit():
    now   = datetime.now()
    year  = int(request.args.get('year',  now.year))
    month = int(request.args.get('month', now.month))

    db   = Repository()
    data = _calc_profit(db, year, month)

    # Month selector options
    months = [
        {'value': m, 'label': datetime(2000, m, 1).strftime('%B')}
        for m in range(1, 13)
    ]
    years = list(range(2024, now.year + 1))

    return render_template(
        'profit.html',
        data=data,
        year=year,
        month=month,
        month_name=datetime(year, month, 1).strftime('%B %Y'),
        months=months,
        years=years,
        active_page='profit',
    )
