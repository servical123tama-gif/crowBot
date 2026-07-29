"""
Report calculations untuk web dashboard.

Pure functions: terima Repository sebagai parameter, return data dict.
Tidak boleh impor Flask.
"""
from typing import Dict, Any

from app.db.repository import Repository


def build_capster_lookup(repo: Repository) -> Dict[str, Dict[str, Any]]:
    """
    Bangun lookup capster: name/alias (lowercased) → {employment_type, commission_rate, monthly_salary, branch_id, name}
    """
    lookup: Dict[str, Dict[str, Any]] = {}
    for c in repo.get_all_capsters():
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
        for key in (c.get('Name', ''), c.get('Alias', '')):
            k = (key or '').lower().strip()
            if k:
                lookup[k] = info
    return lookup


def calc_profit(repo: Repository, year: int, month: int) -> Dict[str, Any]:
    """
    Hitung profit per cabang untuk bulan tertentu.

    Sumber data:
      - Branches config (nama, biaya operasional) → DB tabel `branches`
      - Capster salary (tetap) → DB tabel `capsters`
      - Transaksi → DB tabel `transactions`

    Return:
        {
          'branches': { short_name: { revenue, fixed_ops, tetap_lines,
                                       tetap_total, fixed_total, mitra_lines,
                                       commission, total_cost, net_profit, tx_count, ... } },
          'overall':  { revenue, fixed, salary, commission, total_cost, net_profit }
        }
        Atau {} bila tidak ada transaksi di bulan tersebut.
    """
    df = repo.get_transactions_dataframe(year=year)
    if df.empty:
        return {}

    month_str = f"{year:04d}-{month:02d}"
    monthly_df = df[df['Date'].dt.strftime('%Y-%m') == month_str]
    if monthly_df.empty or 'Branch' not in monthly_df.columns:
        return {}

    capster_lookup = build_capster_lookup(repo)
    results: Dict[str, Dict[str, Any]] = {}
    overall = {'revenue': 0, 'fixed': 0, 'salary': 0, 'commission': 0}

    # Iterate branches dari DB (bukan constants) → biaya operasional live per edit UI
    for branch_cfg in repo.get_all_branches_config():
        branch_id = branch_cfg.get('BranchID', '')
        short     = branch_cfg.get('Short') or branch_id
        branch_df = monthly_df[monthly_df['Branch'] == branch_id]
        revenue   = int(branch_df['Price'].sum())

        # Fixed operational (non-karyawan) — dari kolom DB, admin bisa edit via /branches
        fixed_ops = (
            int(branch_cfg.get('Cost_tempat', 0) or 0)
            + int(branch_cfg.get('Cost_listrik_air', 0) or 0)
            + int(branch_cfg.get('Cost_wifi', 0) or 0)
        )

        # Tetap salary for this branch — dari capster.monthly_salary
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
                cap_rev = int(cap_df['Price'].sum())
                info    = capster_lookup.get(cap_name.lower().strip())
                if info and info['employment_type'] == 'mitra':
                    rate    = info['commission_rate']
                    cap_com = int(cap_rev * rate)
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
            'name':         branch_cfg.get('Name', short),
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
