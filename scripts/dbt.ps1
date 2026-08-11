param(
    [ValidateSet("debug", "build", "run", "test", "clean")]
    [string]$Command = "build",
    [string]$Select = ""
)

$composeFile = Join-Path $PSScriptRoot "..\infra\docker-compose.yml"
$args = @("compose", "-f", $composeFile, "run", "--rm", "dbt", $Command, "--profiles-dir", ".")

if ($Select) {
    $args += @("--select", $Select)
}

Write-Host "SkyData Studio dbt: $Command $Select" -ForegroundColor Cyan
& docker @args
exit $LASTEXITCODE
