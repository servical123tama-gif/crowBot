b"""Branch CRUD management page."""
import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from dashboard.auth import login_required
from app.db.repository import Repository

branches_bp = Blueprint('branches', __name__)


def _make_branch_id(name: str) -> str:
    """snake_case dari nama cabang — contoh: 'Cabang Baru' → 'cabang_baru'."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
    return slug


def _parse_int(val, default=0) -> int:
    try:
        return int(float(str(val).replace('.', '').replace(',', '') or default))
    except (ValueError, TypeError):
        return default


def _parse_float(val, default=0.0) -> float:
    try:
        return float(str(val).replace(',', '.') or default)
    except (ValueError, TypeError):
        return default


@branches_bp.route('/branches')
@login_required
def branch_manage():
    db  = Repository()
    raw = db.get_all_branches_config()

    # Hitung gaji tetap per branch dari data capster
    tetap_salary_by_branch: dict[str, int] = {}
    tetap_names_by_branch:  dict[str, list] = {}
    seen_names: set = set()
    for c in db.get_all_capsters():
        if (c.get('EmploymentType') or 'mitra').lower() != 'tetap':
            continue
        cname = c.get('Name', '')
        if not cname or cname in seen_names:
            continue
        seen_names.add(cname)
        bid = (c.get('BranchID') or '').strip()
        salary = c.get('MonthlySalary', 0)
        tetap_salary_by_branch[bid] = tetap_salary_by_branch.get(bid, 0) + salary
        tetap_names_by_branch.setdefault(bid, []).append(cname)

    branches = []
    for b in raw:
        bid = b.get('BranchID', '')
        branches.append({
            'branch_id':       bid,
            'name':            b.get('Name', ''),
            'location':        b.get('Location', ''),
            'short':           b.get('Short', ''),
            'employees':       b.get('Employees', 2),
            'commission_rate': b.get('CommissionRate', 0.0),
            'commission_pct':  int(b.get('CommissionRate', 0.0) * 100),
            'cost_tempat':     b.get('Cost_tempat', 0),
            'cost_listrik_air':b.get('Cost_listrik_air', 0),
            'cost_wifi':       b.get('Cost_wifi', 0),
            'tetap_salary':    tetap_salary_by_branch.get(bid, 0),
            'tetap_names':     tetap_names_by_branch.get(bid, []),
        })

    return render_template(
        'branch_manage.html',
        branches=branches,
        active_page='branches',
        now=datetime.now(),
    )


@branches_bp.route('/branches/add', methods=['POST'])
@login_required
def branch_add():
    db   = Repository()
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nama cabang tidak boleh kosong.', 'danger')
        return redirect(url_for('branches.branch_manage'))

    branch_id = _make_branch_id(name)

    # Cek duplikat
    existing = db.get_all_branches_config()
    if any(b.get('BranchID') == branch_id for b in existing):
        flash(f"Cabang dengan ID '{branch_id}' sudah ada. Gunakan nama yang berbeda.", 'warning')
        return redirect(url_for('branches.branch_manage'))

    short            = request.form.get('short', '').strip()
    location         = request.form.get('location', '').strip()
    employees        = _parse_int(request.form.get('employees', '2'), 2)
    commission_pct   = _parse_float(request.form.get('commission_rate', '0'))
    commission_rate  = commission_pct / 100.0
    cost_tempat      = _parse_int(request.form.get('cost_tempat', '0'))
    cost_listrik_air = _parse_int(request.form.get('cost_listrik_air', '0'))
    cost_wifi        = _parse_int(request.form.get('cost_wifi', '0'))

    if db.add_branch(branch_id, name, location=location, short=short,
                     employees=employees, commission_rate=commission_rate,
                     cost_tempat=cost_tempat, cost_listrik_air=cost_listrik_air,
                     cost_wifi=cost_wifi, cost_karyawan=0):
        flash(f"Cabang '{name}' berhasil ditambahkan (ID: {branch_id}).", 'success')
    else:
        flash('Gagal menambahkan cabang.', 'danger')
    return redirect(url_for('branches.branch_manage'))


@branches_bp.route('/branches/edit/<branch_id>', methods=['POST'])
@login_required
def branch_edit(branch_id):
    db = Repository()

    fields = {}

    name = request.form.get('name', '').strip()
    if name:
        fields['name'] = name

    short = request.form.get('short', '').strip()
    fields['short'] = short          # allow clearing

    location = request.form.get('location', '').strip()
    fields['location'] = location    # allow clearing

    employees = _parse_int(request.form.get('employees', ''), -1)
    if employees >= 0:
        fields['employees'] = employees

    commission_pct = request.form.get('commission_rate', '').strip()
    if commission_pct:
        fields['CommissionRate'] = _parse_float(commission_pct) / 100.0

    cost_tempat = request.form.get('cost_tempat', '').strip()
    if cost_tempat:
        fields['cost_tempat'] = _parse_int(cost_tempat)

    cost_listrik_air = request.form.get('cost_listrik_air', '').strip()
    if cost_listrik_air:
        fields['cost_listrik_air'] = _parse_int(cost_listrik_air)

    cost_wifi = request.form.get('cost_wifi', '').strip()
    if cost_wifi:
        fields['cost_wifi'] = _parse_int(cost_wifi)

    if not fields:
        flash('Tidak ada perubahan.', 'info')
        return redirect(url_for('branches.branch_manage'))

    if db.update_branch_config(branch_id, **fields):
        flash('Data cabang berhasil diperbarui.', 'success')
    else:
        flash('Gagal memperbarui data cabang.', 'danger')
    return redirect(url_for('branches.branch_manage'))


@branches_bp.route('/branches/delete/<branch_id>', methods=['POST'])
@login_required
def branch_delete(branch_id):
    db   = Repository()
    raw  = db.get_all_branches_config()
    name = next((b['Name'] for b in raw if b.get('BranchID') == branch_id), branch_id)

    if db.remove_branch(branch_id):
        flash(f"Cabang '{name}' berhasil dihapus.", 'success')
    else:
        flash('Gagal menghapus cabang.', 'danger')
    return redirect(url_for('branches.branch_manage'))
