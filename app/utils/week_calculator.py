"""
Week Calculator - Calculate week ranges based on Monday-Sunday
"""
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
from calendar import monthrange

logger = logging.getLogger(__name__)

class WeekCalculator:
    """Calculate weekly ranges for reporting"""
    
    @staticmethod
    def get_first_monday_of_month(year: int, month: int) -> datetime:
        """
        Get first Monday of the month
        If month doesn't start with Monday, find the first Monday
        """
        # First day of month
        first_day = datetime(year, month, 1)
        
        # Find first Monday
        # weekday: 0=Monday, 6=Sunday
        days_until_monday = (7 - first_day.weekday()) % 7
        if days_until_monday == 0 and first_day.weekday() == 0:
            # Already Monday
            first_monday = first_day
        else:
            # Find next Monday
            first_monday = first_day + timedelta(days=days_until_monday)
            if first_monday.month != month:
                # Next Monday is in next month, so we start from first day
                first_monday = first_day
        
        return first_monday
    
    @staticmethod
    def get_weeks_in_month(year: int, month: int) -> List[Dict]:
        """
        Get all weeks in a month (Monday to Sunday)
        
        Returns:
            List of dicts with 'week_num', 'start_date', 'end_date'
        """
        weeks = []
        
        # Start from first Monday
        current_monday = WeekCalculator.get_first_monday_of_month(year, month)
        
        # Last day of month
        last_day = monthrange(year, month)[1]
        month_end = datetime(year, month, last_day, 23, 59, 59)
        
        week_num = 1
        
        while True:
            # Sunday is 6 days after Monday
            current_sunday = current_monday + timedelta(days=6)
            current_sunday = current_sunday.replace(hour=23, minute=59, second=59)
            
            # Check if we're still in the month or just starting next month
            if current_monday.month == month or (current_monday.month == month and week_num == 1):
                weeks.append({
                    'week_num': week_num,
                    'start_date': current_monday,
                    'end_date': current_sunday,
                    'start_str': current_monday.strftime('%d %b'),
                    'end_str': current_sunday.strftime('%d %b')
                })
                
                week_num += 1
                
                # Move to next Monday
                current_monday = current_sunday + timedelta(days=1)
                current_monday = current_monday.replace(hour=0, minute=0, second=0)
                
                # Stop if next Monday is too far into next month
                if current_monday.month != month and current_monday.day > 7:
                    break
            else:
                break
        
        return weeks
    
    @staticmethod
    def get_current_week_info(year: int = None, month: int = None) -> Dict:
        """
        Get current week info based on today's date
        
        Returns:
            Dict with 'week_num', 'start_date', 'end_date', 'month', 'year'
        """
        if year is None or month is None:
            today = datetime.now()
            year = today.year
            month = today.month
        else:
            today = datetime.now()
        
        weeks = WeekCalculator.get_weeks_in_month(year, month)
        
        # Find which week contains today
        for week in weeks:
            if week['start_date'].date() <= today.date() <= week['end_date'].date():
                return {
                    **week,
                    'month': month,
                    'year': year,
                    'month_name': datetime(year, month, 1).strftime('%B %Y')
                }
        
        # If today is before first week of month, return None
        # If today is after last week, return last week
        if weeks:
            return {
                **weeks[-1],
                'month': month,
                'year': year,
                'month_name': datetime(year, month, 1).strftime('%B %Y')
            }
        
        return None
    
    @staticmethod
    def get_week_range(year: int, month: int, week_num: int) -> Tuple[datetime, datetime]:
        """
        Get start and end date for specific week number
        
        Args:
            year: Year
            month: Month (1-12)
            week_num: Week number (1-4/5)
        
        Returns:
            (start_date, end_date) or (None, None) if invalid
        """
        weeks = WeekCalculator.get_weeks_in_month(year, month)
        
        for week in weeks:
            if week['week_num'] == week_num:
                return week['start_date'], week['end_date']
        
        return None, None