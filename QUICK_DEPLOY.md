# Quick Deploy to Railway - 5 Minute Guide

## Prerequisites
✅ Code pushed to GitHub
✅ Railway account (free - sign up with GitHub at https://railway.app)

---

## 🚀 Deploy in 5 Steps

### Step 1: Create Railway Project (1 min)
1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose `pettycash_system`
5. Click **"Deploy Now"**

### Step 2: Add Database (30 sec)
1. In project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Wait ~30 seconds for provisioning

### Step 3: Set Environment Variables (2 min)
Click web service → **"Variables"** → Add these:

```bash
SECRET_KEY=django-insecure-CHANGE-THIS-TO-SOMETHING-SECRET-12345
DEBUG=False
ALLOWED_HOSTS=.railway.app
CSRF_TRUSTED_ORIGINS=https://*.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

**Generate better SECRET_KEY:**
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 4: Generate Domain (10 sec)
1. Click service → **"Settings"**
2. Under "Domains", click **"Generate Domain"**
3. Copy your URL: `your-app-XXXX.up.railway.app`

### Step 5: Create Admin User (1 min)
1. Click service → **"Deployments"** → Latest
2. Click terminal icon (⌘) top right
3. Run:
```bash
python manage.py createsuperuser
```

---

## ✅ Done! Your app is live!

**Access your app:**
- Homepage: `https://your-app-XXXX.up.railway.app`
- Admin: `https://your-app-XXXX.up.railway.app/admin`

---

## 🔥 Common Issues

**Issue:** App won't start
**Fix:** Check logs - usually missing environment variable

**Issue:** Database connection failed
**Fix:** Verify `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`

**Issue:** Static files missing
**Fix:** Already configured with WhiteNoise - should work automatically

---

## 💰 Free Tier

- **$5 credit/month** (resets monthly)
- **~500 hours** usage (~20 days always-on)
- Perfect for testing/staging

---

## 📱 Update Your App

```powershell
git add .
git commit -m "Update"
git push
```

Railway auto-deploys! 🎉
