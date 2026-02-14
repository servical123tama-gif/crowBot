"""
Capster Service
"""
import logging
from typing import Dict, List, Optional

from app.models.capster import Capster
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class CapsterService:
    """Capster-related business logic"""

    def __init__(self, sheets_service):
        self.sheets = sheets_service
        # In-memory cache: telegram_id -> real name
        self._name_cache: Dict[int, str] = {}

    def add_capster(self, name: str, telegram_id: int, alias: str = '') -> bool:
        """Add a new capster to sheets and authorize at runtime."""
        try:
            capster = Capster(name=name, telegram_id=telegram_id, alias=alias)
            success = self.sheets.add_capster(capster)
            if success:
                AuthService.add_authorized_user(telegram_id)
                self._name_cache[telegram_id] = name
            return success
        except Exception as e:
            logger.error(f"Failed to add capster: {e}", exc_info=True)
            return False

    def remove_capster(self, telegram_id: int) -> bool:
        """Remove capster from sheets and revoke authorization at runtime."""
        try:
            success = self.sheets.remove_capster(telegram_id)
            if success:
                AuthService.remove_authorized_user(telegram_id)
                self._name_cache.pop(telegram_id, None)
            return success
        except Exception as e:
            logger.error(f"Failed to remove capster: {e}", exc_info=True)
            return False

    def update_capster(self, telegram_id: int, name: str = None, alias: str = None) -> bool:
        """Update capster name/alias in sheets and refresh cache."""
        try:
            success = self.sheets.update_capster(telegram_id, name=name, alias=alias)
            if success and name:
                self._name_cache[telegram_id] = name
            return success
        except Exception as e:
            logger.error(f"Failed to update capster: {e}", exc_info=True)
            return False

    def get_real_name(self, telegram_id: int, fallback: str = None) -> str:
        """Get capster real name by telegram_id. Returns fallback if not found."""
        if telegram_id in self._name_cache:
            return self._name_cache[telegram_id]
        return fallback or str(telegram_id)

    def get_all_capsters(self) -> List[Capster]:
        """Get all capsters from sheets."""
        try:
            records = self.sheets.get_all_capsters()
            return [
                Capster(
                    name=rec['Name'],
                    telegram_id=int(rec['TelegramID']),
                    alias=rec.get('Alias', '')
                )
                for rec in records
            ]
        except Exception as e:
            logger.error(f"Failed to get capsters: {e}", exc_info=True)
            return []

    def get_name_alias_map(self) -> Dict[str, List[str]]:
        """Build a map: name_lower -> [all known names for this capster].
        Used by report filtering so 'Zidan' also matches 'timingemma' in old transactions."""
        alias_map: Dict[str, List[str]] = {}
        capsters = self.get_all_capsters()
        for c in capsters:
            all_names = c.all_names()  # [real_name] or [real_name, alias]
            all_lower = [n.lower() for n in all_names]
            for name_lower in all_lower:
                alias_map[name_lower] = all_lower
        return alias_map

    def migrate_old_transaction_names(self) -> dict:
        """Batch update old transaction capster names from alias to real name."""
        capsters = self.get_all_capsters()
        alias_to_real = {}
        for c in capsters:
            if c.alias and c.alias.lower() != c.name.lower():
                alias_to_real[c.alias.lower()] = c.name
        if not alias_to_real:
            return {}
        return self.sheets.migrate_capster_names(alias_to_real)

    def load_capsters_to_auth(self):
        """Load all capsters from sheets into AuthService (merge with .env) and populate name cache."""
        try:
            capsters = self.get_all_capsters()
            count = 0
            for capster in capsters:
                self._name_cache[capster.telegram_id] = capster.name
                if AuthService.add_authorized_user(capster.telegram_id):
                    count += 1
            logger.info(f"Loaded {count} new capster(s) from sheets into AuthService (total in sheets: {len(capsters)})")
            logger.info(f"Name cache populated with {len(self._name_cache)} capster(s)")
        except Exception as e:
            logger.error(f"Failed to load capsters to auth: {e}", exc_info=True)
