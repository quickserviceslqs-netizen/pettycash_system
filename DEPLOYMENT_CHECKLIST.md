# Pre-Deployment Checklist ✅

Before deploying to Railway/Render, ensure:

## Code Preparation

- [x] ✅ `requirements.txt` updated (gunicorn, whitenoise, dj-database-url)
- [x] ✅ `settings.py` configured for production (environment variables)
- [x] ✅ `Procfile` created
- [x] ✅ `runtime.txt` created
- [x] ✅ `.gitignore` configured
- [x] ✅ Static files configured (WhiteNoise)

## Git Repository

- [ ] Initialize git: `git init`
- [ ] Add files: `git add .`
- [ ] Commit: `git commit -m "Initial deployment commit"`
- [ ] Create GitHub repo
- [ ] Push to GitHub:
  ```powershell
  git remote add origin https://github.com/YOUR_USERNAME/pettycash_system.git
  git branch -M main
  git push -u origin main
  ```

## Railway Account

- [ ] Sign up at https://railway.app (use GitHub)
- [ ] Verify email

## Ready to Deploy!

Follow: `QUICK_DEPLOY.md` for 5-minute deployment

---

## After Deployment

- [ ] Generate domain
- [ ] Create superuser
- [ ] Test login
- [ ] Create sample data
- [ ] Share URL with team

---

**Everything is configured and ready to go!** 🚀
