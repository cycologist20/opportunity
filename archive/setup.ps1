# setup-ok-mvp.ps1
# Creates folder structure and empty files for Wizard's Toolkit MVP

$projectRoot = "C:\Users\jyoun\Projects\ok-mvp"

# Create root folder
New-Item -Path $projectRoot -ItemType Directory -Force | Out-Null

# Create subfolders
$folders = @(
    "$projectRoot\ok_mvp",
    "$projectRoot\output"
)

foreach ($folder in $folders) {
    New-Item -Path $folder -ItemType Directory -Force | Out-Null
}

# Create empty files
$files = @(
    "$projectRoot\README.md",
    "$projectRoot\.env.example",
    "$projectRoot\.gitignore",
    "$projectRoot\ok_mvp\__init__.py",
    "$projectRoot\ok_mvp\main.py",
    "$projectRoot\ok_mvp\config.py",
    "$projectRoot\ok_mvp\youtube_module.py",
    "$projectRoot\ok_mvp\arxiv_module.py",
    "$projectRoot\ok_mvp\llm_utils.py",
    "$projectRoot\ok_mvp\logger.py"
)

foreach ($file in $files) {
    New-Item -Path $file -ItemType File -Force | Out-Null
}

Write-Host "✅ Project structure created at $projectRoot"
