"""
Branch Management Service
"""
import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class BranchService:
    """Manage user branch selection (in-memory, daily reset)"""
    
    # Format: {user_id: {'branch_id': 'cabang_a', 'date': '2026-01-19'}}
    _user_branches: Dict[int, Dict[str, str]] = {}
    
    @classmethod
    def set_branch(cls, user_id: int, branch_id: str) -> bool:
        """Set branch for user (for today)"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        cls._user_branches[user_id] = {
            'branch_id': branch_id,
            'date': today
        }
        
        logger.info(f"User {user_id} set to branch {branch_id} for {today}")
        return True
    
    @classmethod
    def get_branch(cls, user_id: int) -> Optional[str]:
        """Get user's branch for today (returns branch_id or None)"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if user_id not in cls._user_branches:
            logger.debug(f"User {user_id} has no branch set")
            return None
        
        user_data = cls._user_branches[user_id]
        stored_date = user_data.get('date')
        
        # Check if stored date is today
        if stored_date != today:
            logger.info(f"User {user_id} branch expired (stored: {stored_date}, today: {today})")
            # Clear old data
            del cls._user_branches[user_id]
            return None
        
        branch_id = user_data.get('branch_id')
        logger.debug(f"User {user_id} branch: {branch_id}")
        return branch_id
    
    @classmethod
    def has_branch_today(cls, user_id: int) -> bool:
        """Check if user has set branch for today"""
        return cls.get_branch(user_id) is not None
    
    @classmethod
    def clear_branch(cls, user_id: int) -> bool:
        """Clear user's branch (force re-select)"""
        if user_id in cls._user_branches:
            del cls._user_branches[user_id]
            logger.info(f"Cleared branch for user {user_id}")
            return True
        return False
    
    @classmethod
    def get_all_branches_today(cls) -> Dict[int, str]:
        """Get all users with branches set for today (for debugging)"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        result = {}
        for user_id, data in cls._user_branches.items():
            if data.get('date') == today:
                result[user_id] = data.get('branch_id')
        
        return result