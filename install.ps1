$ErrorActionPreference = 'Stop'
$release = 'https://github.com/Buasakaking/NecoL-Codex-Pet/releases/latest/download/NecoL-codex-pet.zip'
$expected = 'ADC88616817E9BE2D272C58689307FEA1B674E725EABE521585BE1304803FCFE'
$root = Join-Path $env:TEMP 'NecoL-Codex-Pet'
$zip = Join-Path $root 'NecoL-codex-pet.zip'
$expanded = Join-Path $root 'package'
New-Item -ItemType Directory -Force -Path $root | Out-Null
Invoke-WebRequest $release -OutFile $zip
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash
if ($actual -ne $expected) { throw "SHA-256 mismatch: $actual" }
if (Test-Path $expanded) { Remove-Item $expanded -Recurse -Force }
Expand-Archive $zip $expanded -Force
$installer = Join-Path $expanded 'install.ps1'
if (-not (Test-Path $installer)) { throw "Installer not found: $installer" }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installer
if ($LASTEXITCODE -ne 0) { throw "NecoL installer failed: $LASTEXITCODE" }
Write-Host 'NecoL Codex pet installation completed.'
