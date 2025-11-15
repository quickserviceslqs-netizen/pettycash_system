# Reset script for pettycash_system project

# Database connection info
$dbName = "pettycash_db"
$dbUser = "chelotian"
$dbPassword = "35315619@Ian"

# Paths
$projectRoot = "C:\Users\ADMIN\pettycash_system"
$pgBinPath = "C:\Program Files\PostgreSQL\18\bin"

# Stop Django server if running
Write-Host "Stopping any running Django development servers..."
Get-Process | Where-Object { $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Drop and recreate database
Write-Host "Resetting PostgreSQL database..."
& "$pgBinPath\psql.exe" -U postgres -c "DROP DATABASE IF EXISTS $dbName;"
& "$pgBinPath\psql.exe" -U postgres -c "CREATE DATABASE $dbName OWNER $dbUser;"
& "$pgBinPath\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;"

# Remove all migration files except __init__.py
Write-Host "Cleaning up migrations..."
$apps = "accounts","organization","transactions","treasury","workflow","reports"
foreach ($app in $apps) {
    $migPath = "$projectRoot\$app\migrations"
    if (Test-Path $migPath) {
        Get-ChildItem -Path $migPath -Include *.py,*.pyc -Exclude __init__.py -Recurse | Remove-Item -Force
        Write-Host "Cleaned migrations for $app"
    }
}

# Delete SQLite db if it exists (for safety)
$sqliteFile = "$projectRoot\db.sqlite3"
if (Test-Path $sqliteFile) {
    Remove-Item $sqliteFile -Force
}

# Run Django migrations fresh
Write-Host "Running fresh Django migrations..."
Set-Location $projectRoot
& "$projectRoot\venv\Scripts\python.exe" manage.py makemigrations
& "$projectRoot\venv\Scripts\python.exe" manage.py migrate

Write-Host "Project reset completed successfully."
