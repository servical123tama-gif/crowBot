"""
Simple Test - Owner Check
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 SIMPLE TEST - OWNER CHECK")
print("=" * 60)

# Import
from app.config.settings import settings
from app.services.auth_service import AuthService

print(f"\n📋 Configuration:")
print(f"   AUTHORIZED_CAPSTERS: {settings.AUTHORIZED_CAPSTERS}")
print(f"   OWNER_IDS: {settings.OWNER_IDS}")

# Initialize
AuthService.initialize(
    authorized_users=settings.AUTHORIZED_CAPSTERS,
    owner_ids=settings.OWNER_IDS
)

print(f"\n✅ AuthService initialized")

# Test owner
test_id = 5964385547  # Your user ID
print(f"\n🧪 Testing user {test_id}:")
print(f"   Is authorized: {AuthService.is_authorized(test_id)}")
print(f"   Is owner: {AuthService.is_owner(test_id)}")
print(f"   Role: {AuthService.get_user_role(test_id)}")

print("\n" + "=" * 60)
print("✅ TEST COMPLETED")
print("=" * 60)