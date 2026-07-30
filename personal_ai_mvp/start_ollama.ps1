param(
    [string]$EnvFile = ".env"
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$managerPath = Join-Path $projectRoot "manage_runtime.ps1"

& $managerPath -Action start -Components ollama -EnvFile $EnvFile
