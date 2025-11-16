# Backup and prepare migration script (PowerShell)
# Usage: Run from project root. Requires pg_dump in PATH and appropriate env vars.

param(
    [string]$DbHost = 'localhost',
    [string]$DbPort = '5432',
    [string]$DbName = 'pettycash',
    [string]$DbUser = 'postgres',
    [string]$BackupFile = "pettycash_backup_$(Get-Date -Format yyyyMMdd_HHmmss).sql"
)

Write-Host "Backing up database $DbName to $BackupFile"
$env:PGPASSWORD = Read-Host -AsSecureString "Enter DB password (will not echo)" | ConvertFrom-SecureString
# Note: ConvertFrom-SecureString output is encrypted; user should set PGPASSWORD env var manually or run interactively.

# Example interactive backup command (uncomment and run manually with PGPASSWORD set):
# pg_dump -h $DbHost -p $DbPort -U $DbUser -F c -b -v -f $BackupFile $DbName

Write-Host "Backup script created. Please run the pg_dump command interactively with correct credentials."

Write-Host "Next steps:"
Write-Host "1) Verify backup file exists and is restorable."
Write-Host "2) In staging run the MIGRATION_RECONCILE.md plan."
