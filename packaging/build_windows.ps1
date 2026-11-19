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

$version = (Get-Date -Format "yyyyMMdd-HHmmss")
$distDir = Join-Path $root "dist\SUN_watching"
$zipPath = Join-Path $root "dist\SUN_watching-windows-x64-$version.zip"
Compress-Archive -Path "$distDir\*" -DestinationPath $zipPath -Force
Write-Host "Created: $zipPath"
