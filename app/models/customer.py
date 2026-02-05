"""
Customer Model
"""
from dataclasses import dataclass

@dataclass
class Customer:
    """Customer data"""
    name: str
    phone: str
