# save.ps1

function Is-GitRepo {
    return Test-Path .git
}

if (-not (Is-GitRepo)) {
    Write-Host "Not a Git repository. Please run this in your project folder." -ForegroundColor Red
    exit 1
}

# Check for any changes
$changes = git status --porcelain

if ([string]::IsNullOrWhiteSpace($changes)) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
    exit 0
}

# Prompt for commit message
$commitMessage = Read-Host "Enter a commit description"

# Append current timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMessageWithTimestamp = "$commitMessage [$timestamp]"

Write-Host "`nStaging changes..."
& git add -A

Write-Host "Committing changes..."
& git commit -m "$commitMessageWithTimestamp"

Write-Host "Pushing to main branch..."
& git push origin main

# Create log folder if it doesn't exist
$logDir = ".\git-log"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

# Log the commit
$logFileName = "$logDir\commit-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
$logContent = @"
Commit: $commitMessageWithTimestamp
Time:   $timestamp
Branch: main
Repo:   $(git config --get remote.origin.url)
"@
$logContent | Out-File $logFileName -Encoding UTF8

Write-Host "`nSave complete! Commit logged to $logFileName" -ForegroundColor Green
