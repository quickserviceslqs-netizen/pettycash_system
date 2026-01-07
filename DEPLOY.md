Deployment checklist

Superuser from environment variables

You can configure an admin (superuser) to be created automatically during bootstrap by setting these environment variables on your host (Render, Railway, Heroku, etc):

- ADMIN_EMAIL: admin email (and username) to create
- ADMIN_PASSWORD: admin password (must be a secure strong password)
- Optional: ADMIN_FIRST_NAME, ADMIN_LAST_NAME

How it works

- After migrations succeed, the bootstrap script (`scripts/bootstrap_db.py`) ensures a superuser exists if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set.
- Creation is idempotent: if a user with the given email already exists, creation is skipped.
- For security: set these environment variables via your hosting provider's secrets/environment variables dashboard (do NOT commit them to source control).

Example (Render):

1. Go to your Render service dashboard -> Environment -> Environment Variables
2. Add `ADMIN_EMAIL` and `ADMIN_PASSWORD` (and optional name fields)
3. Deploy — the bootstrap script will create the admin automatically.

Notes

- If you prefer the admin created only for staging environments, avoid setting `ADMIN_EMAIL`/`ADMIN_PASSWORD` in production or use different credentials per environment.
- If you need a separate non-superuser admin or different roles, create them manually in Django Admin or via a custom management command.
