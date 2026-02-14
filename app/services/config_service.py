"""
Config Service — Manages services and branch config via Google Sheets.
Loads config at startup and updates constants dicts in-place.
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_float(value, default=0.0):
    """Parse float from string, handling comma decimal separator (e.g. '0,5' → 0.5)."""
    if not value and value != 0:
        return default
    try:
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return default


def _parse_int(value, default=0):
    """Parse int from string, handling comma/dot separators."""
    if not value and value != 0:
        return default
    try:
        return int(float(str(value).replace(',', '.')))
    except (ValueError, TypeError):
        return default


class ConfigService:
    """Business logic for config CRUD (services + branches)."""

    def __init__(self, sheets_service):
        self.sheets = sheets_service

    # ------------------------------------------------------------------
    # Load all config from sheets → update constants dicts in-place
    # ------------------------------------------------------------------

    def load_all_config(self):
        """Load all config from sheets, update constants in-place."""
        self._load_services()
        self._load_branches()
        self._load_products()

    def _load_services(self):
        """Load services from sheet → update SERVICES_MAIN, SERVICES_COLORING, ALL_SERVICES."""
        records = self.sheets.get_all_services()
        if not records:
            logger.info("No services in sheet, keeping hardcoded defaults.")
            return

        main = {}
        coloring = {}
        for rec in records:
            sid = rec.get('ServiceID', '')
            if not sid:
                continue
            entry = {'name': rec.get('Name', sid), 'price': _parse_int(rec.get('Price', 0))}
            category = rec.get('Category', 'main').lower()
            if category == 'coloring':
                coloring[sid] = entry
            else:
                main[sid] = entry

        from app.config.constants import SERVICES_MAIN, SERVICES_COLORING, ALL_SERVICES
        SERVICES_MAIN.clear()
        SERVICES_MAIN.update(main)
        SERVICES_COLORING.clear()
        SERVICES_COLORING.update(coloring)
        ALL_SERVICES.clear()
        ALL_SERVICES.update({**main, **coloring})
        logger.info(f"Loaded {len(main)} main + {len(coloring)} coloring services from sheet.")

    def _load_branches(self):
        """Load branches from sheet → update BRANCHES in-place."""
        records = self.sheets.get_all_branches_config()
        if not records:
            logger.info("No branches in sheet, keeping hardcoded defaults.")
            return

        branches = {}
        for rec in records:
            bid = rec.get('BranchID', '')
            if not bid:
                continue
            branches[bid] = {
                'name': rec.get('Name', bid),
                'location': rec.get('Location', ''),
                'short': rec.get('Short', ''),
                'employees': _parse_int(rec.get('Employees', 2), 2),
                'commission_rate': _parse_float(rec.get('CommissionRate', 0)),
                'operational_cost': {
                    'tempat': _parse_int(rec.get('Cost_tempat', 0)),
                    'listrik air': _parse_int(rec.get('Cost_listrik_air', 0)),
                    'wifi': _parse_int(rec.get('Cost_wifi', 0)),
                    'karyawan_fixed': _parse_int(rec.get('Cost_karyawan', 0)),
                }
            }

        from app.config.constants import BRANCHES
        BRANCHES.clear()
        BRANCHES.update(branches)
        logger.info(f"Loaded {len(branches)} branches from sheet.")

    def _load_products(self):
        """Load products from sheet → update PRODUCTS in-place."""
        records = self.sheets.get_all_products()
        if not records:
            logger.info("No products in sheet, keeping hardcoded defaults.")
            return

        products = {}
        for rec in records:
            pid = rec.get('ProductID', '')
            if not pid:
                continue
            products[pid] = {
                'name': rec.get('Name', pid),
                'price': _parse_int(rec.get('Price', 0)),
            }

        from app.config.constants import PRODUCTS
        PRODUCTS.clear()
        PRODUCTS.update(products)
        logger.info(f"Loaded {len(products)} products from sheet.")

    # ------------------------------------------------------------------
    # Service CRUD
    # ------------------------------------------------------------------

    def _make_service_id(self, name: str) -> str:
        """Generate a ServiceID from name (PascalCase, no spaces)."""
        words = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
        return ''.join(w.capitalize() for w in words)

    def add_service(self, name: str, category: str, price: int) -> bool:
        """Add a new service → sheet + reload in-memory."""
        service_id = self._make_service_id(name)
        success = self.sheets.add_service(service_id, name, category, price)
        if success:
            self._load_services()
        return success

    def update_service_price(self, service_id: str, new_price: int) -> bool:
        """Update a service's price → sheet + reload in-memory."""
        success = self.sheets.update_service(service_id, Price=new_price)
        if success:
            self._load_services()
        return success

    def remove_service(self, service_id: str) -> bool:
        """Remove a service → sheet + reload in-memory."""
        success = self.sheets.remove_service(service_id)
        if success:
            self._load_services()
        return success

    def get_all_services(self) -> List[Dict]:
        """Get all services as list of dicts from sheet."""
        return self.sheets.get_all_services()

    # ------------------------------------------------------------------
    # Branch CRUD
    # ------------------------------------------------------------------

    def update_branch_cost(self, branch_id: str, cost_key: str, new_value: int) -> bool:
        """Update a branch operational cost item → sheet + reload in-memory."""
        # Map cost_key to sheet column name
        cost_column_map = {
            'tempat': 'Cost_tempat',
            'listrik air': 'Cost_listrik_air',
            'wifi': 'Cost_wifi',
            'karyawan_fixed': 'Cost_karyawan',
        }
        column = cost_column_map.get(cost_key)
        if not column:
            logger.warning(f"Unknown cost key: {cost_key}")
            return False
        success = self.sheets.update_branch_config(branch_id, **{column: new_value})
        if success:
            self._load_branches()
        return success

    def update_branch_commission(self, branch_id: str, rate: float) -> bool:
        """Update a branch commission rate → sheet + reload in-memory."""
        success = self.sheets.update_branch_config(branch_id, CommissionRate=rate)
        if success:
            self._load_branches()
        return success

    def get_branch_details(self, branch_id: str) -> Optional[Dict]:
        """Get a single branch's details from in-memory constants."""
        from app.config.constants import BRANCHES
        return BRANCHES.get(branch_id)

    # ------------------------------------------------------------------
    # Product CRUD
    # ------------------------------------------------------------------

    def _make_product_id(self, name: str) -> str:
        """Generate a ProductID from name (PascalCase, no spaces)."""
        words = re.sub(r'[^a-zA-Z0-9\s]', '', name).split()
        return ''.join(w.capitalize() for w in words)

    def add_product(self, name: str, price: int) -> bool:
        """Add a new product → sheet + reload in-memory."""
        product_id = self._make_product_id(name)
        success = self.sheets.add_product(product_id, name, price)
        if success:
            self._load_products()
        return success

    def update_product_price(self, product_id: str, new_price: int) -> bool:
        """Update a product's price → sheet + reload in-memory."""
        success = self.sheets.update_product(product_id, Price=new_price)
        if success:
            self._load_products()
        return success

    def remove_product(self, product_id: str) -> bool:
        """Remove a product → sheet + reload in-memory."""
        success = self.sheets.remove_product(product_id)
        if success:
            self._load_products()
        return success
