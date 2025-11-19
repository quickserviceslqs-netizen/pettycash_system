# Deploy to Render - Quick Start (10 Minutes)

## 🚀 Fastest Deployment Path

### 1. Push to GitHub (2 min)
```powershell
git init
git add .
git commit -m "Deploy to Render"
git remote add origin https://github.com/YOUR_USERNAME/pettycash_system.git
git push -u origin main
```

### 2. Create Render Account (1 min)
- Go to https://render.com
- Sign up with GitHub (free, no credit card needed)

### 3. Create Database (1 min)
- Click **"New +"** → **"PostgreSQL"**
- Name: `pettycash-db`
- Plan: **Free**
- Click **"Create Database"**
- **Copy Internal Database URL** 📋

### 4. Create Web Service (2 min)
- Click **"New +"** → **"Web Service"**
- Connect GitHub repo: `pettycash_system`
- Configure:
  - **Name:** `pettycash-system`
  - **Runtime:** Python 3
  - **Build Command:** `./build.sh`
  - **Start Command:** `gunicorn pettycash_system.wsgi:application`
  - **Plan:** Free

### 5. Set Environment Variables (2 min)

Generate SECRET_KEY first:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Add these variables:
```
SECRET_KEY = [generated key from above]
DEBUG = False
ALLOWED_HOSTS = .onrender.com
CSRF_TRUSTED_ORIGINS = https://*.onrender.com
DATABASE_URL = [paste Internal Database URL]
PYTHON_VERSION = 3.11.7
```

### 6. Deploy! (1 min)
- Click **"Create Web Service"**
- Wait 3-5 minutes for deployment

### 7. Create Admin (1 min)
- Go to service → **"Shell"** tab
- Run: `python manage.py createsuperuser`

---

## ✅ Done!

**Your app:** `https://pettycash-system.onrender.com`
**Admin:** `https://pettycash-system.onrender.com/admin`

---

## ⚠️ Important Notes

**Free tier sleeps after 15 min** (wakes in 30 sec on first request)
**Database free for 90 days** (then $7/month)

---

## 💰 Cost After Free Period

- **Option 1:** Keep app free + pay $7/month for database
- **Option 2:** Upgrade to always-on $7/month app + $7/month DB = $14/month
- **Option 3:** Migrate to your own server when you get domain

---

## 🔄 Update Your App

```powershell
git add .
git commit -m "Updates"
git push
```

Render auto-deploys! 🎉

---

**Full guide:** `.deployment/RENDER_DEPLOYMENT.md`
