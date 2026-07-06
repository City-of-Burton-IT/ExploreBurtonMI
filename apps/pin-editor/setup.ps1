# Pin Editor one-time setup: create the venv, install deps, and add the
# pins.local hosts entry (the hosts edit needs an elevation prompt). PS 5.1 safe.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# 1. venv + dependencies
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host 'Creating virtual environment...'
    python -m venv .venv
}
Write-Host 'Installing dependencies...'
& '.venv\Scripts\python.exe' -m pip install --quiet --upgrade pip
& '.venv\Scripts\python.exe' -m pip install --quiet -r requirements.txt

# 2. hosts entry: 127.0.0.1 pins.local
$hostsFile = "$env:SystemRoot\System32\drivers\etc\hosts"
$present = Select-String -Path $hostsFile -Pattern '\bpins\.local\b' -Quiet -ErrorAction SilentlyContinue
if ($present) {
    Write-Host 'hosts entry for pins.local already present.'
} else {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
    if ($admin) {
        Add-Content -Path $hostsFile -Value '127.0.0.1 pins.local'
        Write-Host 'Added pins.local to the hosts file.'
    } else {
        Write-Host 'Adding pins.local to the hosts file (an elevation prompt will appear)...'
        Start-Process powershell -Verb RunAs -Wait -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
            "Add-Content -Path '$hostsFile' -Value '127.0.0.1 pins.local'"
        )
        Write-Host 'hosts entry added (if you approved the prompt).'
    }
}

# 3. port 80 availability check
$busy = Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    Write-Host 'WARNING: port 80 is already in use on this machine.'
    Write-Host '  Start with a different port:  set PIN_EDITOR_PORT=8080 then run.cmd'
    Write-Host '  and open http://pins.local:8080'
}
Write-Host ''
Write-Host 'Setup complete. Double-click run.cmd to start the editor.'
