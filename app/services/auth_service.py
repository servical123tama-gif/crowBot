"""
Authentication Service
"""
import logging
from typing import List
from app.config.constants import ROLE_OWNER, ROLE_ADMIN, ROLE_CAPSTER

logger = logging.getLogger(__name__)

class AuthService:
    """Handle authentication and authorization"""
    
    # Static lists
    _authorized_users = []
    _owner_ids = []
    _admin_ids = []
    
    @classmethod
    def initialize(cls, authorized_users: List[int], owner_ids: List[int] = None, admin_ids: List[int] = None):
        """Initialize with authorized users and roles"""
        cls._authorized_users = authorized_users.copy()
        cls._owner_ids = owner_ids.copy() if owner_ids else []
        cls._admin_ids = admin_ids.copy() if admin_ids else []
        
        logger.info(f"AuthService initialized:")
        logger.info(f"  - Authorized users: {len(cls._authorized_users)}")
        logger.info(f"  - Owners: {len(cls._owner_ids)}")
        logger.info(f"  - Admins: {len(cls._admin_ids)}")
    
    @classmethod
    def is_authorized(cls, user_id: int) -> bool:
        """Check if user is authorized to use bot"""
        authorized = user_id in cls._authorized_users
        
        if not authorized:
            logger.warning(f"Unauthorized access attempt: {user_id}")
        
        return authorized
    
    @classmethod
    def is_owner(cls, user_id: int) -> bool:
        """Check if user is owner"""
        return user_id in cls._owner_ids
    
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in cls._admin_ids
    
    @classmethod
    def is_owner_or_admin(cls, user_id: int) -> bool:
        """Check if user is owner or admin"""
        return cls.is_owner(user_id) or cls.is_admin(user_id)
    
    @classmethod
    def get_user_role(cls, user_id: int) -> str:
        """Get user role"""
        if cls.is_owner(user_id):
            return ROLE_OWNER
        elif cls.is_admin(user_id):
            return ROLE_ADMIN
        elif cls.is_authorized(user_id):
            return ROLE_CAPSTER
        else:
            return None
    
    @classmethod
    def get_authorized_users(cls) -> List[int]:
        """Get list of authorized users"""
        return cls._authorized_users.copy()
    
    @classmethod
    def add_authorized_user(cls, user_id: int) -> bool:
        """Add new authorized user (runtime only)"""
        if user_id not in cls._authorized_users:
            cls._authorized_users.append(user_id)
            logger.info(f"Added authorized user: {user_id}")
            return True
        return False
    
    @classmethod
    def remove_authorized_user(cls, user_id: int) -> bool:
        """Remove authorized user (runtime only)"""
        if user_id in cls._authorized_users:
            cls._authorized_users.remove(user_id)
            logger.info(f"Removed authorized user: {user_id}")
            return True
        return False