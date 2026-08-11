param(
    [ValidateSet("debug", "build", "run", "test", "clean")]
    [string]$Command = "build",
    [string]$Select = ""
)

$composeFile = Join-Path $PSScriptRoot "..\infra\docker-compose.yml"
$dockerArgs = @("compose", "-f", $composeFile, "run", "--rm", "dbt", $Command, "--profiles-dir", ".")

if ($Select) {
    $dockerArgs += @("--select", $Select)
}

Write-Host "SkyData Studio dbt: $Command $Select" -ForegroundColor Cyan
& docker @dockerArgs
exit $LASTEXITCODE
