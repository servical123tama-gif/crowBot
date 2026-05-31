"""Product CRUD management page + stock management."""
import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from web.auth import login_required
from app.db.repository import Repository
from app.config.constants import BRANCHES

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
        commission_rate = p.get('CommissionRate', 0.0)
        products.append({
            'product_id':      p.get('ProductID', ''),
            'name':            p.get('Name', ''),
            'price':           p.get('Price', 0),
            'commission_rate': commission_rate,
            'commission_pct':  int(commission_rate * 100),
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

    try:
        commission_rate = float(request.form.get('commission_rate', '0') or '0') / 100
        commission_rate = max(0.0, min(1.0, commission_rate))
    except (ValueError, TypeError):
        commission_rate = 0.0

    if db.add_product(product_id, name, price, commission_rate=commission_rate):
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

    commission_rate_str = request.form.get('commission_rate', '').strip()
    if commission_rate_str:
        try:
            cr = float(commission_rate_str) / 100
            fields['commission_rate'] = max(0.0, min(1.0, cr))
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


# ── Stock Management ────────────────────────────────────────────────────────

@products_bp.route('/products/stock')
@login_required
def product_stock():
    db = Repository()
    raw_products = db.get_all_products()

    branches_list = [
        {'id': bid, 'name': bcfg.get('name', bid), 'short': bcfg.get('short', bid)}
        for bid, bcfg in BRANCHES.items()
    ]

    # Build per-branch stock map: {branch_id: [{product_id, name, price, commission_pct, quantity}]}
    stock_by_branch = {}
    for b in branches_list:
        stocks = db.get_product_stocks(branch_id=b['id'])
        stock_map = {s['ProductID']: s['Quantity'] for s in stocks}
        rows = []
        for p in raw_products:
            try:
                price = int(float(p.get('Price', 0)))
            except (ValueError, TypeError):
                price = 0
            rows.append({
                'product_id':      p['ProductID'],
                'name':            p['Name'],
                'price':           price,
                'commission_pct':  int(float(p.get('CommissionRate', 0)) * 100),
                'quantity':        stock_map.get(p['ProductID'], 0),
            })
        rows.sort(key=lambda x: x['name'])
        stock_by_branch[b['id']] = rows

    return render_template(
        'product_stock.html',
        branches=branches_list,
        stock_by_branch=stock_by_branch,
        active_page='product_stock',
        now=datetime.now(),
    )


@products_bp.route('/products/stock/set', methods=['POST'])
@login_required
def product_stock_set():
    db         = Repository()
    product_id = request.form.get('product_id', '').strip()
    branch_id  = request.form.get('branch_id', '').strip()
    try:
        quantity = int(float(request.form.get('quantity', '0') or '0'))
    except (ValueError, TypeError):
        quantity = 0

    if not product_id or not branch_id:
        flash('Data tidak lengkap.', 'danger')
        return redirect(url_for('products.product_stock'))

    if db.set_stock(product_id, branch_id, quantity):
        flash('Stok berhasil diperbarui.', 'success')
    else:
        flash('Gagal memperbarui stok.', 'danger')
    return redirect(url_for('products.product_stock', branch=branch_id))
