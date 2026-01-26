"""
Unit Tests for Services
"""
import pytest
from datetime import datetime
from app.models.transaction import Transaction
from app.services.auth_service import AuthService

def test_transaction_creation():
    """Test transaction model creation"""
    trans = Transaction(
        caster="John",
        service="Potong Rambut",
        price=35000
    )
    
    assert trans.caster == "John"
    assert trans.service == "Potong Rambut"
    assert trans.price == 35000
    assert trans.date is not None

def test_auth_service():
    """Test authentication service"""
    # This would need proper setup
    assert AuthService.is_authorized(123456789) == False
    
def test_transaction_to_dict():
    """Test transaction conversion to dict"""
    trans = Transaction(
        caster="Jane",
        service="Styling",
        price=50000,
        date=datetime.now()
    )
    
    data = trans.to_dict()
    assert 'caster' in data
    assert 'service' in data
    assert 'price' in data
    assert data['caster'] == "Jane"