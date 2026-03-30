"""Promo management — owner CRUD."""
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from dashboard.auth import login_required
from app.db.repository import Repository
from app.config.constants import BRANCHES

promos_bp = Blueprint('promos', __name__)


@promos_bp.route('/promos')
@login_required
def promo_manage():
    db       = Repository()
    promos   = db.get_all_promos()
    services = db.get_all_services()
    now      = datetime.now()

    # Pisah aktif / tidak aktif
    today_str = now.strftime('%Y-%m-%d')
    active_promos   = [p for p in promos if p['is_active'] and p['end_date'] >= today_str]
    inactive_promos = [p for p in promos if not p['is_active'] or p['end_date'] < today_str]

    return render_template(
        'promo_manage.html',
        active_promos=active_promos,
        inactive_promos=inactive_promos,
        services=services,
        branches=BRANCHES,
        now=now,
        active_page='promos',
    )


@promos_bp.route('/promos/add', methods=['POST'])
@login_required
def promo_add():
    db   = Repository()
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nama promo tidak boleh kosong.', 'danger')
        return redirect(url_for('promos.promo_manage'))

    try:
        discount_pct = float(request.form.get('discount_pct', '0').replace(',', '.'))
        if not (0 < discount_pct < 100):
            raise ValueError
    except (ValueError, TypeError):
        flash('Diskon harus antara 1–99%.', 'danger')
        return redirect(url_for('promos.promo_manage'))

    start_str = request.form.get('start_date', '').strip()
    end_str   = request.form.get('end_date', '').strip()
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date   = datetime.strptime(end_str, '%Y-%m-%d').date()
        if end_date < start_date:
            raise ValueError
    except (ValueError, TypeError):
        flash('Tanggal tidak valid atau tanggal selesai sebelum tanggal mulai.', 'danger')
        return redirect(url_for('promos.promo_manage'))

    service_ids = request.form.getlist('service_ids')
    if not service_ids:
        flash('Pilih minimal satu layanan.', 'danger')
        return redirect(url_for('promos.promo_manage'))

    branch_ids_raw = request.form.getlist('branch_ids')
    # 'ALL' special value means all branches
    if not branch_ids_raw or 'ALL' in branch_ids_raw:
        branch_ids = ['ALL']
    else:
        branch_ids = branch_ids_raw

    if db.add_promo(name, discount_pct, start_date, end_date, service_ids, branch_ids):
        flash(f"Promo '{name}' berhasil ditambahkan.", 'success')
    else:
        flash('Gagal menambahkan promo.', 'danger')
    return redirect(url_for('promos.promo_manage'))


@promos_bp.route('/promos/<int:promo_id>/edit', methods=['POST'])
@login_required
def promo_edit(promo_id):
    db   = Repository()
    name = request.form.get('name', '').strip() or None

    fields = {}
    if name:
        fields['name'] = name

    try:
        discount_pct = float(request.form.get('discount_pct', '').replace(',', '.'))
        if 0 < discount_pct < 100:
            fields['discount_pct'] = discount_pct
    except (ValueError, TypeError):
        pass

    start_str = request.form.get('start_date', '').strip()
    end_str   = request.form.get('end_date', '').strip()
    try:
        fields['start_date'] = datetime.strptime(start_str, '%Y-%m-%d').date()
        fields['end_date']   = datetime.strptime(end_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        pass

    service_ids = request.form.getlist('service_ids')
    if service_ids:
        fields['service_ids'] = service_ids

    branch_ids_raw = request.form.getlist('branch_ids')
    if branch_ids_raw:
        fields['branch_ids'] = ['ALL'] if 'ALL' in branch_ids_raw else branch_ids_raw

    # is_active toggle
    is_active = request.form.get('is_active')
    if is_active is not None:
        fields['is_active'] = is_active == '1'

    if db.update_promo(promo_id, **fields):
        flash('Promo berhasil diperbarui.', 'success')
    else:
        flash('Gagal memperbarui promo.', 'danger')
    return redirect(url_for('promos.promo_manage'))


@promos_bp.route('/promos/<int:promo_id>/delete', methods=['POST'])
@login_required
def promo_delete(promo_id):
    db = Repository()
    if db.delete_promo(promo_id):
        flash('Promo berhasil dihapus.', 'success')
    else:
        flash('Promo tidak ditemukan.', 'danger')
    return redirect(url_for('promos.promo_manage'))
