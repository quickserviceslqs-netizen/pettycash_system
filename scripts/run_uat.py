"""
Run UAT automation: execute the integration test suite and save output to `reports/uat_report.txt`.
Run from project root: `python scripts/run_uat.py --settings=test_settings`
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPORT = Path('reports')
REPORT.mkdir(exist_ok=True)
OUTFILE = REPORT / 'uat_report.txt'

parser = argparse.ArgumentParser()
parser.add_argument('--settings', default='test_settings', help='Django settings module to use')
args = parser.parse_args()

cmd = [sys.executable, 'manage.py', 'test', 'tests.integration.test_e2e', f'--settings={args.settings}']
print('Running UAT tests:', ' '.join(cmd))
with OUTFILE.open('w', encoding='utf-8') as f:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    f.write(proc.stdout.decode('utf-8', errors='replace'))

print('UAT finished. Report written to', OUTFILE)
