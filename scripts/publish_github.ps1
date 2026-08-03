$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& (Join-Path $PSScriptRoot "initialize_repo.ps1")

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required. Install it, authenticate with 'gh auth login', and rerun this script."
}

$repoName = "PStar1980/SkyDataStudio"
$remoteNames = git remote

if ($remoteNames -contains "origin") {
    Write-Host "Remote origin already exists; skipping repository creation." -ForegroundColor Yellow
} else {
    Write-Host "Creating public GitHub repository $repoName..." -ForegroundColor Cyan
    git switch main
    gh repo create $repoName --public --source . --remote origin --push
}

Write-Host "Publishing dev branch..." -ForegroundColor Cyan
git switch dev
git push -u origin dev

Write-Host "SkyDataStudio is published with main and dev branches." -ForegroundColor Green
