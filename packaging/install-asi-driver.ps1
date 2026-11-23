<#
.SYNOPSIS
    Downloads and installs the official ZWO ASI camera driver.

.DESCRIPTION
    The SUN_watching installer runs this script when the optional
    "ZWO ASI camera driver" task is selected. The driver installer itself is
    not redistributed; it is downloaded from the official ZWO download
    endpoint, checked for a valid Authenticode signature, and then started
    elevated in silent mode (/S, NSIS).

    Use -CheckOnly to download and verify the installer without running it.

.PARAMETER DownloadUrl
    Official ZWO download endpoint.

.PARAMETER WorkDir
    Directory used for the temporary installer. Defaults to %TEMP%.

.PARAMETER CheckOnly
    Download and verify the signature, then exit without installing.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File install-asi-driver.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File install-asi-driver.ps1 -CheckOnly
#>
[CmdletBinding()]
param(
    [string]$DownloadUrl = 'https://dl.zwoastro.com/software?app=AsiCameraDriver&platform=windows86&region=Overseas',
    [string]$WorkDir = (Join-Path $env:TEMP 'SUN_watching_asi_driver'),
    [string]$PublisherPattern = 'ZWO',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$officialPage = 'https://www.zwoastro.com/software/camera-driver/'
$installer = $null
$exitCode = 1

function Write-Step {
    param([string]$Message)
    Write-Host "[asi-driver] $Message"
}

try {
    New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
    $installer = Join-Path $WorkDir 'ZWO_ASI_Cameras_driver_Setup.exe'
    Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue

    Write-Step "Downloading the driver installer from $DownloadUrl"
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $installer -UseBasicParsing -MaximumRedirection 10

    $signature = Get-AuthenticodeSignature -FilePath $installer
    if ($signature.Status -ne 'Valid') {
        throw "The downloaded installer does not have a valid Authenticode signature (status=$($signature.Status))."
    }
    $subject = $signature.SignerCertificate.Subject
    if ($subject -notmatch $PublisherPattern) {
        throw "Unexpected publisher: $subject"
    }
    Write-Step "Publisher: $subject"
    Write-Step "SHA256: $((Get-FileHash -Path $installer -Algorithm SHA256).Hash)"

    if ($CheckOnly) {
        Write-Step 'CheckOnly: download and signature verification succeeded.'
        $exitCode = 0
        return
    }

    Write-Step 'Starting the driver installer (a UAC prompt may appear)...'
    $process = Start-Process -FilePath $installer -ArgumentList '/S' -Verb RunAs -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "The driver installer exited with code $($process.ExitCode)."
    }
    Write-Step 'ZWO ASI driver installation completed.'
    $exitCode = 0
}
catch {
    Write-Error "[asi-driver] $($_.Exception.Message)"
    Write-Host "[asi-driver] Download page: $officialPage"
    $exitCode = 1
}
finally {
    if ($installer -and (Test-Path -LiteralPath $installer)) {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }
}

exit $exitCode
