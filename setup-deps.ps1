# setup-deps.ps1
# Robust, ASCII-only dependency setup for ok-mvp

param(
  [string]$ProjectRoot = (Get-Location).Path
)

function Exec-Or-Die {
  param([string]$Cmd, [string[]]$Args, [string]$FailMsg)
  & $Cmd @Args
  if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: $FailMsg"
    exit 1
  }
}

Push-Location $ProjectRoot

# 0) Check Poetry
$poetry = Get-Command poetry -ErrorAction SilentlyContinue
if (-not $poetry) {
  Write-Host "ERROR: Poetry is not installed. Install Poetry and re-run this script."
  Pop-Location
  exit 1
}

# 1) Ensure pyproject.toml exists (no --readme flag to avoid version differences)
if (-not (Test-Path "$ProjectRoot\pyproject.toml")) {
  Exec-Or-Die "poetry" @("init","-n","--name","ok-mvp","--description","Wizards Toolkit MVP CLI","--license","MIT") "poetry init failed."
  Write-Host "Created pyproject.toml"
}

# 2) Add runtime deps (idempotent)
Exec-Or-Die "poetry" @("add","youtube-transcript-api","arxiv","pypdf","openai","python-dotenv","argparse") "poetry add (runtime) failed."
Write-Host "Runtime dependencies added."

# 3) Add dev deps (idempotent)
Exec-Or-Die "poetry" @("add","--dev","black","ruff") "poetry add (dev) failed."
Write-Host "Dev dependencies added."

# 4) Try to export requirements.txt
$exportOk = $false
& poetry export -f requirements.txt -o requirements.txt --without-hashes
if ($LASTEXITCODE -eq 0) { $exportOk = $true }

# 4a) If export missing, install plugin and retry
if (-not $exportOk) {
  Write-Host "poetry export not available. Installing poetry-plugin-export..."
  & poetry self add poetry-plugin-export
  if ($LASTEXITCODE -eq 0) {
    & poetry export -f requirements.txt -o requirements.txt --without-hashes
    if ($LASTEXITCODE -eq 0) { $exportOk = $true }
  }
}

# 4b) Last-resort fallback: write a minimal requirements.txt that satisfies the PRD
if (-not $exportOk) {
  Write-Host "Falling back to minimal requirements.txt"
  @(
    "youtube-transcript-api",
    "arxiv",
    "pypdf",
    "openai",
    "python-dotenv",
    "argparse"
  ) | Set-Content -Encoding ASCII -Path "$ProjectRoot\requirements.txt"
}

Write-Host "Dependencies ready."
Pop-Location
