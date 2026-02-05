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
        capster="John",
        service="Potong Rambut",
        price=35000
    )
    
    assert trans.capster == "John"
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
        capster="Jane",
        service="Styling",
        price=50000,
        date=datetime.now()
    )
    
    data = trans.to_dict()
    assert 'capster' in data
    assert 'service' in data
    assert 'price' in data
    assert data['capster'] == "Jane"