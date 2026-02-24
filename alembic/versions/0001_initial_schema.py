"""Initial schema — 7 tables + seed data

Revision ID: 0001
Revises:
Create Date: 2026-02-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Create tables                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('capster_name', sa.String(100), nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('payment_method', sa.String(20), nullable=False, server_default='Cash'),
        sa.Column('branch', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_date', 'transactions', ['date'])
    op.create_index('ix_transactions_branch', 'transactions', ['branch'])
    op.create_index('ix_transactions_capster_date', 'transactions', ['capster_name', 'date'])

    op.create_table(
        'capsters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('alias', sa.String(100), nullable=True, server_default=''),
        sa.Column('employment_type', sa.String(20), nullable=False, server_default='mitra'),
        sa.Column('commission_rate', sa.Float(), nullable=False, server_default='0.5'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id', name='uq_capsters_telegram_id'),
        sa.CheckConstraint("employment_type IN ('mitra', 'tetap')", name='ck_capsters_employment_type'),
    )

    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(30), nullable=True, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'services',
        sa.Column('service_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(20), nullable=False, server_default='main'),
        sa.Column('price', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('service_id'),
        sa.CheckConstraint("category IN ('main', 'coloring')", name='ck_services_category'),
    )

    op.create_table(
        'branches',
        sa.Column('branch_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('location', sa.String(100), nullable=True, server_default=''),
        sa.Column('short', sa.String(50), nullable=True, server_default=''),
        sa.Column('employees', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('commission_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cost_tempat', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_listrik_air', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_wifi', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_karyawan', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('branch_id'),
    )

    op.create_table(
        'products',
        sa.Column('product_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('product_id'),
    )

    op.create_table(
        'salary_withdrawals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('capster_name', sa.String(100), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_salary_telegram_period', 'salary_withdrawals',
        ['telegram_id', 'period_start', 'period_end']
    )

    # ------------------------------------------------------------------ #
    # Seed data                                                            #
    # ------------------------------------------------------------------ #
    services_table = sa.table(
        'services',
        sa.column('service_id', sa.String),
        sa.column('name', sa.String),
        sa.column('category', sa.String),
        sa.column('price', sa.Integer),
    )
    op.bulk_insert(services_table, [
        {'service_id': 'Potong',          'name': 'Potong Rambut',      'category': 'main',     'price': 25000},
        {'service_id': 'PotongCuci',      'name': 'Potong + Cuci',      'category': 'main',     'price': 30000},
        {'service_id': 'PotongAnak',      'name': 'Potong Anak',        'category': 'main',     'price': 20000},
        {'service_id': 'PotongAnakCuci',  'name': 'Potong & Cuci Anak', 'category': 'main',     'price': 25000},
        {'service_id': 'PotongBapakAnak', 'name': 'Potong Bapak & Anak','category': 'main',     'price': 40000},
        {'service_id': 'ColoringHighlights','name': 'Highlights',       'category': 'coloring', 'price': 60000},
        {'service_id': 'ColoringFull',    'name': 'Full Color',         'category': 'coloring', 'price': 200000},
        {'service_id': 'BlackColor',      'name': 'Black',              'category': 'coloring', 'price': 40000},
        {'service_id': 'ColoringBleaching','name': 'Bleaching',         'category': 'coloring', 'price': 45000},
    ])

    branches_table = sa.table(
        'branches',
        sa.column('branch_id', sa.String),
        sa.column('name', sa.String),
        sa.column('location', sa.String),
        sa.column('short', sa.String),
        sa.column('employees', sa.Integer),
        sa.column('commission_rate', sa.Float),
        sa.column('cost_tempat', sa.Integer),
        sa.column('cost_listrik_air', sa.Integer),
        sa.column('cost_wifi', sa.Integer),
        sa.column('cost_karyawan', sa.Integer),
    )
    op.bulk_insert(branches_table, [
        {
            'branch_id': 'cabang_a', 'name': 'Cabang Denailla',
            'location': 'Mojosari', 'short': 'Cabang A',
            'employees': 2, 'commission_rate': 0.0,
            'cost_tempat': 520000, 'cost_listrik_air': 400000,
            'cost_wifi': 15000, 'cost_karyawan': 2500000,
        },
        {
            'branch_id': 'cabang_b', 'name': 'Cabang Sumput',
            'location': 'Sumput', 'short': 'Cabang B',
            'employees': 2, 'commission_rate': 0.5,
            'cost_tempat': 792000, 'cost_listrik_air': 350000,
            'cost_wifi': 30000, 'cost_karyawan': 0,
        },
    ])

    products_table = sa.table(
        'products',
        sa.column('product_id', sa.String),
        sa.column('name', sa.String),
        sa.column('price', sa.Integer),
    )
    op.bulk_insert(products_table, [
        {'product_id': 'Pomade',    'name': 'Pomade',     'price': 55000},
        {'product_id': 'Powder',    'name': 'Powder',     'price': 15000},
        {'product_id': 'HairTonic', 'name': 'Hair Tonic', 'price': 25000},
    ])


def downgrade() -> None:
    op.drop_index('ix_salary_telegram_period', table_name='salary_withdrawals')
    op.drop_table('salary_withdrawals')
    op.drop_table('products')
    op.drop_table('branches')
    op.drop_table('services')
    op.drop_table('customers')
    op.drop_table('capsters')
    op.drop_index('ix_transactions_capster_date', table_name='transactions')
    op.drop_index('ix_transactions_branch', table_name='transactions')
    op.drop_index('ix_transactions_date', table_name='transactions')
    op.drop_table('transactions')
