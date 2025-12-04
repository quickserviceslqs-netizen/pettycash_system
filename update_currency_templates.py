"""
Update all report templates to use currency_filters templatetag
"""

import os
import re

# Reports template directory
templates_dir = r'C:\Users\ADMIN\pettycash_system\templates\reports'

# Files to update
files_to_update = [
    'treasury_report.html',
    'budget_vs_actuals.html',
    'category_spending.html',
    'payment_method_analysis.html',
    'regional_comparison.html',
    'rejection_analysis.html',
    'average_metrics.html',
    'dashboard.html',
    'transaction_report.html',
    'approval_report.html',
    'user_activity_report.html',
    'stuck_approvals.html',
    'threshold_overrides.html',
    'treasury_fund_detail.html',
]

def update_template(filepath):
    """Update a template file to use currency filters"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Add currency_filters load if not present
    if '{% load currency_filters %}' not in content:
        # Add after {% load static %} if present
        if '{% load static %}' in content:
            content = content.replace(
                '{% load static %}',
                '{% load static %}\n{% load currency_filters %}'
            )
            changes.append('Added {% load currency_filters %}')
        # Or after extends if no static load
        elif '{% extends' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '{% extends' in line:
                    lines.insert(i + 1, '{% load currency_filters %}')
                    break
            content = '\n'.join(lines)
            changes.append('Added {% load currency_filters %}')
    
    # Replace ${{ variable|floatformat:2 }} with {{ variable|currency }}
    pattern1 = r'\$\{\{\s*([^}|]+)\|floatformat:2\s*\}\}'
    content = re.sub(pattern1, r'{{ \1|currency }}', content)
    if re.search(pattern1, original_content):
        changes.append('Replaced ${{ var|floatformat:2 }} patterns')
    
    # Replace KES {{ variable|floatformat:2 }} with {{ variable|currency }}
    pattern2 = r'KES\s*\{\{\s*([^}|]+)\|floatformat:2\s*\}\}'
    content = re.sub(pattern2, r'{{ \1|currency }}', content)
    if re.search(pattern2, original_content):
        changes.append('Replaced KES {{ var|floatformat:2 }} patterns')
    
    # Replace {{ variable|floatformat:2 }} in money contexts (look for td/div with text-end or amount keywords)
    # This is more selective to avoid breaking percentages
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes
    
    return False, []

def main():
    print("="*80)
    print("  UPDATING REPORT TEMPLATES TO USE CURRENCY SETTINGS")
    print("="*80)
    print()
    
    updated_count = 0
    skipped_count = 0
    
    for filename in files_to_update:
        filepath = os.path.join(templates_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  SKIP: {filename} (not found)")
            skipped_count += 1
            continue
        
        updated, changes = update_template(filepath)
        
        if updated:
            print(f"✅ UPDATED: {filename}")
            for change in changes:
                print(f"    - {change}")
            updated_count += 1
        else:
            print(f"   SKIP: {filename} (no changes needed)")
            skipped_count += 1
    
    print()
    print("="*80)
    print(f"  Summary: {updated_count} updated, {skipped_count} skipped")
    print("="*80)
    print()
    print("Currency symbols will now use system settings:")
    print("  - CURRENCY_SYMBOL (e.g., 'KSh', '$', '€')")
    print("  - CURRENCY_DECIMAL_PLACES")
    print("  - CURRENCY_THOUSAND_SEPARATOR")
    print("  - CURRENCY_DECIMAL_SEPARATOR")
    print("  - CURRENCY_SYMBOL_POSITION")

if __name__ == '__main__':
    main()
