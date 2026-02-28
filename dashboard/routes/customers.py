"""Customer management routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from dashboard.auth import login_required
from app.db.repository import Repository

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/customers')
@login_required
def customers_list():
    repo = Repository()
    all_customers = repo.get_all_customers()

    search = request.args.get('q', '').strip().lower()
    if search:
        all_customers = [
            c for c in all_customers
            if search in c['Name'].lower() or search in c['Phone'].lower()
        ]

    return render_template(
        'customers.html',
        customers=all_customers,
        search=search,
        total=len(all_customers),
        active_page='customers',
    )


@customers_bp.route('/customers/add', methods=['POST'])
@login_required
def customer_add():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()

    if not name:
        flash('Nama customer wajib diisi.', 'danger')
        return redirect(url_for('customers.customers_list'))

    repo = Repository()

    class _C:
        pass

    c = _C()
    c.name = name
    c.phone = phone
    repo.add_customer(c)

    flash(f'Customer "{name}" berhasil ditambahkan.', 'success')
    return redirect(url_for('customers.customers_list'))


@customers_bp.route('/customers/<int:cid>/edit', methods=['POST'])
@login_required
def customer_edit(cid):
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()

    if not name:
        flash('Nama customer wajib diisi.', 'danger')
        return redirect(url_for('customers.customers_list'))

    repo = Repository()
    ok = repo.update_customer(cid, name, phone)

    if ok:
        flash(f'Customer "{name}" berhasil diupdate.', 'success')
    else:
        flash('Customer tidak ditemukan.', 'danger')
    return redirect(url_for('customers.customers_list'))


@customers_bp.route('/customers/<int:cid>/qr.png')
@login_required
def customer_qr(cid):
    repo = Repository()
    png  = repo.generate_customer_qr_png(cid)
    return Response(png, mimetype='image/png')


@customers_bp.route('/customers/<int:cid>/delete', methods=['POST'])
@login_required
def customer_delete(cid):
    repo = Repository()
    ok = repo.delete_customer(cid)

    if ok:
        flash('Customer berhasil dihapus.', 'success')
    else:
        flash('Customer tidak ditemukan.', 'danger')
    return redirect(url_for('customers.customers_list'))
