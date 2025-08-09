# setup-missing-deps.ps1
# Ensures all PRD-required deps are installed with Poetry (ASCII-only, safe on Windows PowerShell)

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
  Write-Host "ERROR: Poetry is not installed. Install Poetry and re-run."
  Pop-Location
  exit 1
}

# 1) Ensure pyproject.toml exists
if (-not (Test-Path "$ProjectRoot\pyproject.toml")) {
  Exec-Or-Die "poetry" @("init","-n","--name","ok-mvp","--description","Wizards Toolkit MVP CLI","--license","MIT") "poetry init failed."
  Write-Host "Created pyproject.toml"
}

# 2) Ensure Python constraint is compatible with youtube-transcript-api (<3.14)
#    Replace any existing 'python = "...' with '>=3.11,<3.14'
$py = "$ProjectRoot\pyproject.toml"
if (Test-Path $py) {
  $content = Get-Content $py -Raw
  $new = $content -replace 'python\s*=\s*".*"', 'python = ">=3.11,<3.14"'
  if ($new -ne $content) {
    $new | Set-Content $py
    Write-Host "Updated Python version constraint to >=3.11,<3.14"
    $pyChanged = $true
  }
}

# 3) Use a compatible interpreter (best effort)
#    You have 3.13 available already; if not, this will error which is fine.
& poetry env use 3.13 | Out-Null

# 4) If pyproject changed significantly, refresh lock
if ($pyChanged) {
  Exec-Or-Die "poetry" @("lock","--no-update") "poetry lock failed."
}

# 5) Install core runtime deps (idempotent; safe if already installed)
#    FR/NFR packages per PRD + yt-dlp for search
$runtime = @(
  "yt-dlp",
  "youtube-transcript-api",
  "arxiv",
  "pypdf",
  "openai",
  "python-dotenv",
  "argparse"
)
Exec-Or-Die "poetry" @("add") + $runtime "poetry add (runtime) failed."

# 6) Dev deps
$dev = @("black","ruff")
Exec-Or-Die "poetry" @("add","--dev") + $dev "poetry add (dev) failed."

# 7) Install everything according to lockfile
Exec-Or-Die "poetry" @("install") "poetry install failed."

# 8) Export requirements.txt if plugin is available; otherwise attempt to add plugin
$exportOk = $false
& poetry export -f requirements.txt -o requirements.txt --without-hashes
if ($LASTEXITCODE -eq 0) { $exportOk = $true }
if (-not $exportOk) {
  Write-Host "poetry export unavailable. Installing poetry-plugin-export..."
  & poetry self add poetry-plugin-export
  if ($LASTEXITCODE -eq 0) {
    & poetry export -f requirements.txt -o requirements.txt --without-hashes
    if ($LASTEXITCODE -eq 0) { $exportOk = $true }
  }
}
if (-not $exportOk) {
  Write-Host "Falling back to minimal requirements.txt"
  @(
    "yt-dlp",
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

