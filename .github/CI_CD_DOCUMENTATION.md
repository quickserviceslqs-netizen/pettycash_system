# CI/CD Pipeline Documentation

## Overview

Automated CI/CD pipeline using GitHub Actions for the Petty Cash Management System. The pipeline includes code quality checks, security scanning, automated testing, and deployment to staging and production environments.

---

## Pipeline Stages

### 1. Code Quality & Linting

**Triggers:** All pushes and pull requests

**Steps:**
- Code formatting check (Black)
- Import sorting check (isort)
- Linting (flake8)
- Static analysis (Pylint)

**Pass Criteria:**
- No syntax errors
- No undefined names
- Pylint score ≥ 7.0

```bash
# Run locally
black --check .
isort --check-only .
flake8 .
pylint --fail-under=7.0 accounts/ organization/ transactions/ treasury/
```

### 2. Security Scanning

**Triggers:** All pushes and pull requests

**Steps:**
- Dependency vulnerability scan (Safety)
- Code security analysis (Bandit)

**Artifacts:**
- `safety-report.json`
- `bandit-report.json`

```bash
# Run locally
safety check
bandit -r . -ll
```

### 3. Unit & Integration Tests

**Triggers:** All pushes and pull requests

**Services:**
- PostgreSQL 15 test database

**Steps:**
- Unit tests with coverage
- Integration tests
- Coverage report upload to Codecov

**Pass Criteria:**
- All tests pass
- Coverage ≥ 80% (recommended)

```bash
# Run locally
coverage run --source='.' manage.py test --settings=test_settings
coverage report
python manage.py test tests.integration --settings=test_settings
```

### 4. Security Tests

**Triggers:** All pushes and pull requests

**Steps:**
- RBAC tests
- CSRF protection tests
- Injection prevention tests

```bash
# Run locally
python manage.py test tests.security --settings=test_settings
```

### 5. Performance Tests

**Triggers:** Pushes to `staging` or `main` branches only

**Steps:**
- Start Django development server
- Run Locust smoke tests (10 users, 2 minutes)

**Artifacts:**
- Performance results CSV

```bash
# Run locally
locust -f load_tests/locustfile.py --host=http://localhost:8000 \
  --users 10 --spawn-rate 2 --run-time 2m --headless --csv=results
```

### 6. Deploy to Staging

**Triggers:** Push to `staging` branch (after all tests pass)

**Environment:** `staging`

**Steps:**
1. Collect static files
2. Run database migrations
3. Deploy to staging server
4. Run smoke tests

**Requirements:**
- `STAGING_DATABASE_URL` secret
- `STAGING_SECRET_KEY` secret
- `STAGING_DEPLOY_KEY` secret
- `STAGING_HOST` secret
- `STAGING_USER` secret

### 7. Deploy to Production

**Triggers:** Push to `main` branch (after all tests pass)

**Environment:** `production`

**Steps:**
1. Collect static files
2. Create database backup
3. Run database migrations
4. Deploy to production
5. Run smoke tests
6. Notify on success/failure
7. Rollback on failure

**Requirements:**
- `PROD_DATABASE_URL` secret
- `PROD_SECRET_KEY` secret
- `PROD_DEPLOY_KEY` secret
- `PROD_HOST` secret
- `PROD_USER` secret

---

## GitHub Secrets Configuration

### Required Secrets

Navigate to: **Settings → Secrets and variables → Actions**

#### Staging Secrets
```
STAGING_DATABASE_URL=postgresql://user:pass@host:5432/staging_db
STAGING_SECRET_KEY=your-secret-key-here
STAGING_DEPLOY_KEY=ssh-private-key-or-api-token
STAGING_HOST=staging.yourcompany.com
STAGING_USER=deploy
```

#### Production Secrets
```
PROD_DATABASE_URL=postgresql://user:pass@host:5432/prod_db
PROD_SECRET_KEY=your-secret-key-here
PROD_DEPLOY_KEY=ssh-private-key-or-api-token
PROD_HOST=pettycash.yourcompany.com
PROD_USER=deploy
```

### Optional Secrets
```
CODECOV_TOKEN=your-codecov-token
SLACK_WEBHOOK=https://hooks.slack.com/services/...
SENTRY_DSN=https://...@sentry.io/...
```

---

## Branch Strategy

### Branches

- **`main`**: Production-ready code. Auto-deploys to production.
- **`staging`**: Pre-production testing. Auto-deploys to staging.
- **`develop`**: Development integration branch. CI only, no deployment.
- **`feature/*`**: Feature branches. CI on pull requests.
- **`bugfix/*`**: Bug fix branches. CI on pull requests.

### Workflow

```
feature/new-feature → develop → staging → main
                      ↓         ↓         ↓
                     CI      Staging   Production
```

1. Create feature branch from `develop`
2. Develop and test locally
3. Create pull request to `develop`
4. CI runs on pull request
5. Merge to `develop` after review
6. Merge `develop` to `staging` for testing
7. Staging deployment + smoke tests
8. Merge `staging` to `main` for production
9. Production deployment + smoke tests

---

## Running CI/CD Locally

### Prerequisites
```bash
pip install black isort flake8 pylint safety bandit coverage locust
```

### Full CI Simulation
```bash
# 1. Code quality
black --check .
isort --check-only .
flake8 .
pylint --fail-under=7.0 accounts/ organization/ transactions/ treasury/

# 2. Security
safety check
bandit -r . -ll

# 3. Tests
coverage run --source='.' manage.py test --settings=test_settings
coverage report
python manage.py test tests.integration --settings=test_settings
python manage.py test tests.security --settings=test_settings

# 4. Performance (optional)
python manage.py runserver &
sleep 5
locust -f load_tests/locustfile.py --host=http://localhost:8000 \
  --users 10 --spawn-rate 2 --run-time 1m --headless
```

---

## Smoke Tests

### Running Smoke Tests

```bash
# Local
python scripts/smoke_tests.py --env local

# Staging
python scripts/smoke_tests.py --env staging

# Production
python scripts/smoke_tests.py --env production

# Custom URL
python scripts/smoke_tests.py --env staging --url https://custom.url.com
```

### Smoke Test Coverage

- ✅ Health check endpoint
- ✅ Static files availability
- ✅ Login page loads
- ✅ API endpoints respond
- ✅ Database connection
- ✅ Authentication redirects

---

## Deployment Process

### Automatic Deployment

1. **Push to `staging` branch:**
   ```bash
   git checkout staging
   git merge develop
   git push origin staging
   ```
   → CI runs → Tests pass → Auto-deploy to staging

2. **Push to `main` branch:**
   ```bash
   git checkout main
   git merge staging
   git push origin main
   ```
   → CI runs → Tests pass → Auto-deploy to production

### Manual Deployment Trigger

Re-run failed workflow:
1. Go to **Actions** tab on GitHub
2. Select failed workflow run
3. Click **Re-run failed jobs**

### Deployment Rollback

If deployment fails, the pipeline automatically attempts rollback. Manual rollback:

```bash
# On production server
cd /var/www/pettycash_system
git checkout <previous-commit-hash>
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
sudo systemctl restart gunicorn
```

---

## Monitoring & Notifications

### Pipeline Status

View pipeline status:
- **GitHub:** Repository → Actions tab
- **Badge:** Add to README.md

```markdown
![CI/CD](https://github.com/yourcompany/pettycash_system/workflows/CI/CD%20Pipeline/badge.svg)
```

### Notifications

**Email Notifications:**
GitHub sends emails on workflow failures (configure in Settings → Notifications)

**Slack Integration (optional):**
```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Troubleshooting

### Common Issues

#### 1. Tests Fail on CI but Pass Locally
**Cause:** Environment differences
**Solution:**
```bash
# Match CI Python version
python --version  # Should match CI (3.11)

# Use exact dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. Migration Failures
**Cause:** Migration conflicts or missing migrations
**Solution:**
```bash
# Check migration status
python manage.py showmigrations

# Create missing migrations
python manage.py makemigrations
```

#### 3. Static Files Not Loading
**Cause:** `collectstatic` not run
**Solution:**
```bash
python manage.py collectstatic --noinput
```

#### 4. Database Connection Failed
**Cause:** Invalid `DATABASE_URL` secret
**Solution:**
- Verify secret format: `postgresql://user:pass@host:5432/db`
- Test connection locally with same credentials

#### 5. Deployment Timeout
**Cause:** Large static files or slow network
**Solution:**
- Increase timeout in workflow (default: 360s)
- Optimize static files (minify CSS/JS)

---

## Performance Benchmarks

### CI Pipeline Duration

| Stage | Expected Duration |
|-------|-------------------|
| Lint | 1-2 min |
| Security Scan | 2-3 min |
| Tests | 5-10 min |
| Security Tests | 2-3 min |
| Performance Tests | 3-5 min |
| Deploy Staging | 5-10 min |
| Deploy Production | 5-10 min |

**Total CI Runtime:** ~15-25 minutes for full pipeline

---

## Best Practices

1. **Run tests locally** before pushing
2. **Use pull requests** for code review
3. **Keep branches short-lived** (< 1 week)
4. **Review CI logs** for failures
5. **Monitor coverage trends** over time
6. **Tag releases** in production
7. **Document breaking changes** in commit messages
8. **Test staging thoroughly** before production deploy

---

## Next Steps

1. ✅ Configure GitHub secrets
2. ✅ Set up staging environment
3. ✅ Set up production environment
4. ✅ Add Codecov integration
5. 📋 Configure Slack notifications
6. 📋 Set up Sentry error tracking
7. 📋 Add automated database backups
8. 📋 Configure CDN for static files

---

## Support

**CI/CD Issues:** devops@yourcompany.com  
**Pipeline Documentation:** This file  
**GitHub Actions Docs:** https://docs.github.com/en/actions
