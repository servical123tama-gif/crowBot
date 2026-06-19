"""
SQLAlchemy ORM Models — 7 tables
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Date, DateTime,
    Text, Index, CheckConstraint, UniqueConstraint, Boolean
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    # capster_name is a raw string (NOT FK) for backward compat with alias system
    capster_name = Column(String(100), nullable=False)
    service_name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False, default=0)
    payment_method = Column(String(20), nullable=False, default='Cash')
    branch = Column(String(50), nullable=True)
    customer_id = Column(Integer, nullable=True)
    promo_name  = Column(String(100), nullable=True, default='')
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_transactions_date', 'date'),
        Index('ix_transactions_branch', 'branch'),
        Index('ix_transactions_capster_date', 'capster_name', 'date'),
    )

    def __repr__(self):
        return f"<Transaction id={self.id} date={self.date} capster={self.capster_name} service={self.service_name}>"


class Capster(Base):
    __tablename__ = 'capsters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    alias = Column(String(100), nullable=True, default='')
    username = Column(String(50), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=True)
    employment_type = Column(String(20), nullable=False, default='mitra')
    commission_rate = Column(Float, nullable=False, default=0.5)
    monthly_salary = Column(Integer, nullable=False, default=0)
    branch_id = Column(String(50), nullable=True, default='')

    __table_args__ = (
        UniqueConstraint('telegram_id', name='uq_capsters_telegram_id'),
        CheckConstraint("employment_type IN ('mitra', 'tetap')", name='ck_capsters_employment_type'),
    )

    def __repr__(self):
        return f"<Capster id={self.id} name={self.name} telegram_id={self.telegram_id}>"


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True, default='')
    visit_count = Column(Integer, nullable=False, default=0)
    point_balance = Column(Integer, nullable=False, default=0)  # poin loyalty (reset setelah klaim)
    added_by = Column(String(100), nullable=True, default='')
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)

    def __repr__(self):
        return f"<Customer id={self.id} name={self.name}>"


class LoyaltyClaim(Base):
    """Riwayat klaim poin loyalty oleh customer."""
    __tablename__ = 'loyalty_claims'

    id             = Column(Integer, primary_key=True, autoincrement=True)
    customer_id    = Column(Integer, nullable=False)
    claim_type     = Column(String(20), nullable=False)   # '50pct' | 'free'
    points_used    = Column(Integer, nullable=False)       # 5 atau 10
    claimed_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    transaction_id = Column(Integer, nullable=True)        # transaksi yang menggunakan klaim ini

    __table_args__ = (
        Index('ix_loyalty_customer', 'customer_id'),
    )


class LoyaltyAudit(Base):
    """Audit trail setiap perubahan point_balance customer.

    Setiap row = 1 event delta. Read-only (jangan UPDATE/DELETE).
    Reasons: 'transaction', 'claim_50pct', 'claim_free', 'manual_edit', 'sync'.
    """
    __tablename__ = 'loyalty_audits'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    customer_id     = Column(Integer, nullable=False)
    delta           = Column(Integer, nullable=False)        # +1, -5, dll.
    before_balance  = Column(Integer, nullable=False)
    after_balance   = Column(Integer, nullable=False)
    reason          = Column(String(30), nullable=False)
    actor           = Column(String(100), nullable=True, default='')
    transaction_id  = Column(Integer, nullable=True)
    note            = Column(Text, nullable=True, default='')
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_loyalty_audit_customer', 'customer_id'),
        Index('ix_loyalty_audit_created', 'created_at'),
    )


class Service(Base):
    __tablename__ = 'services'

    service_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False, default='main')
    price = Column(Integer, nullable=False, default=0)
    commission_rate = Column(Float, nullable=False, default=0.5)  # komisi capster mitra per layanan

    __table_args__ = (
        CheckConstraint("category IN ('main', 'coloring')", name='ck_services_category'),
    )

    def __repr__(self):
        return f"<Service service_id={self.service_id} name={self.name}>"


class Branch(Base):
    __tablename__ = 'branches'

    branch_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=True, default='')
    short = Column(String(50), nullable=True, default='')
    employees = Column(Integer, nullable=False, default=2)
    commission_rate = Column(Float, nullable=False, default=0.0)
    cost_tempat = Column(Integer, nullable=False, default=0)
    cost_listrik_air = Column(Integer, nullable=False, default=0)
    cost_wifi = Column(Integer, nullable=False, default=0)
    cost_karyawan = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<Branch branch_id={self.branch_id} name={self.name}>"


class Product(Base):
    __tablename__ = 'products'

    product_id      = Column(String(50), primary_key=True)
    name            = Column(String(100), nullable=False)
    price           = Column(Integer, nullable=False, default=0)
    commission_rate = Column(Float, nullable=False, default=0.0)  # % komisi capster per penjualan

    def __repr__(self):
        return f"<Product product_id={self.product_id} name={self.name}>"


class ProductStock(Base):
    __tablename__ = 'product_stocks'

    product_id = Column(String(50), primary_key=True)
    branch_id  = Column(String(50), primary_key=True)
    quantity   = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<ProductStock product={self.product_id} branch={self.branch_id} qty={self.quantity}>"


class ProductSale(Base):
    __tablename__ = 'product_sales'

    id               = Column(Integer, primary_key=True, autoincrement=True)
    date             = Column(DateTime, nullable=False)
    capster_name     = Column(String(100), nullable=False)
    product_id       = Column(String(50), nullable=False)
    product_name     = Column(String(100), nullable=False)
    price_each       = Column(Integer, nullable=False, default=0)
    quantity         = Column(Integer, nullable=False, default=1)
    commission_rate  = Column(Float, nullable=False, default=0.0)
    commission_earned= Column(Integer, nullable=False, default=0)
    branch_id        = Column(String(50), nullable=True, default='')

    __table_args__ = (
        Index('ix_product_sales_capster_date', 'capster_name', 'date'),
    )

    def __repr__(self):
        return f"<ProductSale id={self.id} capster={self.capster_name} product={self.product_name}>"


class Promo(Base):
    __tablename__ = 'promos'

    id           = Column(Integer, primary_key=True, autoincrement=True)
    name         = Column(String(100), nullable=False)
    discount_pct = Column(Float, nullable=False, default=0.0)   # e.g. 20.0 = 20% off
    start_date   = Column(Date, nullable=False)
    end_date     = Column(Date, nullable=False)
    is_active    = Column(Boolean, nullable=False, default=True)
    service_ids  = Column(Text, nullable=False, default='')     # comma-separated ServiceID
    branch_ids   = Column(Text, nullable=False, default='ALL')  # comma-separated branch_id or 'ALL'

    def __repr__(self):
        return f"<Promo id={self.id} name={self.name} discount={self.discount_pct}%>"


class Setting(Base):
    """Generic key-value store for app settings (e.g. WA gateway config)."""
    __tablename__ = 'settings'

    key   = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True, default='')

    def __repr__(self):
        return f"<Setting key={self.key}>"


class SalaryWithdrawal(Base):
    __tablename__ = 'salary_withdrawals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    capster_name = Column(String(100), nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    amount = Column(Integer, nullable=False, default=0)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    note = Column(Text, nullable=True, default='')

    __table_args__ = (
        Index('ix_salary_telegram_period', 'telegram_id', 'period_start', 'period_end'),
    )

    def __repr__(self):
        return f"<SalaryWithdrawal id={self.id} capster={self.capster_name} amount={self.amount}>"
