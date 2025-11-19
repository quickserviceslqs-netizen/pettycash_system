# Test Environment Best Practices

## ✅ Current Best Approach

**Use Render as your test environment** - it's already perfect for:
- UAT (User Acceptance Testing)
- Stakeholder demos
- End-to-end testing
- Integration testing

**URL:** https://pettycash-system.onrender.com

---

## 🎯 Test Data Management

### Loading Test Data

**On Render (after deployment):**
```bash
# If shell were available (it's not on free tier)
python manage.py load_test_data
```

**Workaround - Add to build.sh:**

Update `build.sh` to load test data automatically:
```bash
# After migrations
python manage.py load_test_data
```

This creates test users, departments, workflows automatically on each deployment.

---

### Test Users Created

| Username | Password | Role | Purpose |
|----------|----------|------|---------|
| admin | Admin@123456 | Superuser | Admin access |
| treasury_user | Test@123456 | Treasury | Approve payments |
| finance_user | Test@123456 | Finance | Financial approval |
| branch_user | Test@123456 | Branch Manager | Department approval |
| staff_user | Test@123456 | Staff | Create requisitions |

**⚠️ Change these passwords after testing!**

---

## 🔄 Test Workflow

### 1. Development (Local)
```
1. Write code on your computer
2. Test locally: http://localhost:8000
3. Commit and push to GitHub
```

### 2. Testing (Render)
```
4. Auto-deploys to: https://pettycash-system.onrender.com
5. Test with stakeholders
6. Verify all workflows
7. Get feedback
```

### 3. Production (Future)
```
8. When stable, deploy to production VPS
9. Point your domain to production
10. Keep Render as permanent test environment
```

---

## 📊 Data Isolation Strategy

### For Testing on Render:

**Option A: Manual Reset (Current)**
- Use test data
- When messy, reset database manually
- Simple but requires manual work

**Option B: Test Data Command (Recommended)**
- Load fresh test data anytime
- Run: `python manage.py load_test_data`
- Creates consistent test environment

**Option C: Database Snapshots**
- Render doesn't support free tier snapshots
- Upgrade to $7/month for database backups

---

## 🚀 Recommended Setup

### Immediate Actions:

1. **Use current Render deployment for testing** ✅
2. **Add test data loading** (I created the command)
3. **Share URL with stakeholders**
4. **Test all workflows**

### Update build.sh:

Add test data loading to your build script so it loads on every deployment:

```bash
#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python create_superuser.py
python manage.py load_test_data  # ← Add this
```

---

## 🎯 When You Get Your Domain

### Recommended Architecture:

```
┌─────────────────────────────────────────┐
│ Development (Local)                     │
│ - Your computer                         │
│ - SQLite                                │
│ - Instant testing                       │
└─────────────┬───────────────────────────┘
              │ git push
              ▼
┌─────────────────────────────────────────┐
│ Testing/UAT (Render - Free)             │
│ - pettycash-system-test.onrender.com   │
│ - PostgreSQL                            │
│ - Stakeholder testing                   │
│ - Always available for demos            │
└─────────────┬───────────────────────────┘
              │ approved changes
              ▼
┌─────────────────────────────────────────┐
│ Production (Your VPS + Domain)          │
│ - pettycash.yourdomain.com              │
│ - PostgreSQL                            │
│ - Real users, real money                │
│ - Backups enabled                       │
└─────────────────────────────────────────┘
```

---

## 💰 Cost Comparison

### Current (Single Environment):
- **Now:** $0/month
- **After 90 days:** $7/month (database)
- **Use for:** Testing + temporary production

### Future (Separate Test + Production):
- **Render Test:** $7/month (database)
- **Production VPS:** $5-20/month (DigitalOcean, Linode, etc.)
- **Total:** $12-27/month
- **Use for:** Proper test/prod separation

---

## ✅ Action Plan

### This Week:
1. ✅ Use Render as test environment (already done)
2. ⬜ Load test data (run the command I created)
3. ⬜ Test complete requisition workflow
4. ⬜ Share with 2-3 stakeholders for feedback

### Next Month:
1. Gather requirements from stakeholder testing
2. Fix any bugs found
3. Add requested features
4. Prepare for production launch

### When You Get Domain:
1. Decide: Keep Render or move to VPS?
2. If VPS: Set up production environment
3. Point domain to production
4. Keep Render for permanent test environment

---

## 🎯 Bottom Line

**Best approach for you RIGHT NOW:**

✅ **Keep using Render as your test environment**
✅ **Load test data for consistent testing**
✅ **Share with stakeholders**
✅ **Don't overcomplicate - one environment is fine for now**

When you get your domain and go live, THEN set up separate test/production environments.

**Your app is already production-ready and perfect for testing!** 🚀
