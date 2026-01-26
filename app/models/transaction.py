"""
Transaction Model
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Transaction:
    """Transaction data model"""
    caster: str
    service: str
    price: float
    payment_method : Optional[str] = "Cash"
    date: Optional[datetime] = None,
    branch: Optional[str] = None
    
    def __post_init__(self):
        if self.date is None:
            self.date = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'caster': self.caster,
            'service': self.service,
            'price': self.price,
            'date': self.date,
            'payment' : self.payment_method,
            'branch': self.branch
        }
    
    def __str__(self):
        return f"Transaction({self.caster}, {self.service}, {self.price}, {self.branch}, {self.payment_method}, {self.date})"