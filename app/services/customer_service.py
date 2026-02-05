"""
Customer Service
"""
import logging
from typing import List
from app.models.customer import Customer
from app.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)

class CustomerService:
    """Customer-related business logic"""

    def __init__(self):
        self.sheets = SheetsService()

    def add_customer(self, name: str, phone: str) -> bool:
        """Add a new customer."""
        try:
            customer = Customer(name=name, phone=phone)
            return self.sheets.add_customer(customer)
        except Exception as e:
            logger.error(f"Failed to create and add customer: {e}", exc_info=True)
            return False

    def get_all_customers(self) -> List[Customer]:
        """Get all customers."""
        try:
            records = self.sheets.get_all_customers()
            customers = [Customer(name=rec['Name'], phone=rec['Phone']) for rec in records]
            return customers
        except Exception as e:
            logger.error(f"Failed to get all customers: {e}", exc_info=True)
            return []
