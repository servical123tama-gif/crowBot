"""
SQLAlchemy ORM Models — 7 tables
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Date, DateTime,
    Text, Index, CheckConstraint, UniqueConstraint
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

    def __repr__(self):
        return f"<Customer id={self.id} name={self.name}>"


class Service(Base):
    __tablename__ = 'services'

    service_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False, default='main')
    price = Column(Integer, nullable=False, default=0)

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

    product_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<Product product_id={self.product_id} name={self.name}>"


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
