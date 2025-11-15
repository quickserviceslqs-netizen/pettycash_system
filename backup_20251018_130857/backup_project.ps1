# ===============================================
# Full Backup Script for pettycash_system Project
# ===============================================

# Variables
$projectRoot = "C:\Users\ADMIN\pettycash_system"
$backupRoot = "C:\Backup"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFolder = "$backupRoot\backup_$timestamp"
$zipFile = "$backupRoot\pettycash_backup_$timestamp.zip"

# Database details
$dbName = "pettycash_db"
$dbUser = "chelotian"
$backupDbFile = "$backupFolder\$dbName.backup"

# Create backup folder
if (!(Test-Path $backupFolder)) {
    New-Item -ItemType Directory -Path $backupFolder | Out-Null
}

Write-Host "Starting full backup at $(Get-Date)..."
Write-Host "Backing up Django project files..."

# Copy full project directory, excluding unnecessary folders
$excludePatterns = @("env", "venv", "__pycache__", ".git", "*.pyc", "*.log", "node_modules")
Get-ChildItem -Path $projectRoot -Recurse | Where-Object {
    $excludePatterns -notcontains $_.Name
} | Copy-Item -Destination $backupFolder -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Project files backed up successfully."

# Backup PostgreSQL database
Write-Host "Backing up PostgreSQL database..."
pg_dump -U $dbUser -h localhost -F c -b -v -f $backupDbFile $dbName
Write-Host "Database backup completed: $backupDbFile"

# Compress the backup folder into a zip file
Write-Host "Compressing backup folder..."
Compress-Archive -Path $backupFolder -DestinationPath $zipFile -Force
Write-Host "Backup compressed successfully: $zipFile"

# Optionally remove the uncompressed folder after zipping
Remove-Item -Path $backupFolder -Recurse -Force

# Cleanup old backups (older than 7 days)
Write-Host "Cleaning up old backups..."
Get-ChildItem $backupRoot -Filter "pettycash_backup_*.zip" | 
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | 
    Remove-Item -Force

Write-Host "Old backups cleaned up (older than 7 days)."
Write-Host "Full backup completed successfully at $(Get-Date)"
Write-Host "Backup saved to: $zipFile"
