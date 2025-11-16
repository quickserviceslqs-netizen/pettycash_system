# Sentry Setup (notes)

This file outlines basic Sentry integration steps for error monitoring.

1. Create a Sentry project for `pettycash_system`.
2. Add DSN to environment variables in staging/production: `SENTRY_DSN`.
3. Install SDK: `pip install sentry-sdk`
4. Initialize in `pettycash_system/__init__.py` or `settings.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)
```

5. Configure release tagging in CI and set environment tags for staging/prod.

6. Add runbook: when critical errors spike, follow the incident runbook to collect logs, reproduce, and triage.
