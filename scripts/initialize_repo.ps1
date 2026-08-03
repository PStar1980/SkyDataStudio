$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
    Write-Host "Initializing SkyDataStudio local Git repository..." -ForegroundColor Cyan
    git init -b main
    git add .
    git commit -m "Initialize SkyData Studio foundation"
}

$branches = git branch --format="%(refname:short)"
if ($branches -notcontains "main") {
    throw "Expected a main branch but none was found."
}

if ($branches -notcontains "dev") {
    git branch dev main
}

git switch dev
Write-Host "Local repository is ready on the dev branch." -ForegroundColor Green
