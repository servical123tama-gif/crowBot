"""Product CRUD management page."""
import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from dashboard.auth import login_required
from app.db.repository import Repository

products_bp = Blueprint('products', __name__)


def _make_product_id(name: str) -> str:
    """PascalCase dari nama produk — sama dengan pola service_id."""
    words = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
    return ''.join(w.capitalize() for w in words)


@products_bp.route('/products')
@login_required
def product_manage():
    db  = Repository()
    raw = db.get_all_products()

    products = []
    for p in raw:
        try:
            price = int(float(p.get('Price', 0)))
        except (ValueError, TypeError):
            price = 0
        products.append({
            'product_id': p.get('ProductID', ''),
            'name':       p.get('Name', ''),
            'price':      price,
        })

    products.sort(key=lambda x: x['name'])

    return render_template(
        'product_manage.html',
        products=products,
        active_page='products',
        now=datetime.now(),
    )


@products_bp.route('/products/add', methods=['POST'])
@login_required
def product_add():
    db   = Repository()
    name = request.form.get('name', '').strip()
    if not name:
        flash('Nama produk tidak boleh kosong.', 'danger')
        return redirect(url_for('products.product_manage'))

    try:
        price = int(float(request.form.get('price', '0') or '0'))
        if price < 0:
            raise ValueError
    except (ValueError, TypeError):
        flash('Harga tidak valid.', 'danger')
        return redirect(url_for('products.product_manage'))

    product_id = _make_product_id(name)

    # Cek duplikat
    if any(p.get('ProductID') == product_id for p in db.get_all_products()):
        flash(f"Produk '{name}' (ID: {product_id}) sudah terdaftar.", 'warning')
        return redirect(url_for('products.product_manage'))

    if db.add_product(product_id, name, price):
        flash(f"Produk '{name}' berhasil ditambahkan.", 'success')
    else:
        flash('Gagal menambahkan produk.', 'danger')
    return redirect(url_for('products.product_manage'))


@products_bp.route('/products/edit/<product_id>', methods=['POST'])
@login_required
def product_edit(product_id):
    db     = Repository()
    fields = {}

    name = request.form.get('name', '').strip()
    if name:
        fields['name'] = name

    try:
        price = int(float(request.form.get('price', '') or ''))
        if price >= 0:
            fields['price'] = price
    except (ValueError, TypeError):
        pass

    if not fields:
        flash('Tidak ada perubahan.', 'info')
        return redirect(url_for('products.product_manage'))

    if db.update_product(product_id, **fields):
        flash('Produk berhasil diperbarui.', 'success')
    else:
        flash('Gagal memperbarui produk.', 'danger')
    return redirect(url_for('products.product_manage'))


@products_bp.route('/products/delete/<product_id>', methods=['POST'])
@login_required
def product_delete(product_id):
    db   = Repository()
    name = next(
        (p['Name'] for p in db.get_all_products() if p.get('ProductID') == product_id),
        product_id,
    )
    if db.remove_product(product_id):
        flash(f"Produk '{name}' berhasil dihapus.", 'success')
    else:
        flash('Gagal menghapus produk.', 'danger')
    return redirect(url_for('products.product_manage'))
