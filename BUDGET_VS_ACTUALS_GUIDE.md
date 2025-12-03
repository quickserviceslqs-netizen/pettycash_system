# Budget vs Actuals: Admin & Seeding Guide

This guide covers how to manage budget allocations for the Budget vs Actuals report using Django Admin and the `seed_budgets` management command.

## Prerequisites
- Apply migrations after pulling latest changes:
  - `python manage.py migrate reports`
- Ensure you can access Django Admin and have permissions to manage `Budget allocations`.

## Admin: Import/Export CSV
- Navigate to: `Admin → Reports → Budget allocations`.
- Export selected rows:
  1. Select items
  2. Use Actions → "Export selected to CSV"
- Import CSV:
  - Open: `/admin/reports/budgetallocation/import-csv/`
  - Upload a CSV with headers:
    - `company_id,branch_id,department_id,cost_center_id,year,month,amount`
    - Required: `company_id`, `year`, `amount`
    - Optional: `branch_id`, `department_id`, `cost_center_id`, `month` (leave blank for annual)
  - Rows are upserted on unique key `(company, branch, department, cost_center, year, month)`; `amount` is updated on match.

### Sample CSV
```
company_id,branch_id,department_id,cost_center_id,year,month,amount
1,,, ,2025,,1200000.00
1,10,,,2025,1,100000.00
1,10,,,2025,2,100000.00
1,,20,,2025,1,50000.00
1,,,30,2025,3,25000.00
```

## Management Command: `seed_budgets`
Use this to bulk-generate or import budgets.

### Generate Defaults (no CSV)
- Scope options: `company`, `branch`, `department`, `cost_center`
- `--monthly` creates 12 monthly rows; omit to create a single annual row
- `--overwrite` updates amounts if the row exists

Examples (Windows PowerShell):
```powershell
# Company-wide annual budget
python manage.py seed_budgets --company-id 1 --year 2025 --scope company --amount 1200000

# Per cost center monthly budgets, overwrite if exists
python manage.py seed_budgets --company-id 1 --year 2025 --scope cost_center --amount 100000 --monthly --overwrite

# Per department annual budgets
python manage.py seed_budgets --company-id 1 --year 2025 --scope department --amount 600000
```

### Import from CSV
If you already have a CSV (same headers as Admin import):
```powershell
python manage.py seed_budgets --csv "C:\\path\\to\\budgets.csv" --company-id 1 --year 2025 --overwrite
```
- `company_id` per row can be omitted if `--company-id` is provided.

## Notes & Constraints
- Uniqueness: `(company, branch, department, cost_center, year, month)` must be unique.
- Annual vs monthly: leave `month` blank for annual allocations.
- Hierarchy filters in generation:
  - Branch: filtered by `region__company=<company>`
  - Department: `branch__region__company=<company>`
  - Cost center: `department__branch__region__company=<company>`
- Budget vs Actuals report supports grouping by `branch`, `department`, or `cost center` with monthly variance and CSV/XLSX export.

## Troubleshooting
- Import failures: verify header names and numeric formats; ensure referenced IDs exist.
- Permission denied: confirm your admin user has access to `Budget allocations`.
- No data in report: ensure allocations exist for the selected year and grouping.
