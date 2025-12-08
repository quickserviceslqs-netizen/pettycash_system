"""
Find and fix hardcoded settings across the system
"""

import os
import re
from pathlib import Path

def find_hardcoded_currency():
    """Find hardcoded currency symbols in templates"""
    issues = []
    
    # Directories to check
    dirs_to_check = [
        'templates/workflow',
        'templates/treasury',
        'templates/system_maintenance',
        'templates/transactions',
        'templates/accounts',
    ]
    
    for dir_path in dirs_to_check:
        full_path = Path(r'C:\Users\ADMIN\pettycash_system') / dir_path
        if not full_path.exists():
            continue
            
        for html_file in full_path.glob('**/*.html'):
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find ${{ or KES {{
            dollar_matches = re.findall(r'\$\{\{[^}]+\}\}', content)
            kes_matches = re.findall(r'KES\s+\{\{[^}]+\}\}', content)
            
            if dollar_matches or kes_matches:
                issues.append({
                    'file': str(html_file.relative_to(r'C:\Users\ADMIN\pettycash_system')),
                    'type': 'currency',
                    'dollar_count': len(dollar_matches),
                    'kes_count': len(kes_matches),
                    'examples': dollar_matches[:3] + kes_matches[:3]
                })
    
    return issues

def find_hardcoded_timeouts():
    """Find hardcoded timeout values in Python files"""
    issues = []
    
    # Files to check
    files_to_check = [
        'treasury/services/alert_service.py',
        'system_maintenance/models.py',
        'treasury/services/report_service.py',
    ]
    
    for file_path in files_to_check:
        full_path = Path(r'C:\Users\ADMIN\pettycash_system') / file_path
        if not full_path.exists():
            continue
            
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Find hardcoded timedeltas
            if 'timedelta(' in line and any(x in line for x in ['minutes=', 'hours=', 'days=']):
                # Skip if it's a parameter default or comment
                if 'def ' in line or '#' in line.split('timedelta')[0]:
                    continue
                    
                issues.append({
                    'file': file_path,
                    'line': i,
                    'code': line.strip(),
                    'type': 'timeout'
                })
    
    return issues

def find_hardcoded_limits():
    """Find hardcoded numeric limits"""
    issues = []
    
    # Common patterns
    patterns = [
        (r'page_size.*=.*\d+', 'pagination_limit'),
        (r'limit.*=.*\d+', 'query_limit'),
        (r'max.*=.*\d+', 'max_value'),
    ]
    
    return issues

def print_report():
    """Print comprehensive report"""
    print("\n" + "="*80)
    print("  HARDCODED SETTINGS AUDIT")
    print("="*80 + "\n")
    
    # Currency issues
    currency_issues = find_hardcoded_currency()
    if currency_issues:
        print("1. HARDCODED CURRENCY SYMBOLS")
        print("-" * 80)
        for issue in currency_issues:
            print(f"\n📄 {issue['file']}")
            print(f"   $ symbols: {issue['dollar_count']}, KES symbols: {issue['kes_count']}")
            if issue['examples']:
                print(f"   Examples: {issue['examples'][0]}")
        print(f"\nTotal files: {len(currency_issues)}")
    else:
        print("✅ 1. Currency Symbols - No issues found\n")
    
    # Timeout issues
    timeout_issues = find_hardcoded_timeouts()
    if timeout_issues:
        print("\n2. HARDCODED TIMEOUTS/DURATIONS")
        print("-" * 80)
        for issue in timeout_issues:
            print(f"\n📄 {issue['file']}:{issue['line']}")
            print(f"   {issue['code']}")
        print(f"\nTotal instances: {len(timeout_issues)}")
    else:
        print("✅ 2. Timeouts/Durations - No issues found\n")
    
    print("\n" + "="*80)
    print("  RECOMMENDATIONS")
    print("="*80 + "\n")
    
    if currency_issues:
        print("Currency Symbols:")
        print("  • Create currency_filters templatetag for workflow/treasury/system_maintenance")
        print("  • Replace ${{ amount|floatformat:2 }} with {{ amount|currency }}")
        print("  • Replace KES {{ amount }} with {{ amount|currency }}")
        print()
    
    if timeout_issues:
        print("Timeouts/Durations:")
        print("  • Create system settings for timeout values")
        print("  • Use get_setting('SETTING_NAME', default) instead of hardcoded values")
        print()
    
    total_issues = len(currency_issues) + len(timeout_issues)
    if total_issues == 0:
        print("🎉 NO HARDCODED SETTINGS FOUND! System is clean.")
    else:
        print(f"⚠️  Found {total_issues} areas with hardcoded settings")

if __name__ == '__main__':
    print_report()
