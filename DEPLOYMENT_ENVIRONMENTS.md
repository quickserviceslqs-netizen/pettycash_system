# Deployment Environments Guide

## Current Setup

### Production Environment
- **URL:** https://pettycash-system.onrender.com
- **Database:** pettycash-db (PostgreSQL on Render)
- **Branch:** main
- **Purpose:** Live production system
- **Users:** Real users, real data

---

## Adding a Test Environment

### Option 1: Separate Test Service on Render (Free)

**Steps:**

1. **Create Test Database:**
   - Go to Render Dashboard
   - Click "New +" → "PostgreSQL"
   - Name: `pettycash-test-db`
   - Plan: Free
   - Copy Internal Database URL

2. **Create Test Web Service:**
   - Click "New +" → "Web Service"
   - Connect same GitHub repo: `pettycash_system`
   - Name: `pettycash-system-test`
   - Branch: `main` (or create a `test` branch)
   - Same build/start commands as production

3. **Set Environment Variables:**
   ```
   SECRET_KEY = [generate new one for test]
   DEBUG = True (for easier testing)
   ALLOWED_HOSTS = .onrender.com
   CSRF_TRUSTED_ORIGINS = https://*.onrender.com
   DATABASE_URL = [test database Internal URL]
   PYTHON_VERSION = 3.11.7
   ```

4. **Deploy:**
   - Service will be at: `https://pettycash-system-test.onrender.com`
   - Separate database = test data won't affect production
   - Both services run on free tier!

**Result:**
- **Test:** https://pettycash-system-test.onrender.com (free, sleeps)
- **Prod:** https://pettycash-system.onrender.com (free, sleeps)

---

### Option 2: Use Local + Render

**Simple approach:**

| Environment | Location | Database | URL |
|-------------|----------|----------|-----|
| **Development** | Your computer | SQLite | http://localhost:8000 |
| **Test/UAT** | Render | PostgreSQL | https://pettycash-system.onrender.com |
| **Production** | (Wait for domain) | (Future VPS) | https://pettycash.yourdomain.com |

**Current workflow:**
1. Develop locally → test on localhost
2. Push to GitHub → auto-deploys to Render
3. Test on Render → share with stakeholders
4. When you get domain → migrate to production VPS

---

### Option 3: Environment Variables for Different Modes

Add environment switching in your current Render deployment:

**In Render, add variable:**
```
ENVIRONMENT = test
```

**Then in settings.py:**
```python
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    # Production settings
    DEBUG = False
    # Use production database
elif ENVIRONMENT == 'test':
    # Test settings
    DEBUG = True
    # Use test database
```

---

## Recommended Approach for You

**Right now (no domain yet):**

```
┌─────────────────┐
│ Development     │  Your Computer
│ (Local)         │  SQLite, instant testing
└────────┬────────┘
         │ git push
         ▼
┌─────────────────┐
│ Testing/UAT     │  Render (current deployment)
│ (Cloud)         │  PostgreSQL, stakeholder demos
└─────────────────┘
```

**When you get domain:**

```
┌─────────────────┐
│ Development     │  Your Computer
└────────┬────────┘
         │ git push to test branch
         ▼
┌─────────────────┐
│ Testing         │  Render test service
│                 │  pettycash-system-test.onrender.com
└────────┬────────┘
         │ merge to main
         ▼
┌─────────────────┐
│ Production      │  Your VPS/Domain
│                 │  pettycash.yourdomain.com
└─────────────────┘
```

---

## Cost Breakdown

### Two Free Services on Render:
- Web Service #1 (Test): Free (sleeps)
- Web Service #2 (Prod): Free (sleeps)
- Database #1 (Test): Free 90 days
- Database #2 (Prod): Free 90 days
- **Total now: $0**
- **After 90 days: $14/month** ($7 per database)

### Single Service (Current):
- One web service: Free (sleeps)
- One database: Free 90 days
- **Total now: $0**
- **After 90 days: $7/month**

---

## Quick Commands

### Generate new SECRET_KEY for test environment:
```powershell
.\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Create test superuser (after test deployment):
Same auto-creation script runs, creates `admin` user

### Reset test database (clear all data):
In Render: Delete test database, create new one with same name, redeploy

---

## Which Should You Do?

**For now (next 2-3 months):**
- Keep current setup
- Use Render as your test/demo environment
- Local development only

**When you're ready to go live:**
- Create separate test service on Render
- Move to VPS with your domain for production
- Keep Render test environment for UAT

---

**Current status: You have a working test environment at `https://pettycash-system.onrender.com`!** ✅

You can add stakeholders, test workflows, and demonstrate the system. When you get your domain, you can decide whether to:
1. Point domain to Render (upgrade to paid)
2. Move to your own VPS
3. Keep Render for testing, VPS for production
