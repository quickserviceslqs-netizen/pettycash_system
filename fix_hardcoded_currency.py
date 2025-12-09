"""
Fix hardcoded currency in workflow, treasury, transactions templates
"""

import os
import re
from pathlib import Path


def update_template(filepath):
    """Update a template file to use currency filters"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    changes = []

    # Add currency_filters load if not present
    if "{% load currency_filters %}" not in content:
        # Add after {% load static %} if present
        if "{% load static %}" in content:
            content = content.replace(
                "{% load static %}", "{% load static %}\n{% load currency_filters %}"
            )
            changes.append("Added {% load currency_filters %}")
        # Or after extends if no static load
        elif "{% extends" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "{% extends" in line:
                    lines.insert(i + 1, "{% load currency_filters %}")
                    break
            content = "\n".join(lines)
            changes.append("Added {% load currency_filters %}")

    # Replace ${{ variable|floatformat:2 }} with {{ variable|currency }}
    pattern1 = r"\$\{\{\s*([^}|]+)\|floatformat:2\s*\}\}"
    if re.search(pattern1, content):
        content = re.sub(pattern1, r"{{ \1|currency }}", content)
        changes.append("Replaced ${{ var|floatformat:2 }} patterns")

    # Replace KES {{ variable|floatformat:2 }} with {{ variable|currency }}
    pattern2 = r"KES\s*\{\{\s*([^}|]+)\|floatformat:2\s*\}\}"
    if re.search(pattern2, content):
        content = re.sub(pattern2, r"{{ \1|currency }}", content)
        changes.append("Replaced KES {{ var|floatformat:2 }} patterns")

    # Replace KES {{variable}} patterns (no floatformat)
    pattern3 = r"KES\s*\{\{([^}]+)\}\}"
    if re.search(pattern3, content):
        content = re.sub(pattern3, r"{{ \1|currency }}", content)
        changes.append("Replaced KES {{var}} patterns")

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True, changes

    return False, []


def main():
    print("=" * 80)
    print("  FIXING HARDCODED CURRENCY IN TEMPLATES")
    print("=" * 80)
    print()

    # Files to update (from audit)
    files_to_update = [
        "templates/workflow/dashboard.html",
        "templates/workflow/manage_thresholds.html",
        "templates/treasury/approve_variance.html",
        "templates/treasury/create_payment.html",
        "templates/treasury/create_variance.html",
        "templates/treasury/execute_payment.html",
        "templates/treasury/manage_funds.html",
        "templates/treasury/manage_payments.html",
        "templates/treasury/manage_variances.html",
        "templates/treasury/view_ledger.html",
        "templates/transactions/approve_requisition.html",
        "templates/transactions/manage_requisitions.html",
        "templates/transactions/reject_requisition.html",
        "templates/transactions/requisition_detail.html",
        "templates/transactions/view_requisition.html",
    ]

    updated_count = 0
    skipped_count = 0

    for file_path in files_to_update:
        full_path = Path(r"C:\Users\ADMIN\pettycash_system") / file_path

        if not full_path.exists():
            print(f"⚠️  SKIP: {file_path} (not found)")
            skipped_count += 1
            continue

        updated, changes = update_template(full_path)

        if updated:
            print(f"✅ UPDATED: {file_path}")
            for change in changes:
                print(f"    - {change}")
            updated_count += 1
        else:
            print(f"   SKIP: {file_path} (no changes needed)")
            skipped_count += 1

    print()
    print("=" * 80)
    print(f"  Summary: {updated_count} updated, {skipped_count} skipped")
    print("=" * 80)


if __name__ == "__main__":
    main()
