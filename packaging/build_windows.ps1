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

$null = [scriptblock]::Create((Get-Content -LiteralPath "packaging\install-asi-driver.ps1" -Raw))
$tools = "dist\SUN_watching\tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null
Copy-Item -LiteralPath "packaging\install-asi-driver.ps1" -Destination (Join-Path $tools "install-asi-driver.ps1") -Force

$required = @(
  "dist\SUN_watching\SUN_watching.exe",
  "dist\SUN_watching\_internal\config\config.yaml",
  "dist\SUN_watching\_internal\config\config_schema.json",
  "dist\SUN_watching\_internal\camera\bin\ASICamera2.dll",
  "dist\SUN_watching\tools\install-asi-driver.ps1"
)
foreach ($path in $required) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing packaged file: $path" }
}

# 同梱 DLL がソースと同一で 64bit であることを確認する。
$sourceDll = "sun_find_west_v2\camera\bin\ASICamera2.dll"
$packagedDll = "dist\SUN_watching\_internal\camera\bin\ASICamera2.dll"
if ((Get-FileHash -LiteralPath $packagedDll -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $sourceDll -Algorithm SHA256).Hash) {
  throw "Packaged ASICamera2.dll does not match the source DLL."
}
$peBytes = [System.IO.File]::ReadAllBytes($packagedDll)
$peOffset = [System.BitConverter]::ToInt32($peBytes, 0x3C)
$machine = [System.BitConverter]::ToUInt16($peBytes, $peOffset + 4)
if ($machine -ne 0x8664) { throw ("Packaged ASICamera2.dll is not x64 (machine=0x{0:X4})." -f $machine) }

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
