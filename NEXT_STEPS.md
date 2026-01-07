# Next Steps - Production Deployment & Testing

## 🎯 What's Been Completed

✅ **Permission System Fully Secured**
- All 4 apps (transactions, treasury, workflow, reports) use consistent 3-layer security
- 9 critical treasury actions have explicit permission checks
- 2 transactions admin functions require permissions
- Workflow and reports apps updated from deprecated role system
- 20 automated tests - all passing (100% success rate)
- 5 test users created for manual testing
- Comprehensive test report generated

✅ **Code Pushed to GitHub**
- Latest commit: `d8b7cb5` - "Add comprehensive permission testing suite with 20 automated tests"
- Previous commit: `f4f082f` - "Add explicit permission checks to critical treasury actions"
- All changes synchronized

---

## 📋 Next Steps for Production

### 1. Deploy to Render
Your code is already pushed to GitHub. Render should automatically deploy if you have auto-deploy enabled.

**Manual Deploy Steps (if needed):**
1. Go to Render dashboard
2. Select your pettycash_system service
3. Click "Manual Deploy" > "Deploy latest commit"
4. Wait for build to complete

### 2. Create Superuser on Render

Recommended: Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` (and optional `ADMIN_USERNAME`) as environment variables in Render (dashboard → Environment) and redeploy — `scripts/bootstrap_db.py` will create or update the superuser automatically.

If you need to do it manually in a pinch (not recommended):

**Option A: Using Render Shell**
```bash
# Open Render Shell from dashboard
cd /opt/render/project/src
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> # Deprecated: don't use hardcoded credentials. Instead set ADMIN_EMAIL and ADMIN_PASSWORD as environment variables and rely on scripts/bootstrap_db.py to create/update the superuser during deploy.
```

**Note:** If you use manual creation, avoid leaving hardcoded credentials in scripts or docs; prefer environment variables and the bootstrap script.

### 3. Create Apps in Production Database

Run this in Render shell:
```python
python manage.py shell
>>> from accounts.models import App
>>> apps = ['transactions', 'treasury', 'workflow', 'reports']
>>> for app_name in apps:
...     App.objects.get_or_create(
...         name=app_name,
...         defaults={
...             'display_name': app_name.capitalize(),
...             'description': f'{app_name.capitalize()} management',
...             'is_active': True
...         }
...     )
```

Or create a script:
```bash
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
django.setup()
from accounts.models import App
apps = ['transactions', 'treasury', 'workflow', 'reports']
for app_name in apps:
    App.objects.get_or_create(
        name=app_name,
        defaults={
            'display_name': app_name.capitalize(),
            'description': f'{app_name.capitalize()} management',
            'is_active': True
        }
    )
print('Apps created successfully!')
"
```

### 4. Create Treasury Funds (if needed)

```bash
# Copy create_treasury_funds.py to Render and run
python create_treasury_funds.py
```

### 5. Create Test Users in Production

```bash
# This will create the 5 test users for manual testing
python create_test_users.py
```

---

## 🧪 Manual Testing Checklist

Use the test users to verify permission enforcement:

### Test 1: Basic User (No Access) ❌
- [ ] Login as `test_basic` / `Test@123`
- [ ] Try to access `/treasury/`
- [ ] **Expected:** Redirect with "You don't have access to Treasury app"
- [ ] Try `/transactions/`, `/workflow/`, `/reports/`
- [ ] **Expected:** All blocked with access denied messages

### Test 2: Treasury View-Only 👁️
- [ ] Login as `test_treasury` / `Test@123`
- [ ] Access treasury app - should work
- [ ] View payments list - should work
- [ ] Try to execute payment - **Expected: 403 Forbidden**
- [ ] Try to send OTP - **Expected: 403 Forbidden**

### Test 3: Treasury Full Access ✅
- [ ] Login as `test_treasury_full` / `Test@123`
- [ ] Access treasury app - should work
- [ ] Execute payment - should work
- [ ] Send OTP - should work
- [ ] Reconcile fund - should work

### Test 4: Transactions Limited 📝
- [ ] Login as `test_transactions` / `Test@123`
- [ ] Create new requisition - should work
- [ ] Try to approve requisition - **Expected: Permission error**
- [ ] Try admin override - **Expected: Permission error**

### Test 5: Superuser Full Power 👑
- [ ] Login as `superadmin` / `Super@123456`
- [ ] Access all 4 apps - should work
- [ ] Execute treasury payment - should work
- [ ] Approve requisition - should work
- [ ] All features should be accessible

---

## 🔧 Local Testing (Already Available)

You can test locally right now with the created test users:

```bash
# Start development server
python manage.py runserver

# Test users are already created in your local database:
# - test_basic / Test@123
# - test_treasury / Test@123
# - test_treasury_full / Test@123
# - test_transactions / Test@123
# - test_workflow / Test@123
# - superadmin / Super@123456
```

---

## 📊 Running Automated Tests

```bash
# Run the comprehensive permission test suite
python test_permissions.py

# Expected output: 20/20 tests passing (100% success rate)
```

---

## 🐛 Troubleshooting

### Issue: Apps don't exist in production
**Solution:** Run the create apps script (see step 3 above)

### Issue: Test users can't login
**Solution:** 
1. Verify users exist: `python manage.py shell` → `User.objects.filter(username__startswith='test_').count()`
2. Recreate: `python create_test_users.py`

### Issue: Treasury funds not found
**Solution:** Run `python create_treasury_funds.py`

### Issue: Permission still bypassed
**Solution:** 
1. Check code version: `git log --oneline -3`
2. Should see: `d8b7cb5 Add comprehensive permission testing suite`
3. If not, pull latest: `git pull origin main`

---

## 📝 Permission Assignment Guide

### Via Django Admin UI

1. **Navigate to:** `https://your-domain.com/admin/`
2. **Login as superuser**
3. **Assign Apps:**
   - Users → Select user → Assigned apps → Add apps
4. **Assign Permissions:**
   - Users → Select user → User permissions → Add permissions
   - Common permissions:
     - `treasury.view_payment` - View payments
     - `treasury.change_payment` - Execute payments, send OTP
     - `treasury.add_treasuryfund` - Create funds
     - `transactions.view_requisition` - View requisitions
     - `transactions.add_requisition` - Create requisitions
     - `transactions.change_requisition` - Approve requisitions

### Via Python Script

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from accounts.models import App

User = get_user_model()
user = User.objects.get(username='someuser')

# Assign app
treasury_app = App.objects.get(name='treasury')
user.assigned_apps.add(treasury_app)

# Assign permission
perm = Permission.objects.get(codename='change_payment', content_type__app_label='treasury')
user.user_permissions.add(perm)

print(f"Assigned treasury app and change_payment permission to {user.username}")
```

---

## 📈 Success Metrics

After deployment and testing, you should verify:

- [ ] 0 permission bypass vulnerabilities
- [ ] All test users have correct access levels
- [ ] Superuser can access everything
- [ ] Non-privileged users blocked appropriately
- [ ] Error messages are clear and user-friendly
- [ ] No 500 errors on permission denials (should be 403)

---

## 🎉 You're Ready!

Your permission system is fully tested and secured. All that remains is:
1. Deploy to production
2. Create superuser and apps
3. Run manual tests with test users
4. Assign real users to apps and permissions

**The system is production-ready!** 🚀
