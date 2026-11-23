$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

python -m pip install --upgrade pip
python -m pip install .
python -m pip install pyinstaller
# zwoasi is optional in the source tree. If it is available on this platform,
# include it in the executable so ASI cameras work without a separate Python install.
try { python -m pip install zwoasi } catch { Write-Warning "zwoasi could not be installed; building dummy-camera support only." }

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm --clean SUN_watching.spec

$required = @(
  "dist\SUN_watching\SUN_watching.exe",
  "dist\SUN_watching\_internal\config\config.yaml",
  "dist\SUN_watching\_internal\config\config_schema.json",
  "dist\SUN_watching\_internal\camera\bin\ASICamera2.dll"
)
foreach ($path in $required) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing packaged file: $path" }
}

# 同梱物が揃っていても起動時 import が壊れていないか確認する。
$env:SUN_WATCHING_HOME = Join-Path $env:TEMP "SUN_watching_smoke_home"
& "$root\dist\SUN_watching\SUN_watching.exe" --check-config
if ($LASTEXITCODE -ne 0) { throw "Frozen executable failed --check-config (exit=$LASTEXITCODE)" }
& "$root\dist\SUN_watching\SUN_watching.exe" --check-imports
if ($LASTEXITCODE -ne 0) { throw "Frozen executable failed --check-imports (exit=$LASTEXITCODE)" }

$version = (Get-Date -Format "yyyyMMdd-HHmmss")
$distDir = Join-Path $root "dist\SUN_watching"
$zipPath = Join-Path $root "dist\SUN_watching-windows-x64-$version.zip"
Compress-Archive -Path "$distDir\*" -DestinationPath $zipPath -Force
Write-Host "Created: $zipPath"
