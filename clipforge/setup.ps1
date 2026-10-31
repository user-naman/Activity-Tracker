# One-command setup for Windows 10/11. Safe to re-run.
# Run by double-clicking setup.cmd (it bypasses the script execution policy for this file only).
$ErrorActionPreference = "Continue"   # native tools write to stderr; we check exit codes ourselves
Set-Location $PSScriptRoot

function Say($t)  { Write-Host "`n$t" -ForegroundColor Cyan }
function Fail($t) { Write-Host "`n$t" -ForegroundColor Red; exit 1 }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                "$env:LOCALAPPDATA\Microsoft\WinGet\Links"
}
function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in "3.13", "3.12", "3.11") {
            $exe = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
        }
    }
    $direct = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python31[1-3]\python.exe" -ErrorAction SilentlyContinue |
              Sort-Object FullName -Descending | Select-Object -First 1
    if ($direct) { return $direct.FullName }
    return $null
}
function Winget-Install($id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "winget is missing. Install 'App Installer' from the Microsoft Store, then run setup again."
    }
    winget install -e --id $id --scope user --accept-package-agreements --accept-source-agreements --silent
    Refresh-Path
}

Say "1/5 Python"
$py = Find-Python
if (-not $py) { Winget-Install "Python.Python.3.12"; $py = Find-Python }
if (-not $py) { Fail "Python didn't install. Get Python 3.12 from python.org, then run setup again." }
Write-Host "Using $py"

Say "2/5 ffmpeg"
Refresh-Path
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Winget-Install "Gyan.FFmpeg" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Fail "ffmpeg installed but isn't visible yet. Close this window, then double-click setup.cmd again."
}
Write-Host "ffmpeg OK"

Say "3/5 Installing ClipForge (first time takes a few minutes)"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $py -m venv .venv }
& .venv\Scripts\python.exe -m pip install -q --upgrade pip
& .venv\Scripts\python.exe -m pip install -q -e ".[download,dev]"
if ($LASTEXITCODE -ne 0) { Fail "Install failed. Scroll up for the error and send it to Claude." }

Say "4/5 Your config and the 'clipforge' command"
$home_dir = Join-Path $HOME "ClipForge"
$bin = Join-Path $home_dir "bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$config = Join-Path $home_dir "clipforge.toml"
if (Test-Path $config) { Write-Host "Keeping existing $config" }
else { & .venv\Scripts\clipforge.exe init $config }

$exe = Join-Path $PSScriptRoot ".venv\Scripts\clipforge.exe"
Set-Content -Path (Join-Path $bin "clipforge.cmd") -Value "@`"$exe`" %*" -Encoding ASCII
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $bin) {
    [Environment]::SetEnvironmentVariable("Path", ($userPath.TrimEnd(";") + ";" + $bin), "User")
}
$env:Path += ";$bin"

Say "5/5 Checking everything"
& $exe --config $config doctor

Say "Done."
Write-Host "Open a NEW PowerShell window and type:  clipforge edit"
Write-Host "Your clips and settings live in $home_dir"
