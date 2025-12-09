"""
Test API permission enforcement by simulating requests
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pettycash_system.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
from treasury.views import TreasuryFundViewSet, PaymentViewSet

User = get_user_model()
factory = RequestFactory()

print("=" * 80)
print("TESTING API PERMISSION ENFORCEMENT")
print("=" * 80)

# Test 1: test_basic (no app, no permissions) - should be DENIED
print("\n1. Testing test_basic (No App Assignment, No Permissions)")
print("-" * 80)
test_basic = User.objects.get(username="test_basic")
request = factory.get("/api/treasury/funds/")
force_authenticate(request, user=test_basic)

viewset = TreasuryFundViewSet.as_view({"get": "list"})
try:
    response = viewset(request)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 403:
        print(f"   ✅ BLOCKED - Permission Denied (Expected)")
        print(f"   Response: {response.data}")
    else:
        print(f"   ❌ ALLOWED - This is a SECURITY ISSUE!")
except Exception as e:
    print(f"   ✅ BLOCKED - Exception raised: {type(e).__name__}")

# Test 2: test_treasury (has app, has view_payment only) - should SEE funds but not execute
print("\n2. Testing test_treasury (Has App, View Permission Only)")
print("-" * 80)
test_treasury = User.objects.get(username="test_treasury")

# Test viewing treasury funds
request = factory.get("/api/treasury/funds/")
force_authenticate(request, user=test_treasury)
viewset = TreasuryFundViewSet.as_view({"get": "list"})
try:
    response = viewset(request)
    print(f"   List Funds - Status: {response.status_code}")
    if response.status_code == 403:
        print(f"      ❌ BLOCKED - Should be able to view (has treasury app)")
        print(f"      Response: {response.data}")
    elif response.status_code == 200:
        print(
            f"      ⚠️  ALLOWED but might fail - User has app but lacks view_treasuryfund permission"
        )
    else:
        print(f"      Status: {response.status_code}")
except Exception as e:
    print(f"      Exception: {type(e).__name__}: {e}")

# Test 3: test_treasury_full (has app, has all permissions) - should have FULL ACCESS
print("\n3. Testing test_treasury_full (Has App, All Permissions)")
print("-" * 80)
test_full = User.objects.get(username="test_treasury_full")
request = factory.get("/api/treasury/funds/")
force_authenticate(request, user=test_full)
viewset = TreasuryFundViewSet.as_view({"get": "list"})
try:
    response = viewset(request)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ ALLOWED - Full access (Expected)")
    else:
        print(f"   ❌ BLOCKED - This is an ERROR! User has all permissions")
        print(
            f"   Response: {response.data if hasattr(response, 'data') else response}"
        )
except Exception as e:
    print(f"   ❌ Exception: {type(e).__name__}: {e}")

# Test 4: Superuser - should BYPASS everything
print("\n4. Testing superadmin (Superuser)")
print("-" * 80)
superuser = User.objects.get(username="superadmin")
request = factory.get("/api/treasury/funds/")
force_authenticate(request, user=superuser)
viewset = TreasuryFundViewSet.as_view({"get": "list"})
try:
    response = viewset(request)
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ ALLOWED - Superuser bypass working (Expected)")
    else:
        print(f"   ❌ ISSUE - Superuser should have full access")
except Exception as e:
    print(f"   ❌ Exception: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(
    """
Expected Results:
  1. test_basic       → BLOCKED (no app assignment)
  2. test_treasury    → BLOCKED or LIMITED (has app but missing view_treasuryfund perm)
  3. test_treasury_full → ALLOWED (has app + all permissions)
  4. superadmin       → ALLOWED (superuser bypass)

If test_basic is ALLOWED, there's a permission bypass vulnerability.
If test_treasury_full is BLOCKED, permission checks are too strict.
"""
)
