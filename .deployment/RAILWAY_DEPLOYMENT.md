# Deploy to Railway.app - Step by Step

## Prerequisites
- GitHub account
- Railway account (sign up at https://railway.app with GitHub)
- Your code pushed to GitHub

---

## Step 1: Push Code to GitHub

```powershell
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit - ready for deployment"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/pettycash_system.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy on Railway

### A. Create New Project

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `pettycash_system` repository
5. Click **"Deploy Now"**

### B. Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Wait for database to provision (~30 seconds)

### C. Configure Environment Variables

Click on your web service → **"Variables"** tab:

```bash
# Django Settings
SECRET_KEY=your-super-secret-key-change-this-now-12345678
DEBUG=False
ALLOWED_HOSTS=.railway.app
CSRF_TRUSTED_ORIGINS=https://*.railway.app

# Database (Railway auto-provides these, but verify)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Static Files
DISABLE_COLLECTSTATIC=0

# Email (Optional - configure later)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Important:** Railway automatically sets `DATABASE_URL` when you add PostgreSQL.

### D. Connect Database to Web Service

1. Click on PostgreSQL service
2. Go to **"Connect"** tab
3. Copy the connection variables
4. In your web service, the `DATABASE_URL` should reference: `${{Postgres.DATABASE_URL}}`

---

## Step 3: Generate Secret Key

```powershell
# In your terminal
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and use it for `SECRET_KEY` environment variable.

---

## Step 4: Update Django Settings

Your `pettycash_system/settings.py` should already have:

```python
import os
import dj_database_url

# Security
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-fallback-key')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

---

## Step 5: Deploy!

Railway automatically deploys when you:
1. Push to GitHub (if connected)
2. Click **"Deploy"** button in Railway dashboard

**Deployment takes 2-5 minutes.**

---

## Step 6: Access Your App

1. In Railway dashboard, click on your web service
2. Go to **"Settings"** tab
3. Under **"Domains"**, you'll see your app URL:
   - `your-app-name.railway.app`
4. Click **"Generate Domain"** if not already generated

**Your app is now live!** 🎉

---

## Step 7: Create Superuser

After deployment, create an admin user:

1. In Railway dashboard, click your web service
2. Go to **"Deployments"** tab
3. Click on the latest deployment
4. Click **"View Logs"**
5. In the top right, click the terminal icon (⌘)
6. Run:

```bash
python manage.py createsuperuser
```

Follow the prompts to create admin account.

---

## Step 8: Test Your Deployment

Visit your Railway URL:
- **Homepage:** `https://your-app-name.railway.app/`
- **Admin:** `https://your-app-name.railway.app/admin/`
- **Login:** `https://your-app-name.railway.app/accounts/login/`

---

## Monitoring & Logs

### View Logs
1. Click your service → **"Deployments"** → Latest deployment
2. Real-time logs appear at bottom

### Monitor Resources
1. Click your service → **"Metrics"** tab
2. View CPU, Memory, Network usage

---

## Adding Custom Domain (Later)

When you get your domain:

1. In Railway, click your service → **"Settings"**
2. Scroll to **"Domains"**
3. Click **"Custom Domain"**
4. Enter your domain: `pettycash.yourdomain.com`
5. Add CNAME record in your DNS provider:
   - **Type:** CNAME
   - **Name:** pettycash (or @)
   - **Value:** your-app-name.railway.app

Railway automatically provisions SSL certificate.

---

## Cost Management

### Free Tier Limits
- **$5 credit/month** (resets monthly)
- **500 hours** of usage (~20 days always-on)
- **100GB egress** bandwidth

### Tips to Stay Free
- Use Railway for testing/staging initially
- Upgrade to $5/month plan when ready for production
- Monitor usage in **"Usage"** tab

---

## Troubleshooting

### Issue: "Application Error"
**Solution:** Check logs for errors
```bash
# Common fixes
- Verify SECRET_KEY is set
- Check ALLOWED_HOSTS includes .railway.app
- Ensure database migrations ran
```

### Issue: Static Files Not Loading
**Solution:**
```bash
# In Railway service settings
DISABLE_COLLECTSTATIC=0

# Check settings.py
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
```

### Issue: Database Connection Error
**Solution:**
- Verify PostgreSQL service is running
- Check `DATABASE_URL` variable references `${{Postgres.DATABASE_URL}}`

---

## Updating Your App

```powershell
# Make changes locally
git add .
git commit -m "Updated feature X"
git push origin main
```

Railway automatically redeploys! 🚀

---

## Alternative: Deploy to Render

If you prefer Render:

1. Go to https://render.com
2. Click **"New +"** → **"Web Service"**
3. Connect GitHub repo
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn pettycash_system.wsgi`
5. Add PostgreSQL database (free for 90 days)
6. Set environment variables (same as Railway)
7. Deploy!

---

## Next Steps

✅ Deploy to Railway  
✅ Create superuser  
✅ Test all features  
✅ Add sample data  
✅ Share app URL with stakeholders  
⏳ Get custom domain  
⏳ Configure email (when ready)  
⏳ Set up monitoring  

---

**Your app will be live at:** `https://your-app-name.railway.app`

**Deployment time:** ~5 minutes 🚀
