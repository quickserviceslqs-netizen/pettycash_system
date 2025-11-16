<#
Interactive wrapper to run backup, add payment_id, apply migrations and run UAT on staging.
Usage: Run from project root in PowerShell. This script prompts for values and confirms actions.
#>

param(
    [string]$DbHost = 'localhost',
    [string]$DbPort = '5432',
    [string]$DbName = 'pettycash',
    [string]$DbUser = 'postgres',
    [string]$SettingsModule = 'staging_settings'
)

function Prompt-Confirm($msg){
    $r = Read-Host "$msg (yes/no)"
    return $r -eq 'yes'
}

Write-Host "STAGING MIGRATION WRAPPER"
Write-Host "This will:"
Write-Host " 1) Prompt for DB password and create a backup using pg_dump"
Write-Host " 2) Run scripts/add_payment_id.ps1 to add/seed payment_id"
Write-Host " 3) Run Django migrations and UAT automation"

if (-not (Prompt-Confirm "Do you have a verified backup destination and are you ready to proceed?")){
    Write-Host "Aborting. Please take a backup and re-run when ready."
    exit 1
}

$securePwd = Read-Host -AsSecureString "Enter DB password"
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd)
$plainPwd = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
$env:PGPASSWORD = $plainPwd

$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$backupFile = "backups\staging_backup_$timestamp.dump"
New-Item -ItemType Directory -Path backups -ErrorAction SilentlyContinue | Out-Null

$pgDumpCmd = "pg_dump -h $DbHost -p $DbPort -U $DbUser -F c -b -v -f $backupFile $DbName"
Write-Host "Running backup: $pgDumpCmd"
& pg_dump -h $DbHost -p $DbPort -U $DbUser -F c -b -v -f $backupFile $DbName
if ($LASTEXITCODE -ne 0){ Write-Error "Backup failed with exit code $LASTEXITCODE"; exit $LASTEXITCODE }
Write-Host "Backup complete: $backupFile"

if (-not (Prompt-Confirm "Proceed to run scripts/add_payment_id.ps1 to add/seed payment_id?")){
    Write-Host "Skipping schema helper. Exiting."
    exit 0
}

# Run the add_payment_id helper
Write-Host "Running add_payment_id.ps1"
& .\scripts\add_payment_id.ps1 -DbHost $DbHost -DbPort $DbPort -DbName $DbName -DbUser $DbUser
if ($LASTEXITCODE -ne 0){ Write-Error "add_payment_id.ps1 failed"; exit $LASTEXITCODE }

Write-Host "Verifying payment_id population (counts)"
& psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -c "SELECT COUNT(*) FROM treasury_payment WHERE payment_id IS NULL;"

if (-not (Prompt-Confirm "Proceed to run Django migrations now?")){
    Write-Host "User aborted before migrations. Exiting."
    exit 0
}

Write-Host "Running Django migrations using settings module: $SettingsModule"
$python = "python"
& $python .\manage.py migrate --settings=$SettingsModule
if ($LASTEXITCODE -ne 0){ Write-Error "Django migrate failed"; exit $LASTEXITCODE }

Write-Host "Migrations applied. Running UAT automation (E2E test)"
& $python .\scripts\run_uat.py --settings=$SettingsModule

Write-Host "UAT finished. Inspect reports/uat_report.txt"
Write-Host "Done."
