Deployment checklist

Superuser from environment variables

You can configure an admin (superuser) to be created automatically during bootstrap by setting these environment variables on your host (Render, Railway, Heroku, etc):

- ADMIN_EMAIL: admin email (and username) to create
- ADMIN_PASSWORD: admin password (must be a secure strong password)
- Optional: ADMIN_USERNAME (defaults to `ADMIN_EMAIL` if omitted)
- Optional: ADMIN_FIRST_NAME, ADMIN_LAST_NAME

Updating an existing superuser

- If you change `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_FIRST_NAME` or `ADMIN_LAST_NAME` and redeploy, the bootstrap script will attempt to update the existing admin user to match those values (idempotent).
- Rules:
  - The script tries to find an existing user by `ADMIN_EMAIL`, then by `ADMIN_USERNAME`.
  - If a username or email is already used by a different account, the script will skip changing that field and print a message.
  - Password updates are applied when `ADMIN_PASSWORD` is set (so you can rotate passwords via env vars and redeploy).
- If `ADMIN_USERNAME` is already taken by an existing user, the bootstrap will update that user's password and elevate them to `is_superuser`/`is_staff` (no failure) — it will not error on username collision.
- **Superuser cleanup**: The script will delete all other superusers to ensure only one superuser exists (the one defined by env vars). This prevents hardcoded or leftover superusers from persisting.

REQUIRE_SUPERUSER (enforce admin at startup)

- Set `REQUIRE_SUPERUSER=true` in production if you want the app to refuse to start when there is no superuser and `ADMIN_EMAIL`/`ADMIN_PASSWORD` are not provided. This ensures an operator cannot accidentally bring up an instance without an admin account.
- If `REQUIRE_SUPERUSER=true` and `ADMIN_EMAIL`/`ADMIN_PASSWORD` are missing, Django will raise an `ImproperlyConfigured` error at startup and the deploy will fail.

ADMIN_FORCE_CREATE (override existing superusers)

- Set `ADMIN_FORCE_CREATE=true` to force a destructive override on deploy: the bootstrap will delete all existing superusers and create a single superuser from `ADMIN_EMAIL`/`ADMIN_PASSWORD`/`ADMIN_USERNAME`.
- Use with caution — this is destructive and will remove other superuser accounts. Mark the variable as a secret in Render and only enable it when you explicitly want to replace existing superusers.

Security note: changing the password via an env var will immediately update the account on the next deploy — use your secrets manager and rotate safely.

Sensitive handling
- The bootstrap script avoids printing sensitive values (like `ADMIN_PASSWORD`) to logs. It masks such values when running commands.
- Still, treat these env vars as secrets in Render (mark them secret/private) and do not paste them into logs or public places.

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
