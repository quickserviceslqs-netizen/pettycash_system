# Petty Cash System - AI Coding Agent Instructions

## Architecture Overview
This is a multi-tenant Django web application for managing petty cash requisitions with approval workflows and M-Pesa payments. Key components:
- **accounts**: Custom user model with roles (staff, treasury, CFO, etc.) and app-based permissions
- **organization**: Company hierarchy (Company → Region → Branch → Department → CostCenter)
- **transactions**: Requisition model with status workflow (draft → pending approvals → paid/rejected)
- **workflow**: ApprovalThreshold model defines escalation rules based on amount and origin
- **treasury**: Fund balances, payments, and M-Pesa integration
- **reports**: Analytics and budgeting reports
- **settings_manager**: Dynamic system settings (currencies, timeouts, etc.)
- **system_maintenance**: Maintenance mode and IP/device whitelisting

Multi-tenancy implemented via CompanyMiddleware (thread-local company context) and CompanyManager (automatic company filtering).

## Critical Developer Workflows
- **Setup**: Run `python scripts/bootstrap_db.py` after migrations to initialize superuser and settings
- **Superuser Creation**: Set `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`, and optionally `DJANGO_SUPERUSER_USERNAME` environment variables; the build script will create the superuser automatically
- **Testing**: Use custom test scripts like `python test_all_settings.py` or `python run_all_settings_tests.py` instead of `manage.py test` for comprehensive validation
- **Deployment**: Execute `bash build.sh` for production builds (handles static files, DB checks, and post-deploy seeding)
- **Data Loading**: `python manage.py load_comprehensive_data` for test data; `python create_approval_thresholds.py` for workflow setup
- **Migrations**: Always run `python manage.py migrate` before starting server; check for unapplied migrations in logs

## Project-Specific Patterns
- **Access Control**: Combine role-based logic with app assignments (`user.assigned_apps`) and Django permissions. Check `accounts.permissions.get_user_apps()` in views.
- **Multi-Tenancy Filtering**: Use `CompanyManager` for automatic company scoping. Explicitly filter by `company` field in queries.
- **Workflow Resolution**: Use `workflow.services.resolver.find_approval_threshold()` to determine approval paths based on requisition amount and origin.
- **Status Transitions**: Requisitions follow strict state machine; use `workflow.services.workflow_service.advance_workflow()` for state changes.
- **M-Pesa Integration**: Payments via `treasury.services.mpesa_service`; callback handling in `treasury.views.api_callback`.
- **Settings Management**: Avoid hardcoded values; use `settings_manager.models.SystemSetting` with fallbacks in `pettycash_system.settings`.
- **Error Handling**: Log security events via `pettycash_system.ip_whitelist_middleware.SecurityLoggingMiddleware`; use maintenance mode for deployments.

## Key Files to Reference
- [pettycash_system/settings.py](pettycash_system/settings.py): INSTALLED_APPS, middleware stack, M-Pesa config
- [accounts/models.py](accounts/models.py): User model with roles and app assignments
- [transactions/models.py](transactions/models.py): Requisition status choices and workflow integration
- [workflow/models.py](workflow/models.py): ApprovalThreshold for escalation rules
- [pettycash_system/managers.py](pettycash_system/managers.py): CompanyQuerySet for multi-tenancy
- [build.sh](build.sh): Deployment script with DB checks and seeding
- [WORKFLOW_ROLES_CLARIFICATION.md](WORKFLOW_ROLES_CLARIFICATION.md): Approval vs validation separation

## Common Pitfalls
- Don't query without company context; use managers that inherit from CompanyManager.
- Treasury validates/pays after approvals complete; don't confuse with approvers.
- Test with `local_test_settings.py` for isolated settings testing.
- Use `python manage.py seed_settings` after migrations to populate dynamic settings.</content>
<parameter name="filePath">/workspaces/pettycash_system/.github/copilot-instructions.md