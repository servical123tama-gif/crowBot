"""
Report text builders for the Telegram admin bot.
Reuses Repository (same data source as web dashboard).
Output is plain text (no Markdown) to keep formatting simple.
"""
from datetime import datetime, timedelta, date
from typing import Optional

import pandas as pd

from app.db.repository import Repository
from app.config.constants import BRANCHES
from app.services.reports import calc_profit
from bot.formatters import fmt_idr, fmt_date, fmt_month_id


# ── Helpers ────────────────────────────────────────────────────────────────── #

def _branch_short(branch_id: str) -> str:
    return BRANCHES.get(branch_id, {}).get('short', branch_id or '?')


def _branch_breakdown(df: pd.DataFrame) -> list[str]:
    lines = []
    if df.empty or 'Branch' not in df.columns:
        return lines
    grouped = df.groupby('Branch')
    for branch_id, grp in grouped:
        lines.append(
            f"  • {_branch_short(branch_id)}: "
            f"{fmt_idr(grp['Price'].sum())} ({len(grp)} trx)"
        )
    return lines


def _capster_breakdown(df: pd.DataFrame, top: int = 10) -> list[str]:
    lines = []
    if df.empty or 'Capster' not in df.columns:
        return lines
    grouped = (
        df.groupby('Capster')['Price']
        .agg(['sum', 'count'])
        .sort_values('sum', ascending=False)
        .head(top)
    )
    for capster, row in grouped.iterrows():
        lines.append(
            f"  • {capster}: {fmt_idr(row['sum'])} ({int(row['count'])} trx)"
        )
    return lines


# ── Daily ──────────────────────────────────────────────────────────────────── #

def daily_report(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now()
    repo = Repository()
    df = repo.get_transactions_by_date(dt)

    header = f"📅 Laporan Harian — {fmt_date(dt)}"
    if df.empty:
        return f"{header}\n\nBelum ada transaksi."

    total = int(df['Price'].sum())
    count = len(df)

    lines = [
        header,
        '',
        f"💰 Total: {fmt_idr(total)}",
        f"🧾 Transaksi: {count}",
    ]
    branch_lines = _branch_breakdown(df)
    if branch_lines:
        lines.append('')
        lines.append('🏪 Per Cabang:')
        lines.extend(branch_lines)

    capster_lines = _capster_breakdown(df)
    if capster_lines:
        lines.append('')
        lines.append('💈 Per Capster:')
        lines.extend(capster_lines)

    return '\n'.join(lines)


# ── Weekly ─────────────────────────────────────────────────────────────────── #

def weekly_report(end_dt: Optional[datetime] = None) -> str:
    """Report 7 hari terakhir (rolling window) sampai dengan end_dt."""
    end_dt = end_dt or datetime.now()
    start_dt = (end_dt - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_exclusive = (end_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    repo = Repository()
    df = repo.get_transactions_by_range(start_dt, end_exclusive)

    header = (
        f"📊 Laporan Mingguan — "
        f"{fmt_date(start_dt)} s/d {fmt_date(end_dt)}"
    )
    if df.empty:
        return f"{header}\n\nBelum ada transaksi."

    total = int(df['Price'].sum())
    count = len(df)

    lines = [
        header,
        '',
        f"💰 Total: {fmt_idr(total)}",
        f"🧾 Transaksi: {count}",
        '',
        '📅 Per Hari:',
    ]
    df_copy = df.copy()
    df_copy['_d'] = df_copy['Date'].dt.strftime('%a %d-%m')
    daily_grp = df_copy.groupby('_d', sort=False)['Price'].agg(['sum', 'count'])
    # ensure chronological order
    df_copy['_dkey'] = df_copy['Date'].dt.date
    order = df_copy[['_d', '_dkey']].drop_duplicates().sort_values('_dkey')['_d'].tolist()
    for d in order:
        row = daily_grp.loc[d]
        lines.append(f"  • {d}: {fmt_idr(row['sum'])} ({int(row['count'])} trx)")

    branch_lines = _branch_breakdown(df)
    if branch_lines:
        lines.append('')
        lines.append('🏪 Per Cabang:')
        lines.extend(branch_lines)

    return '\n'.join(lines)


# ── Monthly ────────────────────────────────────────────────────────────────── #

def monthly_report(year: Optional[int] = None, month: Optional[int] = None) -> str:
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    repo = Repository()
    df = repo.get_transactions_by_month(year, month)

    header = f"🗓️ Laporan Bulanan — {fmt_month_id(year, month)}"
    if df.empty:
        return f"{header}\n\nBelum ada transaksi."

    total = int(df['Price'].sum())
    count = len(df)

    lines = [
        header,
        '',
        f"💰 Total: {fmt_idr(total)}",
        f"🧾 Transaksi: {count}",
    ]
    branch_lines = _branch_breakdown(df)
    if branch_lines:
        lines.append('')
        lines.append('🏪 Per Cabang:')
        lines.extend(branch_lines)

    capster_lines = _capster_breakdown(df)
    if capster_lines:
        lines.append('')
        lines.append('💈 Per Capster:')
        lines.extend(capster_lines)

    return '\n'.join(lines)


# ── Profit ─────────────────────────────────────────────────────────────────── #

def profit_report(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """
    Profit per cabang = revenue − biaya operasional tetap − gaji capster tetap − komisi mitra.
    Pakai service yang sama dengan dashboard web (app/services/reports.py).
    """
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    repo = Repository()
    data = calc_profit(repo, year, month)

    header = f"💹 Profit Per Cabang — {fmt_month_id(year, month)}"
    if not data:
        return f"{header}\n\nBelum ada transaksi bulan ini."

    lines = [header, '']
    for short, b in data['branches'].items():
        lines.append(f"🏪 {short}")
        lines.append(f"  Pendapatan : {fmt_idr(b['revenue'])}")
        lines.append(f"  Biaya Tetap: {fmt_idr(b['fixed_total'])}")
        if b['commission']:
            lines.append(f"  Komisi     : {fmt_idr(b['commission'])}")
        lines.append(f"  Profit     : {fmt_idr(b['net_profit'])}  ({b['tx_count']} trx)")
        lines.append('')

    o = data['overall']
    lines.append(f"TOTAL Pendapatan : {fmt_idr(o['revenue'])}")
    lines.append(f"TOTAL Biaya Tetap: {fmt_idr(o['fixed'])}")
    lines.append(f"TOTAL Komisi     : {fmt_idr(o['commission'])}")
    lines.append(f"TOTAL Profit     : {fmt_idr(o['net_profit'])}")
    return '\n'.join(lines)


# ── Per Capster ────────────────────────────────────────────────────────────── #

def capster_report(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Breakdown per capster bulan ini: revenue, jumlah trx, estimasi komisi."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    repo = Repository()
    df = repo.get_transactions_by_month(year, month)
    capsters = repo.get_all_capsters()

    header = f"💈 Breakdown Capster — {fmt_month_id(year, month)}"
    if df.empty:
        return f"{header}\n\nBelum ada transaksi."

    # Build lookup: lowercased name/alias -> capster info
    info_by_key = {}
    for c in capsters:
        info = {
            'name': c.get('Name', ''),
            'type': (c.get('EmploymentType') or 'mitra').lower().strip(),
            'rate': float(c.get('CommissionRate') or 0.5),
            'salary': int(float(c.get('MonthlySalary') or 0)),
        }
        for k in (c.get('Name', ''), c.get('Alias', '')):
            k = (k or '').lower().strip()
            if k:
                info_by_key[k] = info

    lines = [header, '']
    grouped = (
        df.groupby('Capster')['Price']
        .agg(['sum', 'count'])
        .sort_values('sum', ascending=False)
    )
    for capster_name, row in grouped.iterrows():
        revenue = int(row['sum'])
        count = int(row['count'])
        info = info_by_key.get((capster_name or '').lower().strip())

        if info:
            if info['type'] == 'mitra':
                est_komisi = int(revenue * info['rate'])
                line2 = f"     Komisi (est.): {fmt_idr(est_komisi)} ({int(info['rate'] * 100)}%)"
            else:
                line2 = f"     Gaji tetap: {fmt_idr(info['salary'])}/bln"
        else:
            line2 = "     (capster tidak terdaftar)"

        lines.append(f"  • {capster_name}: {fmt_idr(revenue)} ({count} trx)")
        lines.append(line2)

    lines.append('')
    lines.append('*) Komisi estimasi rata-rata. Detail akurat per layanan di dashboard.')
    return '\n'.join(lines)
