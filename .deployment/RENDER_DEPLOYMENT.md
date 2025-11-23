# Deploy to Render - Complete Guide

## Why Render is Great

✅ **Truly free tier** (no credit card required for free tier)
✅ **PostgreSQL included** (free for 90 days, then $7/month)
✅ **Auto-deploy from GitHub**
✅ **Free HTTPS/SSL**
✅ **Custom domains supported**
✅ **Better free tier than Railway** (doesn't count hours)

**Downside:** Free tier sleeps after 15 min inactivity (wakes in ~30 sec on first request)

---

## 🚀 Deploy in 10 Minutes

### Step 1: Push Code to GitHub (2 min)

```powershell
# If not already done
git init
git add .
git commit -m "Ready for Render deployment"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/pettycash_system.git
git branch -M main
git push -u origin main
```

---

### Step 2: Create Render Account (1 min)

1. Go to https://render.com
2. Click **"Get Started for Free"**
3. Sign up with GitHub (recommended)
4. Verify your email

---

### Step 3: Create PostgreSQL Database (2 min)

1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name:** `pettycash-db`
   - **Database:** `pettycash_db` (auto-filled)
   - **User:** `pettycash_user` (auto-filled)
   - **Region:** Choose closest to you
   - **Plan:** **Free** ⭐
3. Click **"Create Database"**
4. Wait ~30 seconds for provisioning
5. **Important:** Copy the **Internal Database URL** (you'll need this)

---

### Step 4: Create Web Service (3 min)

1. Click **"New +"** → **"Web Service"**
2. Click **"Build and deploy from a Git repository"** → **"Next"**
3. Connect your GitHub repo:
   - If first time: Click **"Connect GitHub"** → Authorize Render
   - Select `pettycash_system` repository
4. Click **"Connect"**

---

### Step 5: Configure Web Service (2 min)

Fill in the form:

#### Basic Settings
- **Name:** `pettycash-system` (will be your URL)
- **Region:** Same as your database
- **Branch:** `main`
- **Root Directory:** (leave blank)
- **Runtime:** `Python 3`

#### Build & Deploy
- **Build Command:** `./build.sh`
- **Start Command:** `gunicorn pettycash_system.wsgi:application`

#### Plan
- **Instance Type:** **Free** ⭐

---

### Step 6: Add Environment Variables (2 min)

Scroll down to **"Environment Variables"** and add these:

Click **"Add Environment Variable"** for each:

```
Key: SECRET_KEY
Value: [Generate using: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"]
```

```
Key: DEBUG
Value: False
```

```
Key: ALLOWED_HOSTS
Value: .onrender.com
```

```
Key: CSRF_TRUSTED_ORIGINS
Value: https://*.onrender.com
```

```
Key: DATABASE_URL
Value: [Paste Internal Database URL from Step 3]
```

```
Key: PYTHON_VERSION
Value: 3.11.7
```

**To generate SECRET_KEY:**
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### Step 7: Deploy! (1 min)

1. Click **"Create Web Service"** at the bottom
2. Render will start building (takes 2-5 minutes)
3. Watch the build logs in real-time

**Build stages:**
1. Installing dependencies
2. Collecting static files
3. Running migrations
4. Starting Gunicorn

---

### Step 8: Access Your App! (30 sec)

Once deployed (you'll see "Live" with green dot):

**Your URL:** `https://pettycash-system.onrender.com`

Test these pages:
- **Homepage:** `https://pettycash-system.onrender.com/`
- **Admin:** `https://pettycash-system.onrender.com/admin/`
- **Login:** `https://pettycash-system.onrender.com/accounts/login/`

---

### Step 9: Create Superuser (1 min)

1. In Render dashboard, go to your web service
2. Click **"Shell"** tab (on the left)
3. Click **"Connect"** (opens terminal)
4. Run:
```bash
python manage.py createsuperuser
```
5. Enter username, email, password
6. Done! ✅

---

## 🎉 Your App is Live!

**URL:** `https://pettycash-system.onrender.com`

---

## Important Notes

### Free Tier Behavior

⚠️ **Free tier apps sleep after 15 min of inactivity**
- First request after sleep takes ~30-60 seconds (cold start)
- Subsequent requests are instant
- Good for: Testing, demos, low-traffic apps

💡 **To keep it awake:**
- Use a cron job to ping your app every 10 minutes
- Or upgrade to paid plan ($7/month - always on)

### Database Free Tier

📅 **PostgreSQL free for 90 days**
- After 90 days: $7/month (very reasonable)
- Data is retained, just starts billing
- You'll get email reminders before it expires

---

## Updating Your App

```powershell
# Make changes
git add .
git commit -m "Updated feature"
git push origin main
```

Render **automatically redeploys** when you push! 🚀

---

## Adding Custom Domain (When You Get One)

1. In Render dashboard, go to your web service
2. Click **"Settings"** tab
3. Scroll to **"Custom Domains"**
4. Click **"Add Custom Domain"**
5. Enter your domain: `pettycash.yourdomain.com`
6. Add DNS records as shown (CNAME or A record)
7. Render automatically provisions SSL certificate

**DNS Configuration:**
```
Type: CNAME
Name: pettycash (or www)
Value: pettycash-system.onrender.com
```

---

## Monitoring

### View Logs
1. Go to your service
2. Click **"Logs"** tab
3. Real-time logs appear

### Metrics
1. Click **"Metrics"** tab
2. View:
   - Response times
   - CPU usage
   - Memory usage
   - Request counts

### Alerts
1. Click **"Settings"** → **"Notifications"**
2. Add email for deploy notifications

---

## Cost Breakdown

### Free Forever
- ✅ Web service (sleeps after 15 min)
- ✅ PostgreSQL (90 days free)
- ✅ HTTPS/SSL
- ✅ Custom domain support
- ✅ Unlimited deploys

### After 90 Days
- **Database only:** $7/month
- **Keep app free** (with sleep)

### Fully Paid (No Sleep)
- **Web service:** $7/month (always on)
- **Database:** $7/month
- **Total:** $14/month

---

## Troubleshooting

### Build Fails

**Error:** `build.sh: Permission denied`
**Fix:** Make script executable
```powershell
git update-index --chmod=+x build.sh
git commit -m "Make build.sh executable"
git push
```

### Static Files Not Loading

**Error:** 404 on static files
**Fix:** Already configured with WhiteNoise - should work automatically
Check logs for collectstatic errors

### Database Connection Error

**Error:** `could not connect to server`
**Fix:** 
- Verify DATABASE_URL is set correctly
- Use **Internal Database URL** (not External)
- Check database is running (green dot in dashboard)

### App Won't Wake from Sleep

**Issue:** Takes too long to wake
**Fix:** Normal for free tier (30-60 sec)
**Solution:** Upgrade to $7/month paid plan for always-on

---

## Render vs Railway Comparison

| Feature | Render Free | Railway Free |
|---------|-------------|--------------|
| **App uptime** | Sleeps after 15 min | Always on (~500 hrs/mo) |
| **Database** | Free 90 days | Included in credit |
| **Credit limit** | None | $5/month |
| **Best for** | Long-term free | Short-term testing |
| **Cold start** | 30-60 sec | Instant |
| **Duration** | Forever (with sleep) | ~20 days/month |

**For your case:** Render is better for long-term free tier!

---

## Next Steps

1. ✅ Deploy to Render (follow steps above)
2. ✅ Create superuser
3. ✅ Test all features
4. ✅ Add sample data
5. ✅ Share URL with team
6. ⏳ Get custom domain (add when ready)
7. 📅 In 90 days: Decide on database ($7/month or migrate)

---

## Support

**Render Docs:** https://render.com/docs
**Discord:** https://render.com/discord
**Status:** https://status.render.com

---

**Your app will be live at:** `https://pettycash-system.onrender.com` 🚀

**Total setup time:** ~10 minutes
