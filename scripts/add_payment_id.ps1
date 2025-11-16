# PowerShell helper to run the `add_payment_id.sql` script against Postgres
# Usage: Set $DbHost, $DbName, $DbUser, then run. This script will call psql and requires psql in PATH.

param(
    [string]$DbHost = 'localhost',
    [string]$DbPort = '5432',
    [string]$DbName = 'pettycash',
    [string]$DbUser = 'postgres',
    [string]$SqlFile = "scripts\\add_payment_id.sql"
)

if (-not (Test-Path $SqlFile)) {
    Write-Error "SQL file not found: $SqlFile"
    exit 1
}

# Ask for password securely
$securePwd = Read-Host -AsSecureString "Enter DB password"
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePwd)
$plainPwd = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
$env:PGPASSWORD = $plainPwd

$cmd = "psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $SqlFile"
Write-Host "Running: $cmd"
& psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $SqlFile

if ($LASTEXITCODE -ne 0) {
    Write-Error "psql returned exit code $LASTEXITCODE. Check output above."
    exit $LASTEXITCODE
}

Write-Host "Done. Verify the `treasury_payment.payment_id` column and contents before running Django migrations."