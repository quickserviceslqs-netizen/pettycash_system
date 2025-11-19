# Production Deployment Checklist

**System:** Petty Cash Management System  
**Version:** 1.0  
**Date:** _____________  
**Deployed By:** _____________

---

## Pre-Deployment Checklist

### 1. Code Preparation

- [ ] All tests passing (unit, integration, security)
- [ ] Code reviewed and approved
- [ ] No `DEBUG = True` in settings
- [ ] No hardcoded credentials
- [ ] `SECRET_KEY` is production-ready (not default)
- [ ] All TODO/FIXME comments resolved
- [ ] Documentation updated
- [ ] CHANGELOG.md updated with release notes

### 2. Database Preparation

- [ ] All migrations created (`python manage.py makemigrations --check`)
- [ ] Migrations tested on staging
- [ ] Database backup taken
- [ ] Rollback plan documented
- [ ] Migration time estimated (< 5 min preferred)
- [ ] No breaking schema changes

### 3. Dependencies

- [ ] `requirements.txt` up to date
- [ ] All dependencies security-scanned (no critical vulnerabilities)
- [ ] Python version compatible (3.11+)
- [ ] Database version compatible (PostgreSQL 15+)

### 4. Configuration

- [ ] Environment variables configured
- [ ] `ALLOWED_HOSTS` set correctly
- [ ] `CORS_ALLOWED_ORIGINS` configured
- [ ] Database connection tested
- [ ] Redis/cache configured (if applicable)
- [ ] Email settings configured and tested
- [ ] Static files CDN configured (if applicable)
- [ ] Media files storage configured

### 5. Security

- [ ] HTTPS enforced
- [ ] HSTS enabled
- [ ] CSRF middleware enabled
- [ ] Security headers configured
- [ ] Firewall rules updated
- [ ] SSL certificate valid (not expiring soon)
- [ ] Secrets rotated (if needed)
- [ ] API keys active and valid

### 6. Monitoring & Logging

- [ ] Sentry configured (error tracking)
- [ ] Application logs configured
- [ ] Database slow query logging enabled
- [ ] Health check endpoint working
- [ ] Uptime monitoring configured
- [ ] Alert thresholds set

### 7. Backups

- [ ] Database backup automated
- [ ] Media files backup configured
- [ ] Backup restore tested
- [ ] Backup retention policy set
- [ ] Off-site backup storage configured

---

## Deployment Steps

### Step 1: Pre-Deployment Communication

- [ ] Notify stakeholders of deployment window
- [ ] Schedule deployment during low-traffic period
- [ ] Prepare rollback communication plan
- [ ] Put maintenance page ready (if needed)

**Deployment Window:** ________________  
**Expected Downtime:** ________________  
**Rollback Deadline:** ________________

### Step 2: Final Backup

```bash
# On production server
pg_dump -U postgres -d pettycash_db -F c -f backup_pre_deploy_$(date +%Y%m%d_%H%M%S).backup

# Verify backup
ls -lh backup_pre_deploy_*.backup
```

- [ ] Database backup created
- [ ] Backup size verified (not 0 bytes)
- [ ] Backup download confirmed

**Backup File:** ________________  
**Backup Size:** ________________

### Step 3: Code Deployment

```bash
# On production server
cd /var/www/pettycash_system
git fetch origin
git checkout main
git pull origin main

# Verify correct version
git log -1 --oneline
```

- [ ] Code pulled from repository
- [ ] Correct commit deployed
- [ ] Git status clean (no uncommitted changes)

**Commit Hash:** ________________

### Step 4: Dependencies Update

```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
pip list > installed_packages_$(date +%Y%m%d).txt
```

- [ ] Dependencies installed
- [ ] No installation errors
- [ ] Package list saved

### Step 5: Database Migration

```bash
# Dry run (check migration plan)
python manage.py migrate --plan

# Apply migrations
python manage.py migrate --noinput

# Verify migration status
python manage.py showmigrations
```

- [ ] Migration plan reviewed
- [ ] Migrations applied successfully
- [ ] No migration errors
- [ ] All migrations marked as applied

**Migration Duration:** ________________

### Step 6: Static Files

```bash
python manage.py collectstatic --noinput --clear
```

- [ ] Static files collected
- [ ] No collection errors
- [ ] CDN cache invalidated (if applicable)

### Step 7: Application Restart

```bash
# Gunicorn
sudo systemctl restart gunicorn
sudo systemctl status gunicorn

# Nginx
sudo systemctl reload nginx
sudo systemctl status nginx

# Celery (if applicable)
sudo systemctl restart celery
sudo systemctl status celery
```

- [ ] Gunicorn restarted
- [ ] Nginx reloaded
- [ ] Celery restarted (if applicable)
- [ ] All services running

### Step 8: Smoke Tests

```bash
python scripts/smoke_tests.py --env production
```

- [ ] Health check passes
- [ ] Login page loads
- [ ] Dashboard accessible
- [ ] API responds
- [ ] Database connection works
- [ ] Static files load
- [ ] No 500 errors

**Test Results:** ________________

### Step 9: Verification

Manual verification:

- [ ] Login with test account
- [ ] Create test requisition
- [ ] Submit for approval
- [ ] Approve requisition (as different user)
- [ ] Execute payment (as treasury user)
- [ ] View reports
- [ ] Check alerts
- [ ] Verify dashboard metrics

**Verified By:** ________________

---

## Post-Deployment

### Step 10: Monitoring

First 30 minutes:

- [ ] Monitor error logs: `tail -f /var/log/pettycash/error.log`
- [ ] Monitor access logs: `tail -f /var/log/nginx/access.log`
- [ ] Check Sentry dashboard (no new errors)
- [ ] Monitor server resources (CPU, memory, disk)
- [ ] Check database connections
- [ ] Verify scheduled tasks running

First 24 hours:

- [ ] Monitor user reports
- [ ] Check error rate trends
- [ ] Review performance metrics
- [ ] Validate automated backups
- [ ] Confirm email delivery

### Step 11: Communication

- [ ] Notify stakeholders of successful deployment
- [ ] Update status page (if applicable)
- [ ] Send deployment summary email
- [ ] Update documentation
- [ ] Close deployment ticket

**Deployment Complete:** ________________

---

## Rollback Procedure

### Triggers for Rollback

- Critical bug affecting core functionality
- Database corruption
- Security vulnerability exposed
- Error rate > 5%
- User-facing outage > 15 minutes

### Rollback Steps

**EXECUTE IMMEDIATELY IF TRIGGERED**

```bash
# 1. Stop application
sudo systemctl stop gunicorn

# 2. Revert code
cd /var/www/pettycash_system
git checkout <previous-commit-hash>

# 3. Revert migrations (if applied)
python manage.py migrate <app_name> <previous_migration_number>

# 4. Restore database (if needed)
psql -U postgres -d pettycash_db < backup_pre_deploy_YYYYMMDD_HHMMSS.backup

# 5. Restart application
sudo systemctl start gunicorn
sudo systemctl reload nginx

# 6. Verify rollback
python scripts/smoke_tests.py --env production
```

- [ ] Application stopped
- [ ] Code reverted to previous version
- [ ] Database restored (if needed)
- [ ] Application restarted
- [ ] Smoke tests pass
- [ ] Stakeholders notified

**Rollback Completed:** ________________  
**Reason:** ________________

---

## Environment Configuration

### Environment Variables (`.env` file)

```bash
# Django
SECRET_KEY=<production-secret-key>
DEBUG=False
ALLOWED_HOSTS=pettycash.yourcompany.com,www.yourcompany.com

# Database
DATABASE_URL=postgresql://pettycash_user:password@localhost:5432/pettycash_db

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourcompany.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@yourcompany.com
EMAIL_HOST_PASSWORD=<email-password>

# Sentry
SENTRY_DSN=https://...@sentry.io/...

# Static/Media
STATIC_ROOT=/var/www/pettycash_system/staticfiles
MEDIA_ROOT=/var/www/pettycash_system/media

# Cache (Redis)
REDIS_URL=redis://localhost:6379/0
```

### Systemd Service (`/etc/systemd/system/gunicorn.service`)

```ini
[Unit]
Description=Petty Cash Management System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/pettycash_system
Environment="PATH=/var/www/pettycash_system/venv/bin"
ExecStart=/var/www/pettycash_system/venv/bin/gunicorn \
    --workers 4 \
    --bind unix:/var/www/pettycash_system/gunicorn.sock \
    pettycash_system.wsgi:application

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration (`/etc/nginx/sites-available/pettycash`)

```nginx
server {
    listen 80;
    server_name pettycash.yourcompany.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pettycash.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/pettycash.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pettycash.yourcompany.com/privkey.pem;

    client_max_body_size 10M;

    location /static/ {
        alias /var/www/pettycash_system/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/pettycash_system/media/;
    }

    location / {
        proxy_pass http://unix:/var/www/pettycash_system/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Health Checks

### Manual Health Checks

```bash
# 1. Application health
curl https://pettycash.yourcompany.com/health/

# 2. Database connection
python manage.py dbshell <<< "SELECT 1;"

# 3. Static files
curl -I https://pettycash.yourcompany.com/static/css/styles.css

# 4. API endpoints
curl https://pettycash.yourcompany.com/api/

# 5. Gunicorn status
sudo systemctl status gunicorn

# 6. Nginx status
sudo systemctl status nginx

# 7. Database status
sudo systemctl status postgresql
```

### Automated Health Checks

Configure uptime monitoring:
- **Pingdom:** https://www.pingdom.com
- **UptimeRobot:** https://uptimerobot.com
- **StatusCake:** https://www.statuscake.com

Monitor:
- `/health/` endpoint every 1 minute
- SSL certificate expiry
- Response time < 2 seconds

---

## Performance Benchmarks

### Expected Response Times (95th percentile)

| Endpoint | Target | Max Acceptable |
|----------|--------|----------------|
| `/health/` | 50ms | 100ms |
| `/dashboard/` | 500ms | 1s |
| `/api/requisitions/` | 300ms | 800ms |
| `/api/treasury/payments/` | 400ms | 1s |
| `/reports/` | 2s | 5s |

### Resource Usage

| Metric | Expected | Alert Threshold |
|--------|----------|-----------------|
| CPU | 20-40% | > 70% |
| Memory | 2-4 GB | > 6 GB |
| Disk I/O | Low | > 80% utilization |
| Database Connections | 10-30 | > 80 |
| Response Time | < 500ms | > 2s |

---

## Troubleshooting

### Common Issues

#### 1. 502 Bad Gateway
**Cause:** Gunicorn not running
**Fix:**
```bash
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

#### 2. Static Files Not Loading
**Cause:** Not collected or wrong path
**Fix:**
```bash
python manage.py collectstatic --noinput
sudo systemctl reload nginx
```

#### 3. Database Connection Errors
**Cause:** Wrong credentials or PostgreSQL not running
**Fix:**
```bash
sudo systemctl status postgresql
# Check DATABASE_URL in .env
```

#### 4. 500 Internal Server Error
**Cause:** Application error
**Fix:**
```bash
tail -f /var/log/pettycash/error.log
# Check Sentry dashboard
```

---

## Sign-off

### Deployment Team

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Developer | ____________ | ____________ | ______ |
| QA Lead | ____________ | ____________ | ______ |
| DevOps | ____________ | ____________ | ______ |
| Project Manager | ____________ | ____________ | ______ |

### Approval

**Deployment Approved:** ☐ Yes ☐ No  
**Approved By:** ________________  
**Date:** ________________

---

## Notes

_Record any issues, observations, or deviations from this checklist:_

________________________________________________________________________________________________________

________________________________________________________________________________________________________

________________________________________________________________________________________________________

---

**End of Deployment Checklist**
