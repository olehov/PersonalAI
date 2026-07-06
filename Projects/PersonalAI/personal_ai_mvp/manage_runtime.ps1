param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status",

    [ValidateSet("all", "ollama", "backend", "frontend")]
    [string[]]$Components = @("all"),

    [string]$EnvFile = ".env",
    [string]$BindHost = "127.0.0.1",
    [int]$BackendPort = 8765,
    [int]$FrontendPort = 5173,
    [string]$VaultRoot = ""
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectSrc = Join-Path $projectRoot "src"
$runtimeDir = Join-Path $projectRoot ".runtime"

if (-not $VaultRoot) {
    $VaultRoot = (Resolve-Path (Join-Path $projectRoot "..\..\..")).Path
}

function Load-EnvFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Environment file not found: $Path"
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        if ($line.StartsWith("export ")) {
            $line = $line.Substring(7).Trim()
        }
        $parts = $line.Split("=", 2)
        if ($parts.Count -ne 2) {
            return
        }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim("'`"")
        if ($key) {
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Resolve-CommandPath {
    param([string[]]$Candidates)

    foreach ($candidate in $Candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }
    throw "Required command not found. Tried: $($Candidates -join ', ')"
}

function Ensure-RuntimeDir {
    if (-not (Test-Path $runtimeDir)) {
        New-Item -ItemType Directory -Path $runtimeDir | Out-Null
    }
}

function Get-PidFilePath {
    param([string]$Component)
    return (Join-Path $runtimeDir "$Component.pid")
}

function Get-LogPath {
    param(
        [string]$Component,
        [string]$Stream
    )
    return (Join-Path $runtimeDir "$Component.$Stream.log")
}

function Save-Pid {
    param(
        [string]$Component,
        [int]$ProcessId
    )
    Ensure-RuntimeDir
    Set-Content -Path (Get-PidFilePath $Component) -Value $ProcessId -Encoding ascii
}

function Remove-Pid {
    param([string]$Component)
    $pidPath = Get-PidFilePath $Component
    if (Test-Path $pidPath) {
        Remove-Item -LiteralPath $pidPath -Force
    }
}

function Get-ProcessFromPidFile {
    param([string]$Component)

    $pidPath = Get-PidFilePath $Component
    if (-not (Test-Path $pidPath)) {
        return $null
    }

    $rawPid = (Get-Content $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if (-not $rawPid) {
        Remove-Pid $Component
        return $null
    }

    try {
        $process = Get-Process -Id ([int]$rawPid) -ErrorAction Stop
        return $process
    }
    catch {
        Remove-Pid $Component
        return $null
    }
}

function Find-ProcessByCommandLine {
    param(
        [string]$Component,
        [scriptblock]$Predicate
    )

    $process = Get-ProcessFromPidFile $Component
    if ($null -ne $process) {
        return $process
    }

    try {
        $matched = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object $Predicate | Select-Object -First 1
    }
    catch {
        return $null
    }
    if ($null -eq $matched) {
        return $null
    }

    try {
        $process = Get-Process -Id $matched.ProcessId -ErrorAction Stop
        Save-Pid -Component $Component -ProcessId $process.Id
        return $process
    }
    catch {
        return $null
    }
}

function Get-OllamaProcess {
    return Find-ProcessByCommandLine "ollama" {
        $_.Name -match '^ollama(\.exe)?$' -and $_.CommandLine -match '\bserve\b'
    }
}

function Get-BackendProcess {
    return Find-ProcessByCommandLine "backend" {
        $_.CommandLine -match 'personal_ai\.web_ui' -and
        $_.CommandLine -like "*$VaultRoot*" -and
        $_.CommandLine -like "*$BackendPort*"
    }
}

function Get-FrontendProcess {
    return Find-ProcessByCommandLine "frontend" {
        $_.Name -match '^node(\.exe)?$' -and
        $_.CommandLine -match 'vite' -and
        $_.CommandLine -like "*$projectRoot*" -and
        $_.CommandLine -like "*$FrontendPort*"
    }
}

function Get-ComponentProcess {
    param([string]$Component)

    switch ($Component) {
        "ollama" { return Get-OllamaProcess }
        "backend" { return Get-BackendProcess }
        "frontend" { return Get-FrontendProcess }
        default { throw "Unknown component: $Component" }
    }
}

function Start-Component {
    param([string]$Component)

    $existing = Get-ComponentProcess $Component
    if ($null -ne $existing) {
        Write-Host "[$Component] already running (PID $($existing.Id))."
        return
    }

    Ensure-RuntimeDir
    $stdoutPath = Get-LogPath -Component $Component -Stream "stdout"
    $stderrPath = Get-LogPath -Component $Component -Stream "stderr"

    switch ($Component) {
        "ollama" {
            $ollamaExe = Resolve-CommandPath @("ollama.exe", "ollama")
            $started = Start-Process -FilePath $ollamaExe `
                -ArgumentList @("serve") `
                -WorkingDirectory $projectRoot `
                -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath `
                -WindowStyle Hidden `
                -PassThru
        }
        "backend" {
            $pythonExe = Resolve-CommandPath @("python.exe", "python", "py.exe", "py")
            $started = Start-Process -FilePath $pythonExe `
                -ArgumentList @(
                    "-m",
                    "personal_ai.web_ui",
                    "--vault",
                    $VaultRoot,
                    "--host",
                    $BindHost,
                    "--port",
                    $BackendPort.ToString()
                ) `
                -WorkingDirectory $projectRoot `
                -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath `
                -WindowStyle Hidden `
                -PassThru
        }
        "frontend" {
            $npmCmd = Resolve-CommandPath @("npm.cmd", "npm")
            $started = Start-Process -FilePath $npmCmd `
                -ArgumentList @(
                    "run",
                    "dev",
                    "--",
                    "--host",
                    $BindHost,
                    "--port",
                    $FrontendPort.ToString()
                ) `
                -WorkingDirectory (Join-Path $projectRoot "frontend") `
                -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath `
                -WindowStyle Hidden `
                -PassThru
        }
    }

    Start-Sleep -Milliseconds 500
    Save-Pid -Component $Component -ProcessId $started.Id
    Write-Host "[$Component] started (PID $($started.Id))."
}

function Stop-Component {
    param([string]$Component)

    $process = Get-ComponentProcess $Component
    if ($null -eq $process) {
        Remove-Pid $Component
        Write-Host "[$Component] already stopped."
        return
    }

    Stop-Process -Id $process.Id -Force
    Start-Sleep -Milliseconds 300
    Remove-Pid $Component
    Write-Host "[$Component] stopped (PID $($process.Id))."
}

function Show-Status {
    param([string[]]$ResolvedComponents)

    foreach ($component in $ResolvedComponents) {
        $process = Get-ComponentProcess $component
        if ($null -eq $process) {
            Write-Host "[$component] stopped"
            continue
        }

        $details = switch ($component) {
            "ollama" { "url=$env:OLLAMA_HOST" }
            "backend" { "url=http://$BindHost`:$BackendPort" }
            "frontend" { "url=http://$BindHost`:$FrontendPort" }
        }
        Write-Host "[$component] running pid=$($process.Id) $details"
    }
}

function Resolve-Components {
    param([string[]]$RequestedComponents)

    if ($RequestedComponents -contains "all") {
        return @("ollama", "backend", "frontend")
    }

    $deduped = New-Object System.Collections.Generic.List[string]
    foreach ($component in $RequestedComponents) {
        if (-not $deduped.Contains($component)) {
            $deduped.Add($component)
        }
    }
    return $deduped.ToArray()
}

function Get-ReversedComponents {
    param([string[]]$Items)

    $copy = @($Items.Clone())
    [array]::Reverse($copy)
    return $copy
}

$envPath = Join-Path $projectRoot $EnvFile
Load-EnvFile -Path $envPath

if (-not $env:OLLAMA_HOST -and $env:OLLAMA_BASE_URL) {
    $env:OLLAMA_HOST = $env:OLLAMA_BASE_URL
}

if (-not $env:PYTHONPATH) {
    $env:PYTHONPATH = $projectSrc
}
elseif ($env:PYTHONPATH -notlike "*$projectSrc*") {
    $env:PYTHONPATH = "$projectSrc;$($env:PYTHONPATH)"
}

$resolvedComponents = Resolve-Components $Components

switch ($Action) {
    "start" {
        foreach ($component in $resolvedComponents) {
            Start-Component $component
        }
        Show-Status $resolvedComponents
    }
    "stop" {
        foreach ($component in (Get-ReversedComponents $resolvedComponents)) {
            Stop-Component $component
        }
        Show-Status $resolvedComponents
    }
    "restart" {
        foreach ($component in (Get-ReversedComponents $resolvedComponents)) {
            Stop-Component $component
        }
        foreach ($component in $resolvedComponents) {
            Start-Component $component
        }
        Show-Status $resolvedComponents
    }
    "status" {
        Show-Status $resolvedComponents
    }
}
