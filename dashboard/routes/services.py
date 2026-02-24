"""Service CRUD management page."""
import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from dashboard.auth import login_required
from app.db.repository import Repository

services_bp = Blueprint('services', __name__)


def _make_service_id(name: str) -> str:
    """PascalCase dari nama layanan — sama persis dengan ConfigService._make_service_id."""
    words = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
    return ''.join(w.capitalize() for w in words)


@services_bp.route('/services')
@login_required
def service_manage():
    db  = Repository()
    raw = db.get_all_services()

    services = []
    for s in raw:
        try:
            price = int(float(s.get('Price', 0)))
        except (ValueError, TypeError):
            price = 0
        services.append({
            'service_id': s.get('ServiceID', ''),
            'name':       s.get('Name', ''),
            'category':   (s.get('Category') or 'main').lower(),
            'price':      price,
        })

    # Pisah per kategori untuk tampilan
    main_services     = [s for s in services if s['category'] == 'main']
    coloring_services = [s for s in services if s['category'] == 'coloring']

    return render_template(
        'service_manage.html',
        main_services=main_services,
        coloring_services=coloring_services,
        total=len(services),
        active_page='services',
        now=datetime.now(),
    )


@services_bp.route('/services/add', methods=['POST'])
@login_required
def service_add():
    db   = Repository()
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nama layanan tidak boleh kosong.', 'danger')
        return redirect(url_for('services.service_manage'))

    category = request.form.get('category', 'main').strip().lower()
    if category not in ('main', 'coloring'):
        category = 'main'

    try:
        price = int(float(request.form.get('price', '0').replace('.', '').replace(',', '')))
        if price < 0:
            raise ValueError
    except (ValueError, TypeError):
        flash('Harga tidak valid.', 'danger')
        return redirect(url_for('services.service_manage'))

    service_id = _make_service_id(name)

    # Cek duplikat
    existing = db.get_all_services()
    if any(s.get('ServiceID') == service_id for s in existing):
        flash(f"Layanan '{name}' (ID: {service_id}) sudah terdaftar.", 'warning')
        return redirect(url_for('services.service_manage'))

    if db.add_service(service_id, name, category, price):
        flash(f"Layanan '{name}' berhasil ditambahkan.", 'success')
    else:
        flash('Gagal menambahkan layanan.', 'danger')
    return redirect(url_for('services.service_manage'))


@services_bp.route('/services/edit/<service_id>', methods=['POST'])
@login_required
def service_edit(service_id):
    db = Repository()

    name = request.form.get('name', '').strip() or None

    category = request.form.get('category', '').strip().lower()
    category = category if category in ('main', 'coloring') else None

    try:
        price = int(float(request.form.get('price', '').replace('.', '').replace(',', '')))
        if price < 0:
            price = None
    except (ValueError, TypeError):
        price = None

    fields = {}
    if name is not None:
        fields['name'] = name
    if category is not None:
        fields['category'] = category
    if price is not None:
        fields['price'] = price

    if not fields:
        flash('Tidak ada perubahan.', 'info')
        return redirect(url_for('services.service_manage'))

    if db.update_service(service_id, **fields):
        flash('Layanan berhasil diperbarui.', 'success')
    else:
        flash('Gagal memperbarui layanan.', 'danger')
    return redirect(url_for('services.service_manage'))


@services_bp.route('/services/delete/<service_id>', methods=['POST'])
@login_required
def service_delete(service_id):
    db  = Repository()
    raw = db.get_all_services()
    name = next((s['Name'] for s in raw if s.get('ServiceID') == service_id), service_id)

    if db.remove_service(service_id):
        flash(f"Layanan '{name}' berhasil dihapus.", 'success')
    else:
        flash('Gagal menghapus layanan.', 'danger')
    return redirect(url_for('services.service_manage'))
