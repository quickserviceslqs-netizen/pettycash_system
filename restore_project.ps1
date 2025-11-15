# ===============================================
# Full Restore Script for pettycash_system Project
# ===============================================

# Variables
$projectRoot = "C:\Users\ADMIN\pettycash_system"
$backupRoot = "C:\Backup"
$dbName = "pettycash_db"
$dbUser = "chelotian"

# --------------------------------------------
# Step 1: Choose which backup ZIP to restore
# --------------------------------------------
Write-Host "Looking for latest backup ZIP file in $backupRoot..."

$latestBackup = Get-ChildItem -Path $backupRoot -Filter "pettycash_backup_*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestBackup) {
    Write-Host "❌ No backup ZIP file found in $backupRoot. Aborting restore."
    exit
}

Write-Host "Found latest backup: $($latestBackup.Name)"
$extractFolder = "$backupRoot\restore_temp"

# --------------------------------------------
# Step 2: Extract the backup archive
# --------------------------------------------
if (Test-Path $extractFolder) {
    Remove-Item -Path $extractFolder -Recurse -Force
}
New-Item -ItemType Directory -Path $extractFolder | Out-Null

Write-Host "Extracting $($latestBackup.Name) ..."
Expand-Archive -Path $latestBackup.FullName -DestinationPath $extractFolder -Force
Write-Host "✅ Backup extracted successfully to $extractFolder"

# --------------------------------------------
# Step 3: Restore project files
# --------------------------------------------
Write-Host "Restoring Django project files to $projectRoot ..."

# Ensure destination exists
if (!(Test-Path $projectRoot)) {
    New-Item -ItemType Directory -Path $projectRoot | Out-Null
}

# Copy extracted files into the project directory, overwriting existing files
Copy-Item -Path "$extractFolder\*" -Destination $projectRoot -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "✅ Project files restored successfully."

# --------------------------------------------
# Step 4: Restore PostgreSQL database
# --------------------------------------------
$backupDbFile = Get-ChildItem -Path $extractFolder -Filter "*.backup" -Recurse | Select-Object -First 1

if ($backupDbFile) {
    Write-Host "Restoring PostgreSQL database from: $($backupDbFile.FullName)"
    # Drop and recreate database (optional safety confirmation)
    $confirm = Read-Host "⚠️ Do you want to overwrite the existing database '$dbName'? (Y/N)"
    if ($confirm -eq "Y") {
        Write-Host "Dropping and recreating database..."
        psql -U $dbUser -h localhost -c "DROP DATABASE IF EXISTS $dbName;"
        psql -U $dbUser -h localhost -c "CREATE DATABASE $dbName OWNER $dbUser;"
        Write-Host "Restoring database content..."
        pg_restore -U $dbUser -h localhost -d $dbName -v $($backupDbFile.FullName)
        Write-Host "✅ Database restored successfully."
    }
    else {
        Write-Host "⚠️ Database restore skipped by user."
    }
} else {
    Write-Host "❌ No .backup file found inside the archive. Database restore skipped."
}

# --------------------------------------------
# Step 5: Cleanup temporary files
# --------------------------------------------
Write-Host "Cleaning up temporary extraction folder..."
Remove-Item -Path $extractFolder -Recurse -Force
Write-Host "✅ Cleanup completed."

# --------------------------------------------
# Step 6: Summary
# --------------------------------------------
Write-Host "==============================================="
Write-Host "✅ Full restore completed successfully!"
Write-Host "📁 Project restored to: $projectRoot"
Write-Host "🧠 Database restored: $dbName (if confirmed)"
Write-Host "🕒 Completed at: $(Get-Date)"
Write-Host "==============================================="
