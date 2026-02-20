"""
Capster Service
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

from app.models.capster import Capster
from app.services.auth_service import AuthService
from app.config.constants import DATE_FORMAT

logger = logging.getLogger(__name__)


class CapsterService:
    """Capster-related business logic"""

    def __init__(self, sheets_service):
        self.sheets = sheets_service
        # In-memory cache: telegram_id -> real name
        self._name_cache: Dict[int, str] = {}

    def add_capster(self, name: str, telegram_id: int, alias: str = '',
                    employment_type: str = 'mitra', commission_rate: float = 0.5) -> bool:
        """Add a new capster to sheets and authorize at runtime."""
        try:
            capster = Capster(name=name, telegram_id=telegram_id, alias=alias,
                              employment_type=employment_type,
                              commission_rate=commission_rate)
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

    def update_capster(self, telegram_id: int, name: str = None, alias: str = None,
                       employment_type: str = None, commission_rate: float = None) -> bool:
        """Update capster name/alias/employment in sheets and refresh cache."""
        try:
            success = self.sheets.update_capster(
                telegram_id, name=name, alias=alias,
                employment_type=employment_type, commission_rate=commission_rate
            )
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
            capsters = []
            for rec in records:
                rate = rec.get('CommissionRate', '0.5')
                try:
                    commission = float(rate) if rate else 0.5
                except (ValueError, TypeError):
                    commission = 0.5
                capsters.append(Capster(
                    name=rec['Name'],
                    telegram_id=int(rec['TelegramID']),
                    alias=rec.get('Alias', ''),
                    employment_type=rec.get('EmploymentType', 'mitra') or 'mitra',
                    commission_rate=commission,
                ))
            return capsters
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

    # --- Salary / Withdrawal Methods ---

    def _get_capster_by_tid(self, telegram_id: int) -> Optional[Capster]:
        """Find capster by telegram_id."""
        for c in self.get_all_capsters():
            if c.telegram_id == telegram_id:
                return c
        return None

    def _get_week_range(self) -> tuple:
        """Get current week range (Monday-Sunday)."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday

    def get_capster_earnings(self, capster_name: str, aliases: List[str],
                             start_date: date, end_date: date,
                             commission_rate: float) -> dict:
        """Calculate capster earnings from transactions in a period."""
        try:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            df = self.sheets.get_transactions_by_range(start_dt, end_dt)

            if df.empty:
                return {'total_revenue': 0, 'commission': 0, 'transaction_count': 0}

            # Build set of all known names (case-insensitive)
            all_names = {capster_name.lower()}
            for alias in aliases:
                if alias:
                    all_names.add(alias.lower())

            # Filter by capster
            mask = df['Capster'].str.lower().str.strip().isin(all_names)
            capster_df = df[mask]

            total_revenue = int(capster_df['Price'].sum())
            commission = int(total_revenue * commission_rate)

            return {
                'total_revenue': total_revenue,
                'commission': commission,
                'transaction_count': len(capster_df),
            }
        except Exception as e:
            logger.error(f"Failed to get capster earnings: {e}", exc_info=True)
            return {'total_revenue': 0, 'commission': 0, 'transaction_count': 0}

    def get_salary_summary(self, telegram_id: int, period: str = 'week') -> Optional[dict]:
        """Get salary summary: period earnings + cumulative balance.

        Period earnings show this week/month's transactions for info.
        Balance is cumulative: ALL earnings ever - ALL withdrawals ever.
        """
        capster = self._get_capster_by_tid(telegram_id)
        if not capster:
            return None

        # --- Period range (for display) ---
        if period == 'month':
            today = date.today()
            period_start = today.replace(day=1)
            if today.month == 12:
                period_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                period_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        else:
            period_start, period_end = self._get_week_range()

        aliases = [capster.alias] if capster.alias else []

        # --- Period earnings (for display) ---
        period_earnings = self.get_capster_earnings(
            capster.name, aliases, period_start, period_end, capster.commission_rate
        )

        # --- Cumulative: all earnings from Jan 1 current year until today ---
        today = date.today()
        year_start = date(today.year, 1, 1)
        cumulative_earnings = self.get_capster_earnings(
            capster.name, aliases, year_start, today, capster.commission_rate
        )

        # --- Total withdrawn (all time, no date filter) ---
        all_withdrawals = self.sheets.get_withdrawals(telegram_id)
        total_withdrawn_all = 0
        for r in all_withdrawals:
            try:
                total_withdrawn_all += int(float(r.get('Amount', 0)))
            except (ValueError, TypeError):
                pass

        # Period withdrawn (just for this period's display)
        start_str = period_start.strftime(DATE_FORMAT)
        end_str = period_end.strftime(DATE_FORMAT)
        period_withdrawn = self.sheets.get_total_withdrawn(telegram_id, start_str, end_str)

        # Cumulative balance = all earned commissions - all withdrawals
        cumulative_balance = cumulative_earnings['commission'] - total_withdrawn_all

        # Get last withdrawal date
        last_withdrawal_date = None
        if all_withdrawals:
            try:
                last_date_str = all_withdrawals[-1].get('Date', '')
                if last_date_str:
                    last_withdrawal_date = datetime.strptime(
                        last_date_str[:10], DATE_FORMAT
                    ).date()
            except (ValueError, IndexError):
                pass

        return {
            'capster': capster,
            'period_start': period_start,
            'period_end': period_end,
            # Period info (for display)
            'total_revenue': period_earnings['total_revenue'],
            'commission_earned': period_earnings['commission'],
            'transaction_count': period_earnings['transaction_count'],
            'period_withdrawn': period_withdrawn,
            # Cumulative totals
            'cumulative_commission': cumulative_earnings['commission'],
            'total_withdrawn': total_withdrawn_all,
            'balance': cumulative_balance,
            'last_withdrawal_date': last_withdrawal_date,
        }

    def record_withdrawal(self, telegram_id: int, amount: int,
                          period_start: date, period_end: date, note: str = '') -> bool:
        """Record a salary withdrawal."""
        capster = self._get_capster_by_tid(telegram_id)
        if not capster:
            return False
        return self.sheets.add_withdrawal(
            capster_name=capster.name,
            telegram_id=telegram_id,
            amount=amount,
            period_start=period_start.strftime(DATE_FORMAT),
            period_end=period_end.strftime(DATE_FORMAT),
            note=note,
        )

    def get_withdrawal_history(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Get recent withdrawal history for a capster."""
        records = self.sheets.get_withdrawals(telegram_id)
        # Return most recent first
        return list(reversed(records[-limit:]))
